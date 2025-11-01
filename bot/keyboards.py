from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional
from .i18n import t


def platforms_keyboard(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Ozon", callback_data="platform:ozon")],
        [InlineKeyboardButton(text="Wildberries", callback_data="platform:wb")],
        [InlineKeyboardButton(text="Etsy", callback_data="platform:etsy")],
        [InlineKeyboardButton(text="Shopify", callback_data="platform:shopify")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def export_keyboard(gen_id: int, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=t(lang, "btn_export_txt"), callback_data=f"export:txt:{gen_id}"),
            InlineKeyboardButton(text=t(lang, "btn_export_csv"), callback_data=f"export:csv:{gen_id}"),
        ],
        [InlineKeyboardButton(text=t(lang, "btn_new_generation"), callback_data="new")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def language_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=t("ru", "btn_lang_ru"), callback_data="lang:ru")],
        [InlineKeyboardButton(text=t("en", "btn_lang_en"), callback_data="lang:en")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tone_keyboard(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=t(lang, "btn_tone_salesy"), callback_data="tone:selling")],
        [InlineKeyboardButton(text=t(lang, "btn_tone_concise"), callback_data="tone:concise")],
        [InlineKeyboardButton(text=t(lang, "btn_tone_expert"), callback_data="tone:expert")],
        [InlineKeyboardButton(text=t(lang, "btn_tone_neutral"), callback_data="tone:neutral")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def length_keyboard(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=t(lang, "btn_length_short"), callback_data="length:short")],
        [InlineKeyboardButton(text=t(lang, "btn_length_medium"), callback_data="length:medium")],
        [InlineKeyboardButton(text=t(lang, "btn_length_long"), callback_data="length:long")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_keyboard(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def actions_keyboard(gen_id: int, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    """Offer next steps after success: new or edit current request."""
    buttons = [
        [
            InlineKeyboardButton(text=t(lang, "btn_new_generation"), callback_data="new"),
            InlineKeyboardButton(text=t(lang, "btn_edit_request"), callback_data=f"edit:{gen_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def actions_after_cancel_keyboard(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    """Offer next steps after cancel: new or edit previous request."""
    buttons = [
        [
            InlineKeyboardButton(text=t(lang, "btn_new_generation"), callback_data="new"),
            InlineKeyboardButton(text=t(lang, "btn_edit_previous"), callback_data="edit:last"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
