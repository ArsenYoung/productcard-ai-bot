import types
import pytest


pytestmark = pytest.mark.asyncio


async def _raise_conn_error(*args, **kwargs):
    raise RuntimeError("Cannot connect to host localhost:11434 ssl:default [Connect call failed ('127.0.0.1', 11434)]")


async def test_generation_service_handles_connection_error_with_fallback(monkeypatch):
    """In new behavior, service returns a best-effort payload instead of raising."""
    from services import llm_client
    from services import generation_service

    # Patch OllamaClient.generate to simulate connection failure
    monkeypatch.setattr(llm_client.OllamaClient, "generate", _raise_conn_error, raising=True)

    payload = await generation_service.generate_product_card(
        product_name="Мышь Logitech M185",
        features="2.4 ГГц, тихие клики",
        platform="ozon",
        tone="neutral",
    )
    assert isinstance(payload, dict)
    assert payload.get("title")
    assert payload.get("short_description")


class _FakeUser:
    def __init__(self, id):
        self.id = id


class _FakeWaitMsg:
    def __init__(self):
        self.edited_texts = []

    async def edit_text(self, text):
        self.edited_texts.append(text)


class _FakeMessage:
    def __init__(self, text: str, user_id: int = 1):
        self.text = text
        self.from_user = _FakeUser(user_id)
        self.answers = []
        self.last_wait = None

    async def answer(self, text: str, reply_markup=None):
        # For the first call in handler, we return a message-like object
        # that supports edit_text().
        wait = _FakeWaitMsg()
        self.last_wait = wait
        self.answers.append(text)
        return wait


class _FakeState:
    def __init__(self, data=None):
        self._data = data or {
            "platform": "ozon",
            "tone": "neutral",
            "length": "medium",
        }

    async def get_data(self):
        return dict(self._data)

    # Unused in this path, but present for completeness
    async def set_state(self, *_args, **_kwargs):
        return None


async def test_bot_handler_outputs_content_even_on_error(monkeypatch):
    # Patch product generation to simulate connection error at low level,
    # but service should produce fallback; we stub service to call real one.
    from services import llm_client
    from services import generation_service

    monkeypatch.setattr(llm_client.OllamaClient, "generate", _raise_conn_error, raising=True)

    from bot.handlers import on_input

    msg = _FakeMessage(
        text=(
            "Беспроводная мышь Logitech M185\n"
            "2.4 ГГц, тихие клики, до 12 мес работы"
        ),
        user_id=123,
    )
    state = _FakeState()

    await on_input(msg, state)

    # Handler should still edit the message with generated content
    assert msg.last_wait is not None
    assert msg.last_wait.edited_texts, "wait_msg.edit_text was not called"
    edited = msg.last_wait.edited_texts[-1]
    assert ("Title:" in edited) or ("Заголовок:" in edited)
