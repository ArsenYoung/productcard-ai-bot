from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def platforms_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Ozon", callback_data="platform:ozon")],
        [InlineKeyboardButton(text="Wildberries", callback_data="platform:wb")],
        [InlineKeyboardButton(text="Etsy", callback_data="platform:etsy")],
        [InlineKeyboardButton(text="Shopify", callback_data="platform:shopify")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def export_keyboard(gen_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Экспорт TXT", callback_data=f"export:txt:{gen_id}"),
            InlineKeyboardButton(text="Экспорт CSV", callback_data=f"export:csv:{gen_id}"),
        ],
        [InlineKeyboardButton(text="Новая генерация", callback_data="new")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tone_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Продающий", callback_data="tone:selling")],
        [InlineKeyboardButton(text="Лаконичный", callback_data="tone:concise")],
        [InlineKeyboardButton(text="Экспертный", callback_data="tone:expert")],
        [InlineKeyboardButton(text="Нейтральный", callback_data="tone:neutral")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def length_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Короткое", callback_data="length:short")],
        [InlineKeyboardButton(text="Среднее", callback_data="length:medium")],
        [InlineKeyboardButton(text="Полное", callback_data="length:long")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
