# ProductCard AI Bot — План реализации (MVP)

Этот документ описывает цель, границы MVP, архитектуру, проектную структуру, логику диалогов, стратегию промптинга, модель данных, требования к конфигурации и развёртыванию, а также этапы работ и критерии приёмки.

## 1) Цель и ценностное предложение
- Создавать быстро продающие и SEO-оптимизированные описания карточек товаров под разные маркетплейсы (Ozon, Wildberries, Etsy, Shopify и др.).
- Упростить рутину продавцов: заголовок, описание, ключевые слова, SEO‑теги из одного запроса.
- Дать готовый рабочий инструмент для портфолио как коммерческий сервис.

## 2) Область MVP
- Поддержка платформ в интерфейсе: Ozon, Wildberries, Etsy, Shopify (на уровне выбора логики и подсказок; специфичные жёсткие правила платформ — как конфиг, который можно расширять).
- Генерация: заголовок, описание, ключевые слова, SEO‑теги на основе названия и характеристик товара.
- Выбор стиля: «продающий / лаконичный / экспертный» (опционально — один переключатель в MVP).
- Выбор длины: «короткое / среднее / полное».
- Экспорт результата: текстом в чате + файлы .txt и .csv.
- Хранение последних N (по умолчанию 5) генераций на пользователя в SQLite.
- Простая FSM (шаги: выбор платформы → ввод данных → выбор стиля/длины → генерация → экспорт/повтор).

Вне MVP (на будущее):
- Извлечение данных из фото (keywords → описание).
- Google Sheets API экспорт.
- Редактура с дообучением/шаблонизацией под конкретные магазины.

## 3) Технологический стек
- Telegram Bot: aiogram 3.x (FSM, inline‑кнопки, middlewares).
- NLP/LLM: бесплатная локальная модель phi-3-mini-4k-instruct (через Ollama или Hugging Face Transformers). Опционально — любой OpenAI‑совместимый бэкенд.
- Хранилище: SQLite (через `sqlite3`/`aiosqlite`), JSON‑кэш при необходимости.
- Конфигурация: `python-dotenv` (.env).
- Экспорт: стандартные I/O операции для .txt и .csv.
- Логирование: стандартный `logging` + ротация файлов (по желанию).

## 4) Архитектура и слои
- handlers/ — обработчики команд/кнопок, сценарная логика, FSM состояния.
- services/
  - generation_service.py — оркестрация генерации (сбор промпта, вызов LLM, пост‑обработка).
  - llm_client.py — низкоуровневый клиент к phi‑3 (через Ollama или Transformers) с единым интерфейсом.
  - export_service.py — формирование текстов, .txt и .csv.
- repositories/ (или storage/)
  - sqlite_repo.py — пользователи, сессии, генерации (CRUD с асинхронностью).
- keyboards/ — инлайн‑кнопки: платформа, стиль, длина, экспорт.
- states/ — FSM состояния (например, `GenerationStates`).
- config/
  - config.py — чтение .env, константы, профили маркетплейсов.
- utils/
  - validators.py — базовая валидация данных, ограничений длины и т. п.
  - text.py — общие текстовые хелперы (обрезка по лимиту, slug и т. п.).

Диаграмма на словах: Telegram ⟷ aiogram.handlers → services.generation_service → services.llm_client → phi‑3 → services.export_service → aiogram → Пользователь. Данные связываются через repositories.sqlite_repo.

## 5) Логика диалога (FSM)
Сценарий (минимум шагов, удобно пальцами):
1. /start → приветствие + выбор платформы [Ozon] [Wildberries] [Etsy] [Shopify].
2. После выбора платформы → запрос «Введи название и характеристики» (одно сообщение, свободный текст).
3. Запрос выбора стиля: [Продающий] [Лаконичный] [Экспертный].
4. Запрос длины: [Короткое] [Среднее] [Полное].
5. Генерация → отображение результата блоками: Заголовок, Описание, Ключевые слова, SEO‑теги.
6. Экспорт: [Отправить .txt] [Отправить .csv] [Сгенерировать заново] [Изменить платформу].

Обработка отмены: кнопка «↩️ Назад» на каждом шаге (или /cancel).
Троттлинг: ограничить частоту генераций на пользователя и общий rate (конфигурируемо).

