
 
import os
2 2
 
 
3 3
 
from aiohttp import web
4 4
 
from telegram import Update
5 5
 
from telegram.ext import Application, ApplicationBuilder
6 6
 
 
7 7
 
from .config import load_settings
8
+
from .ai import GeminiClient
8 9
 
from .handlers import setup_application
9 10
 
from .storage import SettingsStore
10 11
 
 
11 12
 
 
12 13
 
settings = load_settings()
13 14
 
store = SettingsStore(settings.database_path)
14 15
 
 
15 16
 
application: Application = ApplicationBuilder().token(settings.telegram_bot_token).build()
16
-
setup_application(application, set(settings.admins), store)
17
+
gemini = (
18
+
    GeminiClient(settings.gemini_api_key, settings.gemini_model)
19
+
    if settings.gemini_api_key
20
+
    else None
21
+
)
22
+
setup_application(application, set(settings.admins), store, gemini, settings.quiz_max_questions)
17 23
 
 
18 24
 
 
19 25
 
async def health(_: web.Request) -> web.Response:
20 26
 
    return web.json_response({"ok": True})
21 27
 
 
22 28
 
 
23 29
 
async def telegram_webhook(request: web.Request) -> web.Response:
24 30
 
    if settings.webhook_secret_token:
25 31
 
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
26 32
 
        if header != settings.webhook_secret_token:
27 33
 
            return web.Response(status=401, text="invalid secret token")
28 34
 
 
29 35
 
    data = await request.json()
30 36
 
    update = Update.de_json(data, application.bot)
31 37
 
    await application.process_update(update)
32 38
 
    return web.json_response({"ok": True})
33 39
 
 
34 40
 
 
35 41
 
async def on_startup(_: web.Application) -> None:
36 42
 
    await application.initialize()
37 43
 
    await application.start()
38 44
 
    webhook_url = f"{settings.webhook_base_url}{settings.webhook_path}"
39 45
 
    await application.bot.set_webhook(
40 46
 
        url=webhook_url,
41 47
 
        secret_token=settings.webhook_secret_token,
42 48
 
        drop_pending_updates=False,
43 49
 
    )
44 50
 
 
45 51
 
 
46 52
 
async def on_cleanup(_: web.Application) -> None:
47 53
 
    await application.bot.delete_webhook(drop_pending_updates=False)
48 54
 
    await application.stop()
49 55
 
    await application.shutdown()
50 56
 
 
51 57
 
 
52 58
 
app = web.Application()
53 59
 
app.router.add_get("/health", health)
54 60
 
app.router.add_post(settings.webhook_path, telegram_webhook)
55 61
 
app.on_startup.append(on_startup)
56 62
 
app.on_cleanup.append(on_cleanup)
57 63
 
 
58 64
 
 
59 65
 
def main() -> None:
60 66
 
    port = int(os.getenv("PORT", "8000"))
61 67
 
    web.run_app(app, host="0.0.0.0", port=port)
62 68
 
 
63 69
 
 
64 70
 
if __name__ == "__main__":
65 71
 
    main()
1 1
 
import os
2 2
 
 
3 3
 
from aiohttp import web
4 4
 
from telegram import Update
5 5
 
from telegram.ext import Application, ApplicationBuilder
6 6
 
 
7 7
 
from .config import load_settings
8 8
 
from .ai import GeminiClient
9 9
 
from .handlers import setup_application
10
+
from .market_data import FinnhubClient, parse_symbol_map
10 11
 
from .storage import SettingsStore
11 12
 
 
12 13
 
 
13 14
 
settings = load_settings()
14 15
 
store = SettingsStore(settings.database_path)
15 16
 
 
16 17
 
application: Application = ApplicationBuilder().token(settings.telegram_bot_token).build()
17 18
 
gemini = (
18 19
 
    GeminiClient(settings.gemini_api_key, settings.gemini_model)
19 20
 
    if settings.gemini_api_key
20 21
 
    else None
21 22
 
)
22
-
setup_application(application, set(settings.admins), store, gemini, settings.quiz_max_questions)
23
+
finnhub = FinnhubClient(settings.finnhub_api_key) if settings.finnhub_api_key else None
24
+
ict_symbols = parse_symbol_map(settings.ict_symbol_map_json)
25
+
setup_application(
26
+
    application,
27
+
    set(settings.admins),
28
+
    store,
29
+
    gemini,
30
+
    settings.quiz_max_questions,
31
+
    finnhub,
32
+
    ict_symbols,
33
+
)
23 34
 
 
24 35
 
 
25 36
 
async def health(_: web.Request) -> web.Response:
26 37
 
    return web.json_response({"ok": True})
27 38
 
 
28 39
 
 
29 40
 
async def telegram_webhook(request: web.Request) -> web.Response:
30 41
 
    if settings.webhook_secret_token:
31 42
 
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
32 43
 
        if header != settings.webhook_secret_token:
33 44
 
            return web.Response(status=401, text="invalid secret token")
34 45
 
 
35 46
 
    data = await request.json()
36 47
 
    update = Update.de_json(data, application.bot)
37 48
 
    await application.process_update(update)
38 49
 
    return web.json_response({"ok": True})
39 50
 
 
40 51
 
 
41 52
 
async def on_startup(_: web.Application) -> None:
42 53
 
    await application.initialize()
43 54
 
    await application.start()
44 55
 
    if not settings.webhook_base_url:
45 56
 
        raise RuntimeError("WEBHOOK_BASE_URL is required for webhook mode")
46 57
 
    webhook_url = f"{settings.webhook_base_url}{settings.webhook_path}"
47 58
 
    await application.bot.set_webhook(
48 59
 
        url=webhook_url,
49 60
 
        secret_token=settings.webhook_secret_token,
50 61
 
        drop_pending_updates=False,
51 62
 
    )
52 63
 
 
53 64
 
 
54 65
 
async def on_cleanup(_: web.Application) -> None:
55 66
 
    await application.bot.delete_webhook(drop_pending_updates=False)
56 67
 
    await application.stop()
57 68
 
    await application.shutdown()
58 69
 
 
59 70
 
 
60 71
 
app = web.Application()
61 72
 
app.router.add_get("/health", health)
62 73
 
app.router.add_post(settings.webhook_path, telegram_webhook)
63 74
 
app.on_startup.append(on_startup)
64 75
 
app.on_cleanup.append(on_cleanup)
65 76
 
 
66 77
 
 
67 78
 
def main() -> None:
68 79
 
    port = int(os.getenv("PORT", "8000"))
69 80
 
    web.run_app(app, host="0.0.0.0", port=port)
70 81
 
 
71 82
 
 
72 83
 
if __name__ == "__main__":
73 84
 
 bl   main()
