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