## 6) Профили маркетплейсов (конфиг)
Создать словарь профилей с мягкими ограничениями и подсказками, чтобы не шить их в код:
```python
MARKETPLACE_PROFILES = {
  "Ozon": {
    "title_max": 120,
    "desc_target": "среднее",
    "keywords_sep": ", ",
    "locale": "ru",
    "style_hint": "деловой, понятный, без спама"
  },
  "Wildberries": {
    "title_max": 120,
    "desc_target": "среднее",
    "keywords_sep": ", ",
    "locale": "ru",
    "style_hint": "кратко, по делу, выгоды"
  },
  "Etsy": {
    "title_max": 140,
    "desc_target": "среднее",
    "keywords_sep": ", ",
    "locale": "en",
    "style_hint": "friendly, handmade, benefits"
  },
  "Shopify": {
    "title_max": 150,
    "desc_target": "среднее",
    "keywords_sep": ", ",
    "locale": "en",
    "style_hint": "conversion-focused, clean"
  }
}
```
Примечание: конкретные лимиты зависят от реальных правил платформ. В MVP — как «мягкие» цели и подсказки; жёсткая валидация — опционально.

## 7) Стратегия промптинга (phi‑3‑mini‑4k‑instruct)
phi‑3 — инструкционная causal‑LM (не чат‑модель в строгом смысле), поэтому используем одношаговый prompt с требованием строгого JSON‑вывода.

Формат обращения к модели:
- Инструкции: роли и ограничения (язык, стиль, длина, платформа, запреты).
- Вход: «название + характеристики» одной строкой от пользователя.
- Требование формата: строго один JSON‑объект без пояснений и бэктиков.

Требуемый формат ответа — JSON:
```json
{
  "title": "...",
  "description": "...",
  "keywords": ["...", "..."],
  "seo_tags": ["...", "..."]
}
```

Шаблон промпта (RU):
```
Ты — ассистент по созданию карточек товаров под маркетплейсы. Пиши на {locale}.
Стиль: {style}. Длина: {length}. Платформа: {platform} ({style_hint}).
Заголовок до ~{title_max} символов. Избегай запрещённых обещаний, спама, CAPS.
Верни СТРОГО один JSON‑объект со свойствами: title, description, keywords[], seo_tags[].
Без пояснений, без бэктиков, без префиксов. Если не уверен — сделай разумные допущения.

Ввод пользователя:
{title_and_attrs}
```

Рекомендованные параметры генерации:
- max_new_tokens: 600–800 (для «среднего» описания)
- temperature: 0.4–0.7
- top_p: 0.9
- stop: по необходимости (например, по двойному переводу строки после JSON)

Пост‑обработка:
- Валидация и безопасный парсинг JSON; при провале — повторная попытка с напоминанием «верни только JSON».
- Подрезка заголовка, если длина превышена профилем платформы.
- Нормализация и уникализация keywords/seo_tags.

Контроль ресурсов:
- Короткие, целевые подсказки; ограничение max_new_tokens.

### 7.1) Интеграция phi‑3 локально: варианты

Вариант A — Ollama (простой и удобный):
- Установка: по инструкции на сайте Ollama.
- Загрузка модели: `ollama pull phi3:mini` (соответствие phi‑3‑mini‑4k‑instruct).
- Тест запуска: `ollama run phi3:mini "Скажи 'ok'"`.
- Конфиг для бота:
  - `LLM_PROVIDER=ollama`
  - `LLM_MODEL=phi3:mini`
  - `LLM_BASE_URL=http://localhost:11434`
- HTTP запрос (без стрима):
```http
POST /api/generate HTTP/1.1
Host: localhost:11434
Content-Type: application/json

{
  "model": "phi3:mini",
  "prompt": "<сформированный промпт из раздела 7>",
  "stream": false,
  "options": { "temperature": 0.6, "num_predict": 800 }
}
```
- Ответ: поле `response` содержит текст; далее выполняем JSON‑парсинг.

