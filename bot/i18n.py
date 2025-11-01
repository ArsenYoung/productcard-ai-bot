from __future__ import annotations

from typing import Dict, Optional


_MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        # Generic flow
        "start_choose_language": "Choose your language",
        "choose_platform": "Choose a marketplace:",
        "choose_language": "Which language should the content be in?",
        "choose_tone": "Choose a writing tone:",
        "choose_length": "Choose description length:",
        "prompt_input": (
            "Send product name and specs in one message.\n"
            "For example:\n"
            "Bluetooth Wireless Mouse Logitech M185\n"
            "2.4 GHz, silent clicks, up to 12 months battery"
        ),
        "empty_message": "Empty message. Please provide product name and specs.",
        "wait_generating": "Generating a product card… This may take a few seconds.",
        "wait_generating_short": "Generating…",
        "gen_failed_unavailable": (
            "Looks like the model service is unavailable.\n"
            "Ensure Ollama is running and reachable at {base_url}.\n"
            "If the bot runs in Docker: use make up (host network)."
        ),
        "gen_failed": "Failed to generate a response: {error}\nTry simplifying the input and retry.",
        "gen_failed_prefix": "Failed to generate a response: {error}",
        "empty_response": "Empty response. Please try again.",
        "export_prompt": "Export the result or start a new generation?",
        "busy_generating": "You already have a generation in progress.",
        "cancelled": "Generation was cancelled.",
        "btn_cancel": "Cancel",
        "btn_edit_request": "Edit Request",
        "btn_edit_previous": "Edit Previous",
        "suggest_next": "What would you like to do next?",
        "edit_send": "Send the edited request as one message.\nOriginal:\n{original}",
        "no_previous": "No previous generation found.",
        "choose_marketplace": "Choose a marketplace:",
        "malformed_request": "Malformed request",
        "record_not_found": "Record not found",
        "unknown_format": "Unknown format",
        "unsupported_language": "Unsupported language",
        # Buttons
        "btn_lang_ru": "Русский",
        "btn_lang_en": "English",
        "btn_tone_salesy": "Salesy",
        "btn_tone_concise": "Concise",
        "btn_tone_expert": "Expert",
        "btn_tone_neutral": "Neutral",
        "btn_length_short": "Short",
        "btn_length_medium": "Medium",
        "btn_length_long": "Long",
        "btn_export_txt": "Export TXT",
        "btn_export_csv": "Export CSV",
        "btn_new_generation": "New Generation",
    },
    "ru": {
        # Generic flow
        "start_choose_language": "Выберите язык интерфейса",
        "choose_platform": "Выберите маркетплейс:",
        "choose_language": "На каком языке должен быть контент?",
        "choose_tone": "Выберите тон текста:",
        "choose_length": "Выберите длину описания:",
        "prompt_input": (
            "Отправьте название товара и характеристики одним сообщением.\n"
            "Например:\n"
            "Беспроводная мышь Logitech M185\n"
            "2.4 ГГц, тихие клики, до 12 месяцев работы от батареи"
        ),
        "empty_message": "Пустое сообщение. Пожалуйста, укажите название и характеристики товара.",
        "wait_generating": "Генерирую карточку товара… Это может занять несколько секунд.",
        "wait_generating_short": "Генерация…",
        "gen_failed_unavailable": (
            "Похоже, сервис модели недоступен.\n"
            "Убедитесь, что Ollama запущен и доступен по адресу {base_url}.\n"
            "Если бот запущен в Docker: используйте make up (host network)."
        ),
        "gen_failed": "Не удалось сгенерировать ответ: {error}\nПопробуйте упростить ввод и повторить.",
        "gen_failed_prefix": "Не удалось сгенерировать ответ: {error}",
        "empty_response": "Пустой ответ. Пожалуйста, попробуйте снова.",
        "export_prompt": "Экспортировать результат или начать новую генерацию?",
        "busy_generating": "У вас уже идёт генерация.",
        "cancelled": "Генерация отменена.",
        "btn_cancel": "Отмена",
        "btn_edit_request": "Редактировать запрос",
        "btn_edit_previous": "Редактировать предыдущий",
        "suggest_next": "Что дальше?",
        "edit_send": "Отправьте отредактированный запрос одним сообщением.\nИсходный текст:\n{original}",
        "no_previous": "Предыдущих генераций не найдено.",
        "choose_marketplace": "Выберите маркетплейс:",
        "malformed_request": "Некорректный запрос",
        "record_not_found": "Запись не найдена",
        "unknown_format": "Неизвестный формат",
        "unsupported_language": "Неподдерживаемый язык",
        # Buttons
        "btn_lang_ru": "Русский",
        "btn_lang_en": "English",
        "btn_tone_salesy": "Рекламный",
        "btn_tone_concise": "Краткий",
        "btn_tone_expert": "Экспертный",
        "btn_tone_neutral": "Нейтральный",
        "btn_length_short": "Короткое",
        "btn_length_medium": "Среднее",
        "btn_length_long": "Длинное",
        "btn_export_txt": "Экспорт TXT",
        "btn_export_csv": "Экспорт CSV",
        "btn_new_generation": "Новая генерация",
    },
}


def t(lang: Optional[str], key: str, **fmt) -> str:
    """Translate a message key into the given language.

    Falls back to English, then to the key itself.
    """
    lang = (lang or "en").lower()
    base = _MESSAGES.get(lang) or _MESSAGES.get("en", {})
    value = base.get(key) or _MESSAGES["en"].get(key) or key
    if fmt:
        try:
            return value.format(**fmt)
        except Exception:
            return value
    return value
