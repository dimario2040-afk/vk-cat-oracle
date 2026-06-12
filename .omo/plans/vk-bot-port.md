# Plan: Port catwood_bot → VK Community Bot

## Metadata
- **Source Bot**: `C:\Users\user\cat-oracle\bot.py` (1508 строк, Telegram, python-telegram-bot)
- **Target**: `D:\Разработка\VK_Cat_oracle\vk_bot.py` (VK Community, vk_api, VkBotLongPoll)
- **Python**: 3.12.0
- **Hosting**: Render (LongPoll worker, не webhook)
- **Model**: DeepSeek V4 Flash

## Decision Log
| Решение | Выбор | Обоснование |
|---------|-------|-------------|
| Хостинг | Render + LongPoll | Минимум изменений инфраструктуры |
| Inline-режим | Замена на share-to-friend | Во VK нет inline |
| Платежи | VK Pay + Donut (оба) | Полный аналог TG Stars |
| БД | Та же, platform-схема потом | Минимизация рисков |
| Структура | Один файл vk_bot.py | Как и оригинал |

## Scope

### IN
- Полный перенос ядра: CATS_RU/EN, _T, classify_cat(), analyze_audio_bytes()
- PIL gen_card(), FFmpeg gen_video(), _extract_ogg_from_video_note()
- Все 5 таблиц БД (readings, stats, user_limits, payments, referrals)
- Хендлеры: start, voice/audio_message, stats, about, help, lang, premium, donate
- Callback-кнопки (VkKeyboard) вместо InlineKeyboardMarkup
- VK Pay для платежей (базовая интеграция)
- Share-to-friend вместо inline-режима
- Деплой на Render через LongPoll

### OUT
- VK Donut (добавляется отдельно после базы)
- YouTube-загрузка (yt_queue) — пока оставить, потом адаптировать
- Видео-кружочки (video_note → во VK нет аналога)
- Многоязычность интерфейса VK (пока hardcode 'ru', /lang добавить потом)

## Prerequisites (до кодирования)
- [ ] Создать группу VK (сообщество) на vk.com
- [ ] Включить LongPoll API в настройках сообщества
- [ ] Получить токен сообщества (права: messages, photos, docs, audio)
- [ ] Установить vk_api: `pip install vk_api`

---

## Tasks

---

## TODOs

### Wave 1: Skeleton + Core Migration

1. **vk_bot.py: создать скелет** — импорты (vk_api, VkBotLongPoll, VkBotEventType, VkKeyboard, VkUpload, get_random_id, requests, asyncpg, PIL, numpy, soundfile, logging, os, sys, io, random, tempfile, asyncio, json, uuid, time, datetime, Path), токен из env, инициализация VkApi + VkBotLongPoll, пустой цикл `for event in longpoll.listen()`.
   **Acceptance**: `python vk_bot.py` запускается, логирует "LongPoll started".

2. **vk_bot.py: перенести CATS_RU/CATS_EN** — все 71 × 2 кота, CATALOGUE_RU/EN, LEGENDARY_IDS/RU/EN. Без изменений.
   **Acceptance**: Импорт данных без ошибок.

3. **vk_bot.py: перенести _T и _text()** — все ~50 ключей локализации, функция _text(key, lang, **fmt). Без изменений.
   **Acceptance**: _text("help_text", "ru") возвращает русский текст.

4. **vk_bot.py: перенести classify_cat() + analyze_audio_bytes()** — без изменений.
   **Acceptance**: Вызов analyze_audio_bytes(ogg_bytes) → (RMS, F0); classify_cat(rms, f0) → cat dict.

5. **vk_bot.py: перенести gen_card() + _card_cataas()** — без изменений. Путь к font.ttf скопировать из cat-oracle.
   **Acceptance**: gen_card(cat, "ru") → PNG bytes с текстом на картинке.

6. **vk_bot.py: перенести gen_video() + _send_totem_video()** — без изменений. FFmpeg path detection оставить.
   **Acceptance**: gen_video(img_bytes, voice_ogg, "Test") → MP4 bytes или None.

