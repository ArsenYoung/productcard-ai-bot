# ProductCard AI — v0.1

Локальный генератор карточек товара (заголовок, краткое описание и пункты) через Ollama. Выход — строгий JSON. Минимальный CLI для демо.

## Установка
- Установите Ollama и загрузите модель:
  - `ollama pull phi3:mini`
  - тест: `ollama run phi3:mini "say ok"`
- Python 3.11+; установите зависимости: `pip install -r requirements.txt`
- Скопируйте `.env.example` в `.env` при необходимости и скорректируйте параметры LLM (по умолчанию подходят: `http://localhost:11434`, `phi3:mini`).

## Запуск CLI
Пример:

```
python -m cli "Беспроводная мышь Logitech M185" \
  --features "2.4 ГГц, тихие клики, до 12 мес работы" \
  --platform ozon --tone neutral
```

На выходе печатается JSON формата:

```
{
  "title": "...",
  "short_description": "...",
  "bullets": ["...", "..."]
}
```

## Документация
- Дорожная карта версий: `docs/ROADMAP.md` (текущий статус: v0.1)

В следующих версиях планируется Telegram‑бот, экспорт файлов и хранилище (см. ROADMAP).
