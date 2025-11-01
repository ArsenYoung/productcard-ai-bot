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
)
from .i18n import t
from aiogram.types import BufferedInputFile
from services import generation_service
import json
import re
from storage.sqlite_repo import add_generation, get_generation, prune_history
from app.config import get_settings


router = Router()


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

    wait_msg = await message.answer(t(language, "wait_generating"))
    try:
        payload = await generation_service.generate_product_card(
            product_name=product_name,
            features=features,
            platform=platform,
            tone=tone,
            length=length,
            language=language,
        )
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
        return

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