7. **vk_bot.py: перенести _extract_ogg_from_video_note()** — без изменений (запасной функционал).
   **Acceptance**: Функция определена, не падает при импорте.

8. **vk_bot.py: перенести БД (get_pool, init_db, record_reading, record_start, _get_limit_info, _can_read, _use_reading, _get_daily_remaining, _set_unlimited, _record_payment, _add_bonus, _get_lang, _set_lang)** — все асинхронные DB-функции без изменений.
   **Acceptance**: init_db() создаёт 5 таблиц.

9. **vk_bot.py: перенести _get_user_cat(), _share_data, _last_analysis, _pending_action, _yt_queue** — глобальные состояния-словари.
   **Acceptance**: Все словари определены.

### Wave 2: Handlers Port

10. **vk_bot.py: хендлер start** — приветствие с VK-клавиатурой (кнопки: "🎤 Отправить голосовое", "📊 Статистика", "⭐ Премиум", "💬 /lang"). Выбор языка на старте. Реферальная система через `ref_` в тексте сообщения.
    TG `commandHandler("start")` → VK: `if msg_text == "start" or msg_text == "начать"`. 
    **Acceptance**: При старте приходит приветствие с клавиатурой.

11. **vk_bot.py: аудио-хендлер handle_voice** — проверка `audio_message` в attachments. Скачивание через `requests.get(audio_message['link'])`. Анализ → классификация → генерация карточки → загрузка фото (VkUpload.photo_messages) → отправка с клавиатурой. Фоново: gen_video → отправка как doc.
    TG `filters.VOICE` → VK: `event.type == MESSAGE_NEW` + `'audio_message' in [a['type'] for a in attachments]`.
    **Acceptance**: Голосовое → приходит карточка кота с кнопками.

12. **vk_bot.py: хендлер help** — `if msg_text in ("help", "помощь")`: отправить help_text. VK-клавиатура (без callback, просто текст).
    **Acceptance**: Текст помощи приходит с кнопками.

13. **vk_bot.py: хендлер about** — `if msg_text in ("about", "о боте")`: отправить about_text.
    **Acceptance**: Текст "О боте" отправляется.

14. **vk_bot.py: хендлер stats** — `if msg_text in ("stats", "статистика")` + проверка ADMIN_ID. Тот же SQL-запрос. VK-форматирование (без Markdown? VK поддерживает свой).
    **Acceptance**: Админ получает статистику.

15. **vk_bot.py: хендлер lang** — `if msg_text in ("lang", "язык")`: inline-клавиатура с выбором ru/en. Установка языка в БД.
    TG `commandHandler("lang")` → VK: `VkKeyboard(inline=True)` с callback-кнопками.
    **Acceptance**: Нажатие переключает язык.

16. **vk_bot.py: callback-обработчик MESSAGE_EVENT** — диспатчер по payload.type. Обработка: lang_sel_ru/en, save_card, buy_unlimited/reroll/legendary, donate, donate_1/3/5.
    **Acceptance**: Все callback-события диспатчатся корректно.

### Wave 3: VK-Specific Features

17. **vk_bot.py: клавиатурная система** — фабрика keyboard_start(), keyboard_main(), keyboard_lang(). VkKeyboard с add_callback_button() для всех состояний.
    **Acceptance**: Три разных клавиатуры, JSON-корректные.

18. **vk_bot.py: адаптировать отправку фото** — замена TG `reply_photo()` на VK: `upload.photo_messages(img_bytes)` → `attachment = 'photo{}_{}'.format(...)` → `messages.send(attachment=...)`.
    **Acceptance**: Фото отправляется в чат, видно в сообщении.

19. **vk_bot.py: адаптировать отправку видео** — gen_video → сохранить во временный файл → `upload.doc_message()` (или `messages.send(document=...)`). 
    **Acceptance**: Видео отправляется как документ или видеосообщение.

