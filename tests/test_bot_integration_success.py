import pytest


pytestmark = pytest.mark.asyncio


class _FakeUser:
    def __init__(self, id):
        self.id = id


class _FakeMessage:
    def __init__(self, text: str, user_id: int = 1):
        self.text = text
        self.from_user = _FakeUser(user_id)
        self.answers = []
        self.last_wait = None

    async def answer(self, text: str, reply_markup=None):
        # Emulate sending a message and return an object that supports edit_text
        self.answers.append(text)

        class _Wait:
            def __init__(self, outer):
                self.outer = outer
                self.edited_texts = []

            async def edit_text(self, text):
                self.edited_texts.append(text)
                self.outer.last_wait = self

        return _Wait(self)


class _FakeCallback:
    def __init__(self, data: str, message: _FakeMessage):
        self.data = data
        self.message = message
        self.answered = False

    async def answer(self, *args, **kwargs):
        self.answered = True


class _FakeState:
    def __init__(self):
        self._data = {}
        self._state = None

    async def set_state(self, value):
        self._state = value

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def get_data(self):
        return dict(self._data)


async def test_full_flow_generates_output(monkeypatch):
    # Arrange: stub product generation with a deterministic payload
    from services import generation_service
    from storage import sqlite_repo
    from app import config as app_config

    async def _fake_generate_product_card(**kwargs):
        return {
            "title": "Logitech M185 — беспроводная мышь",
            "short_description": "Удобная мышь с тихими кликами и стабильной связью 2.4 ГГц.",
            "bullets": [
                "До 12 месяцев работы от батарейки",
                "Компактный размер, Plug-and-Play",
            ],
        }

    async def _fake_add_generation(db_path, **kwargs):
        return 42

    async def _fake_prune_history(db_path, **kwargs):
        return None

    # Return lightweight settings for handler needs
    def _fake_get_settings():
        from types import SimpleNamespace

        return SimpleNamespace(
            db_path=":memory:",  # not used because add/prune are stubbed
            history_limit=5,
            llm_model="phi3:mini",
            llm_base_url="http://localhost:11434",
            log_level="INFO",
        )

    monkeypatch.setattr(
        generation_service, "generate_product_card", _fake_generate_product_card, raising=True
    )
    monkeypatch.setattr(sqlite_repo, "add_generation", _fake_add_generation, raising=True)
    monkeypatch.setattr(sqlite_repo, "prune_history", _fake_prune_history, raising=True)
    monkeypatch.setattr(app_config, "get_settings", _fake_get_settings, raising=True)

    # Import handlers after patching settings to avoid side effects
    from bot.handlers import on_platform, on_language, on_tone, on_length, on_input

    # Simulate user flow
    state = _FakeState()
    msg = _FakeMessage(text="")

    # Select platform
    cb1 = _FakeCallback("platform:ozon", msg)
    await on_platform(cb1, state)

    # Select language
    cb_lang = _FakeCallback("lang:ru", msg)
    await on_language(cb_lang, state)

    # Select tone
    cb2 = _FakeCallback("tone:neutral", msg)
    await on_tone(cb2, state)

    # Select length
    cb3 = _FakeCallback("length:medium", msg)
    await on_length(cb3, state)

    # Send product input
    user_msg = _FakeMessage(
        text=(
            "Беспроводная мышь Logitech M185\n"
            "2.4 ГГц, тихие клики, до 12 мес работы"
        ),
        user_id=123,
    )
    await on_input(user_msg, state)

    # Assert: bot edited the waiting message with full TXT-like content
    assert user_msg.last_wait is not None
    assert user_msg.last_wait.edited_texts, "No output produced by handler"
    out = user_msg.last_wait.edited_texts[-1]
    # Accept either EN or RU localized labels
    assert ("Title:" in out) or ("Заголовок:" in out)
    assert ("Description:" in out) or ("Описание:" in out)
    assert ("Bullets:" in out) or ("Пункты:" in out)
    assert "Logitech" in out
