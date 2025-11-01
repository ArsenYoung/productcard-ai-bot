from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .states import GenerationStates
from .keyboards import (
    platforms_keyboard,
    export_keyboard,
    tone_keyboard,
    length_keyboard,
    language_keyboard,
    cancel_keyboard,
    actions_keyboard,
    actions_after_cancel_keyboard,
)
from .i18n import t
from aiogram.types import BufferedInputFile
from services import generation_service
import json
import re
from storage.sqlite_repo import add_generation, get_generation, prune_history
from app.config import get_settings


router = Router()

# In-memory map of running tasks: tg_id -> {"task": Task, "wait_msg": Message, "lang": str}
_running = {}


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # First step: choose UI/content language
    await state.set_state(GenerationStates.choosing_language)
    await message.answer(
        # Bilingual prompt so the very first message is understandable
        "Выберите язык / Choose language",
        reply_markup=language_keyboard(),
    )


@router.callback_query(F.data.startswith("platform:"))
async def on_platform(callback: CallbackQuery, state: FSMContext):
    platform_code = callback.data.split(":", 1)[1]
    await state.update_data(platform=platform_code)
    data = await state.get_data()
    lang = data.get("language")
    if not lang:
        # If language wasn't chosen yet (backward path), ask for it now
        await state.set_state(GenerationStates.choosing_language)
        await callback.message.answer(
            t("en", "choose_language"), reply_markup=language_keyboard()
        )
    else:
        # Proceed to tone selection in chosen language
        await state.set_state(GenerationStates.choosing_tone)
        await callback.message.answer(
            t(lang, "choose_tone"), reply_markup=tone_keyboard(lang)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def on_language(callback: CallbackQuery, state: FSMContext):
    lang_code = callback.data.split(":", 1)[1]
    if lang_code not in {"ru", "en"}:
        await callback.answer(t("en", "unsupported_language"), show_alert=True)
        return
    await state.update_data(language=lang_code)
    # After choosing language, go to marketplace selection
    await state.set_state(GenerationStates.choosing_platform)
    await callback.message.answer(
        t(lang_code, "choose_marketplace"), reply_markup=platforms_keyboard(lang_code)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tone:"))
async def on_tone(callback: CallbackQuery, state: FSMContext):
    tone_code = callback.data.split(":", 1)[1]
    await state.update_data(tone=tone_code)
    data = await state.get_data()
    lang = data.get("language", "en")
    await state.set_state(GenerationStates.choosing_length)
    await callback.message.answer(
        t(lang, "choose_length"), reply_markup=length_keyboard(lang)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("length:"))
async def on_length(callback: CallbackQuery, state: FSMContext):
    length_code = callback.data.split(":", 1)[1]
    await state.update_data(length=length_code)
    data = await state.get_data()
    lang = data.get("language", "en")
    await state.set_state(GenerationStates.waiting_input)
    await callback.message.answer(
        t(lang, "prompt_input"),
    )
    await callback.answer()


@router.message(GenerationStates.waiting_input)
async def on_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        data = await state.get_data()
        lang = data.get("language", "en")
        await message.answer(t(lang, "empty_message"))
        return

    # Simple heuristic: first line is the product name, the rest are specs
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    product_name = lines[0]
    features = "; ".join(lines[1:]) if len(lines) > 1 else None

    data = await state.get_data()
    platform = data.get("platform")
    language = data.get("language", "ru")
    tone = data.get("tone", "neutral")
    length = data.get("length", "medium")

    # Throttle: if already generating for this user
    if _running.get(message.from_user.id):
        await message.answer(t(language, "busy_generating"))
        return

    await state.set_state(GenerationStates.generating)
    wait_msg = await message.answer(t(language, "wait_generating"), reply_markup=cancel_keyboard(language))

    # Start generation as a task to allow cancellation and progress updates
    import asyncio

    last_percent = 0

    async def _render_progress():
        try:
            await wait_msg.edit_text(
                f"{t(language, 'wait_generating_short')} {last_percent}%",
                reply_markup=cancel_keyboard(language),
            )
        except Exception:
            pass

    async def _progress(frac: float):
        nonlocal last_percent
        pct = max(0, min(100, int(round(frac * 100))))
        if pct <= last_percent:
            return
        last_percent = pct
        await _render_progress()

    async def _do_generate():
        return await generation_service.generate_product_card(
            product_name=product_name,
            features=features,
            platform=platform,
            tone=tone,
            length=length,
            language=language,
            progress_cb=_progress,
        )

    task = asyncio.create_task(_do_generate())
    _running[message.from_user.id] = {"task": task, "wait_msg": wait_msg, "lang": language}

    # Fallback ticker: if model/streaming does not push progress, grow 1..90%
    async def _ticker():
        nonlocal last_percent
        try:
            while not task.done():
                if last_percent < 90:
                    last_percent = min(90, max(1, last_percent + 3))
                    await _render_progress()
                await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            pass

    tick_task = asyncio.create_task(_ticker())

    try:
        payload = await task
    except asyncio.CancelledError:
        try:
            await wait_msg.edit_text(t(language, "cancelled"))
        except Exception:
            pass
        _running.pop(message.from_user.id, None)
        await state.set_state(GenerationStates.waiting_input)
        return
    except Exception as e:
        # Give a more helpful hint on LLM connectivity issues
        err = str(e)
        if "Cannot connect to host" in err or "Connect call failed" in err:
            cfg = get_settings()
            hint = t(language, "gen_failed_unavailable", base_url=cfg.llm_base_url)
            await wait_msg.edit_text(
                t(language, "gen_failed_prefix", error=e) + f"\n\n{hint}"
            )
        else:
            await wait_msg.edit_text(
                t(language, "gen_failed", error=e)
            )
        _running.pop(message.from_user.id, None)
        await state.set_state(GenerationStates.waiting_input)
        return
    finally:
        try:
            tick_task.cancel()
        except Exception:
            pass

    # Save to DB
    cfg = get_settings()
    gen_id = await add_generation(
        cfg.db_path,
        tg_id=message.from_user.id,
        platform=platform,
        product_name=product_name,
        features=features,
        payload=payload,
    )
    # Prune history up to N
    await prune_history(cfg.db_path, tg_id=message.from_user.id, keep=cfg.history_limit)

    # Build payload for display and exports
    gen = {
        "platform": platform,
        "product_name": product_name,
        "features": features,
        "title": payload.get("title"),
        "short_description": payload.get("short_description"),
        "bullets": payload.get("bullets"),
    }
    from services.export_service import render_text_export

    # Render localized plain-text message (ru/en) and strip trailing spaces
    content = render_text_export(gen, language).strip()
    await wait_msg.edit_text(content or t(language, "empty_response"))
    await message.answer(
        t(language, "export_prompt"),
        reply_markup=export_keyboard(gen_id, language),
    )
    # Suggest next actions (new/edit)
    await message.answer(
        t(language, "suggest_next"),
        reply_markup=actions_keyboard(gen_id, language),
    )
    _running.pop(message.from_user.id, None)
    await state.set_state(GenerationStates.waiting_input)


@router.callback_query(F.data == "new")
async def on_new(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    await state.set_state(GenerationStates.choosing_platform)
    await callback.message.answer(
        t(lang, "choose_marketplace"),
        reply_markup=platforms_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def on_cancel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    info = _running.get(callback.from_user.id)
    if not info:
        await callback.answer(t(lang, "malformed_request"), show_alert=False)
        return
    task = info.get("task")
    if task and not task.done():
        task.cancel()
    try:
        await callback.message.edit_text(t(lang, "cancelled"))
    except Exception:
        pass
    _running.pop(callback.from_user.id, None)
    await state.set_state(GenerationStates.waiting_input)
    # Offer next steps: new or edit last request
    await callback.message.answer(
        t(lang, "suggest_next"),
        reply_markup=actions_after_cancel_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit:"))
async def on_edit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    _, target = callback.data.split(":", 1)
    cfg = get_settings()
    from storage.sqlite_repo import get_generation, recent_generations
    row = None
    if target == "last":
        rows = await recent_generations(cfg.db_path, tg_id=callback.from_user.id, limit=1)
        row = rows[0] if rows else None
    else:
        try:
            gen_id = int(target)
            row = await get_generation(cfg.db_path, gen_id=gen_id)
        except Exception:
            row = None
    if not row:
        await callback.answer(t(lang, "no_previous"), show_alert=True)
        return
    name = row.get("product_name") or ""
    feats = row.get("features") or ""
    original = name if not feats else f"{name}\n{feats}"
    await state.set_state(GenerationStates.waiting_input)
    await callback.message.answer(
        t(lang, "edit_send", original=original)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("export:"))
async def on_export(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    try:
        _, kind, id_str = callback.data.split(":", 2)
        gen_id = int(id_str)
    except Exception:
        await callback.answer(t(lang, "malformed_request"), show_alert=True)
        return

    cfg = get_settings()
    row = await get_generation(cfg.db_path, gen_id=gen_id)
    if not row:
        await callback.answer(t(lang, "record_not_found"), show_alert=True)
        return

    # Collect data for export
    gen = {
        "platform": row.get("platform"),
        "product_name": row.get("product_name"),
        "features": row.get("features"),
        "title": row.get("title"),
        "short_description": row.get("short_description"),
        "bullets": row.get("bullets"),
    }

    from services.export_service import render_text_export, render_csv_export

    if kind == "txt":
        # Use user's chosen language for TXT export formatting
        content = render_text_export(gen, lang)
        await callback.message.answer_document(
            BufferedInputFile(content.encode("utf-8"), filename=f"card_{gen_id}.txt")
        )
    elif kind == "csv":
        content = render_csv_export(gen)
        await callback.message.answer_document(
            BufferedInputFile(content.encode("utf-8"), filename=f"card_{gen_id}.csv")
        )
    else:
        await callback.answer(t(lang, "unknown_format"), show_alert=True)
        return

    await callback.answer()