Вариант B — Hugging Face Transformers (максимальный контроль):
- Зависимости: `pip install transformers accelerate torch` (+ по возможности `bitsandbytes` для 4‑бит на GPU).
- Модель/токенизатор: `microsoft/Phi-3-mini-4k-instruct`.
- Псевдокод инференса:
```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

name = "microsoft/Phi-3-mini-4k-instruct"
tok = AutoTokenizer.from_pretrained(name)
model = AutoModelForCausalLM.from_pretrained(
    name, torch_dtype=torch.float16, device_map="auto"
)

prompt = build_prompt(...)  # шаблон из раздела 7
inputs = tok(prompt, return_tensors="pt").to(model.device)
out = model.generate(
    **inputs,
    max_new_tokens=800,
    temperature=0.6,
    do_sample=True,
    top_p=0.9,
)
text = tok.decode(out[0], skip_special_tokens=True)
payload = safe_parse_json(text)
```
- Конфиг для бота: `LLM_PROVIDER=transformers`, `LLM_MODEL=microsoft/Phi-3-mini-4k-instruct`.

Производительность и ресурсы:
- CPU работает, но медленнее; лучше GPU при доступности.
- Уменьшайте `max_new_tokens` и `temperature` для ускорения и стабильности.

## 8) Модель данных (SQLite)
Таблицы (минимум):
- users
  - id INTEGER PK
  - tg_id INTEGER UNIQUE
  - username TEXT NULL
  - locale TEXT DEFAULT 'ru'
  - created_at DATETIME
- sessions
  - id INTEGER PK
  - user_id INTEGER FK → users.id
  - platform TEXT
  - style TEXT
  - length TEXT
  - created_at DATETIME
- generations
  - id INTEGER PK
  - session_id INTEGER FK → sessions.id
  - input_title TEXT
  - input_attrs TEXT
  - output_title TEXT
  - output_description TEXT
  - output_keywords TEXT (CSV или JSON)
  - output_seo_tags TEXT (CSV или JSON)
  - token_usage_prompt INTEGER NULL
  - token_usage_completion INTEGER NULL
  - created_at DATETIME

Индексы: users(tg_id), sessions(user_id, created_at DESC), generations(session_id, created_at DESC).
Политика хранения: держать последние 5 генераций на пользователя (фоновая очистка или при вставке).

## 9) Экспорт
- .txt: последовательность блоков с понятными заголовками.
- .csv: колонки [platform, style, length, input_title, input_attrs, output_title, output_description, keywords, seo_tags, created_at].
- Локальные файлы формируются в памяти и отправляются как документ.
- На будущее: Google Sheets API (табличная схема совпадает с .csv).

## 10) Проектная структура (папки/файлы)
```
project_root/
  bot.py                    # точка входа
  requirements.txt
  README.md
  .env.example
  config/
    config.py
  handlers/
    start.py
    generation.py
  keyboards/
    common.py
  services/
    llm_client.py
    generation_service.py
    export_service.py
  repositories/
    sqlite_repo.py
  states/
    generation_states.py
  utils/
    validators.py
    text.py
  data/
    migrations.sql          # схема БД
  docs/
    IMPLEMENTATION_PLAN.md
```

## 11) Конфигурация и переменные окружения
- BOT_TOKEN=... (токен Telegram)
- LLM_PROVIDER=ollama | transformers
- LLM_MODEL=phi3:mini (для Ollama) | microsoft/Phi-3-mini-4k-instruct (для Transformers)
- LLM_BASE_URL=http://localhost:11434 (если provider=ollama)
- LLM_MAX_NEW_TOKENS=800
- LLM_TEMPERATURE=0.6
- DB_PATH=./data/bot.db
- LOG_LEVEL=INFO
- RATE_LIMIT_PER_MIN=5
- ADMIN_IDS=123456789,987654321

Безопасность:
- Никогда не логировать сырые API‑ключи.
- Базовая защита от флуд/спама.

## 12) Тестирование
- Unit: генерация промпта, парсинг ответа, экспорт в .csv/.txt.
- Интеграционные: мок `llm_client` (заглушка) или локальный Ollama, сквозной сценарий FSM.
- Ручные E2E: основные ветки диалога, отмена, ошибки сети, большой ввод.

## 13) Логирование и наблюдаемость
- Старт/стоп бота, ошибки, таймауты, rate limit срабатывания.
- Техническая метрика: среднее время генерации, частота ошибок парсинга JSON.

