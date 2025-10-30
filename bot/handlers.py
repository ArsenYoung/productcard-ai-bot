from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .states import GenerationStates
from .keyboards import platforms_keyboard, export_keyboard
from aiogram.types import BufferedInputFile
from services.generation_service import generate_product_card
from storage.sqlite_repo import add_generation, get_generation, prune_history
from app.config import get_settings


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(GenerationStates.choosing_platform)
    await message.answer(
        "Привет! Выбери платформу для генерации карточки товара:",
        reply_markup=platforms_keyboard(),
    )


@router.callback_query(F.data.startswith("platform:"))
async def on_platform(callback: CallbackQuery, state: FSMContext):
    platform_code = callback.data.split(":", 1)[1]
    await state.update_data(platform=platform_code)
    await state.set_state(GenerationStates.waiting_input)
    await callback.message.answer(
        "Введи название и характеристики одним сообщением.\n"
        "Например:\n"
        "Беспроводная мышь Logitech M185\n"
        "2.4 ГГц, тихие клики, до 12 мес работы",
    )
    await callback.answer()


@router.message(GenerationStates.waiting_input)
async def on_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Сообщение пустое. Введи название и характеристики.")
        return

    # Простая эвристика: первая строка — название, остальное — характеристики
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    product_name = lines[0]
    features = "; ".join(lines[1:]) if len(lines) > 1 else None

    data = await state.get_data()
    platform = data.get("platform")

    wait_msg = await message.answer("Генерирую карточку… Это может занять несколько секунд.")
    try:
        payload = await generate_product_card(
            product_name=product_name,
            features=features,
            platform=platform,
        )
    except Exception as e:
        await wait_msg.edit_text(
            f"Не удалось сгенерировать ответ: {e}\nПопробуй сократить ввод и повторить."
        )
        return

    # Сохраняем в БД
    cfg = get_settings()
    gen_id = await add_generation(
        cfg.db_path,
        tg_id=message.from_user.id,
        platform=platform,
        product_name=product_name,
        features=features,
        payload=payload,
    )
    # Ограничиваем историю до N
    await prune_history(cfg.db_path, tg_id=message.from_user.id, keep=cfg.history_limit)

    title = payload.get("title", "")
    desc = payload.get("short_description", "")
    bullets = payload.get("bullets", [])

    text_out = (
        f"Заголовок: {title}\n\n"
        f"Описание: {desc}\n\n"
        + ("Пункты:\n" + "\n".join(f"- {b}" for b in bullets) if bullets else "")
    ).strip()

    await wait_msg.edit_text(text_out or "Пустой ответ. Попробуй ещё раз.")
    await message.answer(
        "Экспортировать результат или начать новую генерацию?",
        reply_markup=export_keyboard(gen_id),
    )


@router.callback_query(F.data == "new")
async def on_new(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GenerationStates.choosing_platform)
    await callback.message.answer(
        "Выбери платформу:",
        reply_markup=platforms_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("export:"))
async def on_export(callback: CallbackQuery):
    try:
        _, kind, id_str = callback.data.split(":", 2)
        gen_id = int(id_str)
    except Exception:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    cfg = get_settings()
    row = await get_generation(cfg.db_path, gen_id=gen_id)
    if not row:
        await callback.answer("Запись не найдена", show_alert=True)
        return

    # Собираем данные для экспорта
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
        content = render_text_export(gen)
        await callback.message.answer_document(
            BufferedInputFile(content.encode("utf-8"), filename=f"card_{gen_id}.txt")
        )
    elif kind == "csv":
        content = render_csv_export(gen)
        await callback.message.answer_document(
            BufferedInputFile(content.encode("utf-8"), filename=f"card_{gen_id}.csv")
        )
    else:
        await callback.answer("Неизвестный формат", show_alert=True)
        return

    await callback.answer()