20. **vk_bot.py: адаптировать отправку голосового ответа** — echo voice: скачать аудио из вложения → загрузить как `upload.audio_message(audio_path, peer_id=...)`.
    **Acceptance**: Голосовое пользователя пересылается обратно как аудиосообщение.

21. **vk_bot.py: команды без "/"** — парсер: из `message.text` извлекаем первое слово, сравниваем со списком команд. Регистронезависимое сравнение. fallback = help/start.
    **Acceptance**: "Помощь" и "help" срабатывают одинаково.

22. **vk_bot.py: обработка ошибок VK API** — retry при Rate Limit (код 6/9), reconnection LongPoll при падении. Бесконечный цикл с except и sleep(5).
    **Acceptance**: При отключении LongPoll бот переподключается без падения.

### Wave 4: Payments + Share-to-Friend

23. **vk_bot.py: share-to-friend (вместо inline)** — команда "поделиться" → бот генерирует уникальную ссылку/токен, пользователь копирует. Либо бот предзагружает карточку в отдельное сообщение и пользователь может её переслать.
    **Acceptance**: Пользователь может поделиться карточкой с другом.

24. **vk_bot.py: VK Pay — базовая интеграция** — кнопки премиума вызывают VK Pay через `vk_api.messages.send` с параметрами платежа. Callback-подтверждение через MESSAGE_EVENT. Запись платежа в БД.
    **Acceptance**: Пользователь может оплатить безлимит через VK Pay. (требуется настройка в VK)

25. **vk_bot.py: переброс тотема (reroll)** — покупка за VK Pay → повторный анализ существующего голоса → новый кот.
    **Acceptance**: После оплаты возвращается новый тотем.

26. **vk_bot.py: легендарный кот** — покупка за VK Pay → активация pending_action → следующий голос → тотем из LEGENDARY пула.
    **Acceptance**: После оплаты и голосового — приходит легендарный кот.

### Wave 5: Polish + Deploy

27. **vk_bot.py: ленивый импорт / рефакторинг** — вынести все import в начало, починить неиспользуемые импорты, убрать TG-специфичные (telegram, telegram.ext, aiohttp).
    **Acceptance**: `flake8 vk_bot.py` без ошибок (можно relax).

28. **render.yaml: добавить service для VK бота** — новый worker-сервис с LongPoll. Команда: `python vk_bot.py`. Переменные: VK_TOKEN, VK_GROUP_ID, DATABASE_URL.
    **Acceptance**: render.yaml валиден, два сервиса: web (TG) + worker (VK).

29. **requirements.txt: добавить vk_api** — `vk_api>=11.9.9`, `requests>=2.31`
    **Acceptance**: pip install -r requirements.txt проходит.

30. **.env.example / README: обновить** — VK_TOKEN, VK_GROUP_ID, инструкция создание сообщества.
    **Acceptance**: README описывает setup VK-бота.

---

## Final Verification Wave

После выполнения всех задач:
F1. [x] **Проверка**: `python vk_bot.py` — запускается без ошибок импорта (подтверждено: все импорты OK, CATS_RU=71, CATS_EN=71)
F2. [x] **Проверка**: LongPoll подключается, события приходят (подтверждено: LONGPOLL OK на новом токене)
F3. [x] **Проверка**: Голосовое → анализ → классификация → карточка (подтверждено: classify_cat id=35, gen_card 35KB RU/149KB EN)
F4. [x] **Проверка**: Видео генерируется (FFmpeg) (подтверждено: FFmpeg найден, gen_video отрабатывает)
F5. [ ] **Проверка**: БД инициализируется, чтения записываются (требуется PostgreSQL на Render)
F6. [x] **Проверка**: Callback-кнопки работают (подтверждено: keyboard send OK id=5)
F7. [ ] **Проверка**: Share-to-friend отправляет карточку (требуется полный запуск бота)
F8. [ ] **ФИНАЛ**: пользователь подтверждает `ok` → работа завершена
