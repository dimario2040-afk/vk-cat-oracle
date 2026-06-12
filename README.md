# CatWood VK Bot

Telegram → VK порт бота «Кото-печенька». Слушает голосовые сообщения, анализирует акустику (RMS + F0), подбирает кота-тотема (71 шт), рисует карточку (PIL), делает видео (FFmpeg).

## Структура

| Файл | Описание |
|------|----------|
| `vk_bot.py` | Основной бот (VK LongPoll, vk_api) |
| `bot.py` | Оригинальный Telegram-бот (1508 строк) |
| `config.py` | Конфиг Telegram-бота |
| `requirements-vk.txt` | Зависимости VK-бота |
| `requirements.txt` | Зависимости Telegram-бота |
| `render.yaml` | Деплой на Render (2 сервиса) |
| `image/` | 71 изображение котов-тотемов |
| `font.ttf` | Шрифт для PIL-карточек |

## Установка

```powershell
pip install -r requirements-vk.txt
```

## Настройка сообщества VK

1. Создать/выбрать группу на vk.com
2. **Управление → Работа с API → Ключи доступа** — создать токен (права: messages, photos, docs)
3. **Управление → Работа с API → Long Poll API** — включить, отметить «Входящие сообщения»
4. **Управление → Сообщения → Сообщения сообщества** — включить
5. **Управление → Сообщения → Настройки для бота** — включить

## Запуск

```powershell
$env:VK_TOKEN="ваш_токен"
$env:VK_GROUP_ID="id_группы"
$env:ADMIN_ID="ваш_vk_id"
python vk_bot.py
```

Или через `.env`:

```
VK_TOKEN=...
VK_GROUP_ID=...
ADMIN_ID=...
```

## Команды (в чате бота)

| Команда | Описание |
|---------|----------|
| начать / start | Стартовое приветствие |
| помощь / help | Справка |
| о боте / about | О проекте |
| статистика / stats | Статистика (только админ) |
| премиум / premium | Premium-функции |
| lang / язык | Сменить язык |

## Деплой на Render

В `render.yaml` два сервиса:
- **cat-oracle** — Telegram-бот (web)
- **cat-oracle-vk** — VK-бот (worker)

Переменные окружения для VK-сервиса: `VK_TOKEN`, `VK_GROUP_ID`, `ADMIN_ID`, `DATABASE_URL`.

## Технологии

- Python 3.12
- vk_api + VkBotLongPoll
- asyncpg (PostgreSQL)
- Pillow (PIL) — генерация карточек
- FFmpeg — генерация видео
- numpy + soundfile — анализ звука

## Лицензия

MIT
