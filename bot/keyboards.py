from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


PLATFORMS = [
    ("Ozon", "ozon"),
    ("Wildberries", "wb"),
    ("Etsy", "etsy"),
    ("Shopify", "shopify"),
]


def platforms_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=title, callback_data=f"platform:{code}")]
        for title, code in PLATFORMS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

