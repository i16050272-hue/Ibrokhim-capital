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
```1 1
 
# Telegram bot (webhook)
2 2
 
 
3 3
 
## Ishga tushirish (local)
4 4
 
 
5 5
 
1) Virtualenv:
6 6
 
 
7 7
 
```bash
8 8
 
python -m venv .venv
9 9
 
. .venv/bin/activate
10 10
 
pip install -r requirements.txt
11 11
 
```
12 12
 
 
13 13
 
2) Muhit o‘zgaruvchilari:
14 14
 
 
15 15
 
```bash
16 16
 
cp .env.example .env
17 17
 
```
18 18
 
 
19 19
 
`.env` ichida quyidagilarni to‘ldiring:
20 20
 
- `TELEGRAM_BOT_TOKEN`
21 21
 
- `RUN_MODE` (`webhook` yoki `polling`)
22 22
 
- `WEBHOOK_BASE_URL` (HTTPS domeningiz)
23 23
 
- `TELEGRAM_WEBHOOK_SECRET` (ixtiyoriy, tavsiya qilinadi)
24 24
 
- `ADMIN_IDS` (vergul bilan)
25 25
 
- `GEMINI_API_KEY` (AI uchun)
26
+
- `FINNHUB_API_KEY` (ICT market data uchun)
27
+
- `ICT_SYMBOL_MAP_JSON` (instrument mapping uchun)
26 28
 
 
27 29
 
3) Server:
28 30
 
 
29 31
 
```bash
30 32
 
python -m app.main
31 33
 
```
32 34
 
 
33 35
 
Agar domen/HTTPS bo‘lmasa, polling rejim:
34 36
 
 
35 37
 
```bash
36 38
 
python -m app.polling
37 39
 
```
38 40
 
 
39 41
 
## Telegram tomoni
40 42
 
 
41 43
 
- Webhook URL: `{WEBHOOK_BASE_URL}{WEBHOOK_PATH}` (default: `/webhook`)
42 44
 
- Agar `TELEGRAM_WEBHOOK_SECRET` qo‘ysangiz, so‘rovlar `X-Telegram-Bot-Api-Secret-Token` header orqali tekshiriladi
43 45
 
 
44 46
 
## Admin buyruqlari
45 47
 
 
46 48
 
- `/id`: chat_id/user_id ko‘rsatadi
49
+
- `/ict <symbol>`: D1/H4/H1 bias + key levels (FINNHUB_API_KEY va ICT_SYMBOL_MAP_JSON bo‘lsa)
47 50
 
- `/admin`
48 51
 
- `/status`
49 52
 
- `/setsource <chat_id>`: kuzatiladigan chat (kanal/guruh) id
50 53
 
- `/settarget <chat_id>`: forward qilinadigan chat id
51 54
 
- `/setkeywords <k1,k2,...>`: kalit so‘zlar
52 55
 
- `/mode <include|exclude>`
53 56
 
 
54 57
 
`include` bo‘lsa faqat kalit so‘z topilganda forward qiladi, `exclude` bo‘lsa kalit so‘z bor bo‘lsa forward qilmaydi.
55 58
 
 
56 59
 
## AI
57 60
 
 
58 61
 
- Private chatda `/chat` yuboring, keyin oddiy matn yozsangiz, bot Gemini orqali javob beradi (GEMINI_API_KEY bo‘lsa)
59 62
 
 
60 63
 
## Quiz
61 64
 
 
62 65
 
- `/quiznew` → keyin PDF yuboring (bot AI bilan savollarga ajratadi)
63 66
 
- `/quizzes` → mavjud quizlar ro‘yxati
64 67
 
- `/quizstart <id>` → quizni boshlash (inline tugmalar bilan)
65 68
 
 
66 69
 
## Docker
67 70
 
 
68 71
 
```bash
69 72
 
docker build -t tg-bot .
70 73
 
docker run --rm -p 8000:8000 --env-file .env tg-bot
71 74
 
```
