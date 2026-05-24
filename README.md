# Telegram bot (webhook)

## Ishga tushirish (local)

1) Virtualenv:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2) Muhit o‘zgaruvchilari:

```bash
cp .env.example .env
```

`.env` ichida quyidagilarni to‘ldiring:
- `TELEGRAM_BOT_TOKEN`
- `RUN_MODE` (`webhook` yoki `polling`)
- `WEBHOOK_BASE_URL` (HTTPS domeningiz)
- `TELEGRAM_WEBHOOK_SECRET` (ixtiyoriy, tavsiya qilinadi)
- `ADMIN_IDS` (vergul bilan)
- `GEMINI_API_KEY` (AI uchun)
- `FINNHUB_API_KEY` (ICT market data uchun)
- `ICT_SYMBOL_MAP_JSON` (instrument mapping uchun)

3) Server:

```bash
python -m app.main
```

Agar domen/HTTPS bo‘lmasa, polling rejim:

```bash
python -m app.polling
```

## Telegram tomoni

- Webhook URL: `{WEBHOOK_BASE_URL}{WEBHOOK_PATH}` (default: `/webhook`)
- Agar `TELEGRAM_WEBHOOK_SECRET` qo‘ysangiz, so‘rovlar `X-Telegram-Bot-Api-Secret-Token` header orqali tekshiriladi

## Admin buyruqlari

- `/id`: chat_id/user_id ko‘rsatadi
- `/ict <symbol>`: D1/H4/H1 bias + key levels (FINNHUB_API_KEY va ICT_SYMBOL_MAP_JSON bo‘lsa)
- `/admin`
- `/status`
- `/setsource <chat_id>`: kuzatiladigan chat (kanal/guruh) id
- `/settarget <chat_id>`: forward qilinadigan chat id
- `/setkeywords <k1,k2,...>`: kalit so‘zlar
- `/mode <include|exclude>`

`include` bo‘lsa faqat kalit so‘z topilganda forward qiladi, `exclude` bo‘lsa kalit so‘z bor bo‘lsa forward qilmaydi.

## AI

- Private chatda `/chat` yuboring, keyin oddiy matn yozsangiz, bot Gemini orqali javob beradi (GEMINI_API_KEY bo‘lsa)

## Quiz

- `/quiznew` → keyin PDF yuboring (bot AI bilan savollarga ajratadi)
- `/quizzes` → mavjud quizlar ro‘yxati
- `/quizstart <id>` → quizni boshlash (inline tugmalar bilan)

## Docker

```bash
docker build -t tg-bot .
docker run --rm -p 8000:8000 --env-file .env tg-bot
```
