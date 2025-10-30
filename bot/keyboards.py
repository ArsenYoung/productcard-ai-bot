from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def platforms_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Ozon", callback_data="platform:ozon")],
        [InlineKeyboardButton(text="Wildberries", callback_data="platform:wb")],
        [InlineKeyboardButton(text="Etsy", callback_data="platform:etsy")],
        [InlineKeyboardButton(text="Shopify", callback_data="platform:shopify")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

