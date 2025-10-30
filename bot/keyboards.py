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
