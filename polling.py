
 
from telegram.ext import Application, ApplicationBuilder
2 2
 
 
3 3
 
from .ai import GeminiClient
4 4
 
from .config import load_settings
5 5
 
from .handlers import setup_application
6
+
from .market_data import FinnhubClient, parse_symbol_map
6 7
 
from .storage import SettingsStore
7 8
 
 
8 9
 
 
9 10
 
def main() -> None:
10 11
 
    settings = load_settings()
11 12
 
    store = SettingsStore(settings.database_path)
12 13
 
    app: Application = ApplicationBuilder().token(settings.telegram_bot_token).build()
13 14
 
    gemini = (
14 15
 
        GeminiClient(settings.gemini_api_key, settings.gemini_model)
15 16
 
        if settings.gemini_api_key
16 17
 
        else None
17 18
 
    )
18
-
    setup_application(app, set(settings.admins), store, gemini, settings.quiz_max_questions)
19
+
    finnhub = FinnhubClient(settings.finnhub_api_key) if settings.finnhub_api_key else None
20
+
    ict_symbols = parse_symbol_map(settings.ict_symbol_map_json)
21
+
    setup_application(
22
+
        app,
23
+
        set(settings.admins),
24
+
        store,
25
+
        gemini,
26
+
        settings.quiz_max_questions,
27
+
        finnhub,
28
+
        ict_symbols,
29
+
    )
19 30
 
    app.run_polling(drop_pending_updates=False)
20 31
 
 
21 32
 
 
22 33
 
if __name__ == "__main__":
23 34
 
    main()
