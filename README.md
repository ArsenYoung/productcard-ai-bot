# ProductCard AI Bot

Создаёт продающие описания карточек товаров (заголовок, описание, ключевые слова, SEO‑теги) под популярные площадки. MVP ориентирован на локальный запуск через Ollama без внешних расходов.

## Быстрый старт
- Установите Ollama и загрузите модель:
  - `ollama pull phi3:mini`
  - тест: `ollama run phi3:mini "say ok"`
- Скопируйте `.env.example` в `.env` и заполните `TELEGRAM_BOT_TOKEN`.
- Установите зависимости: `pip install -r requirements.txt`
- Запустите бота: `python -m bot.main`

Бот спросит платформу (Ozon/WB/Etsy/Shopify), затем попросит одним сообщением ввести название и характеристики товара, после чего вернёт сгенерированную карточку.

## Docker
Ниже два варианата запуска контейнера.

- Подготовка (общая):
  - Убедитесь, что на хосте запущен Ollama и загружена модель `phi3:mini`.
  - Скопируйте `.env.example` в `.env` и укажите `TELEGRAM_BOT_TOKEN`.
  - Соберите образ: `make build`

- Вариант A — Linux (host network):
  - Команда: `make run-hostnet`
  - Пояснение: контейнер использует сеть хоста, поэтому `LLM_BASE_URL` может оставаться `http://localhost:11434`.

- Вариант B — Кроссплатформенный (Mac/Windows/Linux):
  - В `.env` установите `LLM_BASE_URL=http://host.docker.internal:11434`
  - Запуск: `make run`
  - Примечание для Linux: цель `make run` добавляет `--add-host=host.docker.internal:host-gateway` (требуется Docker 20.10+). Дополнительно нужно, чтобы Ollama слушал не только `127.0.0.1`, а `0.0.0.0`.
    - systemd: `sudo systemctl edit ollama` и добавить:
      ```
      [Service]
      Environment="OLLAMA_HOST=0.0.0.0:11434"
      ```
      затем `sudo systemctl daemon-reload && sudo systemctl restart ollama`.
    - вручную: `OLLAMA_HOST=0.0.0.0 ollama serve`
  - Симптом неправильной настройки: ошибка подключения к `host.docker.internal:11434` из контейнера.

- Управление:
  - Логи: `make logs`
  - Остановить и удалить контейнер: `make stop`
  - Войти в контейнер: `make sh`

Контейнер ничего не слушает извне (бот использует long polling), проброс портов не требуется.

## Переменные окружения
- `TELEGRAM_BOT_TOKEN` — токен Telegram‑бота (обязателен)
- `LLM_MODEL` — модель Ollama, по умолчанию `phi3:mini`
- `LLM_BASE_URL` — `http://localhost:11434`
- `LLM_TEMPERATURE` — `0.6`
- `LLM_MAX_NEW_TOKENS` — `800`

## Документация
- План реализации: `docs/IMPLEMENTATION_PLAN.md`
- Дорожная карта версий: `docs/ROADMAP.md`

## Установка Ollama на Ubuntu
- Требования: Ubuntu 20.04+ (или совместимая), установлен `curl`.
- Установка (официальный скрипт):
  - `curl -fsSL https://ollama.com/install.sh | sh`
- Запуск службы (systemd):
  - Включить и запустить: `sudo systemctl enable --now ollama`
  - Статус: `systemctl status ollama`
  - Логи: `journalctl -u ollama -f`
- Альтернатива (локально в терминале):
  - Запустить сервер вручную: `ollama serve` (оставить работать), в другом терминале выполнять команды `ollama pull/run`.
- Проверка установки:
  - `ollama --version`
  - `curl http://localhost:11434/api/tags` (должен вернуть список моделей)
- Загрузка и тест модели:
  - `ollama pull phi3:mini`
  - `ollama run phi3:mini "say ok"`
- Примечания:
  - По умолчанию сервер слушает `http://localhost:11434`.
  - Если нет NVIDIA GPU — всё равно работает на CPU (рекомендуются компактные модели 3B–4B).
  - При ошибке порта/службы попробуйте ручной запуск `ollama serve` или перезапуск службы: `sudo systemctl restart ollama`.

## Статус
- Текущий этап — v0.2 (скелет Telegram‑бота на aiogram 3, генерация через Ollama). Без БД и экспорта файлов (войдут в 0.3).

## Обратная связь и задачи
- Идеи и улучшения предлагайте через задачи/тикеты. Релизы помечаем тегами `vX.Y.Z` (SemVer).