## 14) Развёртывание
- Dockerfile + docker-compose для локалки.
- Запуск phi‑3 локально:
  - Вариант A (Ollama, рекомендуется для простоты):
    - Установка Ollama: см. официальный сайт.
    - Загрузка модели: `ollama pull phi3:mini` (вариант, соответствующий phi‑3‑mini‑4k‑instruct).
    - Тест: `ollama run phi3:mini "Скажи 'ok'"`.
    - HTTP API: `POST /api/generate` на `http://localhost:11434` с телом `{ "model": "phi3:mini", "prompt": "...", "options": { "temperature": 0.6, "num_predict": 800 } }`.
  - Вариант B (Transformers):
    - `pip install transformers accelerate torch` (и по необходимости: `pip install bitsandbytes` для 4‑бит на GPU).
    - Модель: `microsoft/Phi-3-mini-4k-instruct`.
    - Пример (упрощённо): загрузить токенизатор/модель, сгенерировать текст по шаблону промпта, распарсить JSON.
- Прод: любой VPS/PAAS (Render/Fly.io/Railway), переменные окружения, volume под SQLite.
- Грейсфул‑shutdown сигналов, авто‑рестарт (systemd или supervisor, если без PAAS).

## 15) Риски и меры
- Rate limit/стоимость LLM: для локальной phi‑3 — контроль токенов и кэширование; для удалённых API — троттлинг.
- Непарсибельный ответ: строгий JSON формат + повторная попытка с напоминанием «верни только JSON».
- Правила маркетплейсов: вынести в конфиг и документировать предположения.
- Производительность локальной модели: лимит max_new_tokens, фоновая генерация, опционально GPU/квантизация.

## 16) Дорожная карта (2–3 дня активной работы)
День 1:
- Инициализация проекта, структура, .env, конфиг, keyboards, states.
- FSM: /start → выбор платформы → ввод данных.
- Репозиторий SQLite + миграции; сохранение пользователей/сессий.

День 2:
- LLM клиент (phi‑3‑mini‑4k‑instruct через Ollama/Transformers) + generation_service, JSON‑формат, пост‑обработка, парсинг.
- Выбор стиля/длины, показ результата, экспорт .txt/.csv.
- Ограничение на 5 последних генераций на пользователя.

День 3:
- Логи, обработка ошибок/таймаутов, троттлинг.
- Юнит‑тесты ключевых частей, README с инструкциями запуска.
- Полировка UX: кнопки «назад», «сгенерировать заново», смена платформы.

## 17) Критерии приёмки (MVP)
- Бот отвечает на /start, предлагает платформы, принимает ввод, предлагает стиль/длину.
- По запросу генерирует валидный JSON и корректно отображает 4 блока: Заголовок, Описание, Ключевые слова, SEO‑теги.
- Экспортирует .txt и .csv файлы, которые корректно открываются.
- Сохраняет и показывает последние 5 генераций на пользователя (при необходимости отдельной командой /history или кнопкой).
- Ошибки и таймауты не ломают FSM, пользователь получает понятные сообщения.

## 18) Пример пользовательского сценария (RU, Ozon)
- Пользователь: /start
- Бот: «Выбери платформу: [Ozon] [Wildberries] [Etsy] [Shopify]»
- Пользователь: Ozon
- Бот: «Введи название и характеристики товара. Пример: Смарт‑часы Xiaomi Mi Band 8, влагозащита, AMOLED‑дисплей, Bluetooth 5.1»
- Пользователь: «Смарт‑часы Xiaomi Mi Band 8, влагозащита, AMOLED‑дисплей, Bluetooth 5.1»
- Бот: «Выбери стиль: [Продающий] [Лаконичный] [Экспертный]»
- Пользователь: «Продающий»
- Бот: «Выбери длину: [Короткое] [Среднее] [Полное]»
- Пользователь: «Среднее»
- Бот: генерирует и отправляет 4 блока + кнопки экспорта.

---

Следующий шаг: инициализировать репозиторий, создать каркас (папки/файлы), добавить .env.example и минимальный bot.py с /start и клавиатурой выбора платформы.
