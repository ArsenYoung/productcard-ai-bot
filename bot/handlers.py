from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .states import GenerationStates
from .keyboards import platforms_keyboard
from services.generation_service import generate_product_card


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

    # Простейшая эвристика: первая строка — название, остальное — характеристики
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

    title = payload.get("title", "")
    desc = payload.get("short_description", "")
    bullets = payload.get("bullets", [])

    text_out = (
        f"Заголовок: {title}\n\n"
        f"Описание: {desc}\n\n"
        + ("Пункты:\n" + "\n".join(f"- {b}" for b in bullets) if bullets else "")
    ).strip()

    await wait_msg.edit_text(text_out or "Пустой ответ. Попробуй ещё раз.")
    # Возвращаемся к выбору платформы для следующей генерации
    await state.set_state(GenerationStates.choosing_platform)
    await message.answer(
        "Готово. Сгенерировать ещё? Выбери платформу:",
        reply_markup=platforms_keyboard(),
    )

