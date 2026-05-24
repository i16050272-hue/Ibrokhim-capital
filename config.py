1 1
 
import os
2 2
 
from dataclasses import dataclass
3 3
 
 
4 4
 
 
5 5
 
def _getenv(name: str, default: str | None = None) -> str | None:
6 6
 
    value = os.getenv(name)
7 7
 
    if value is None or value == "":
8 8
 
        return default
9 9
 
    return value
10 10
 
 
11 11
 
 
12 12
 
def _parse_int(value: str | None) -> int | None:
13 13
 
    if value is None:
14 14
 
        return None
15 15
 
    try:
16 16
 
        return int(value)
17 17
 
    except ValueError:
18 18
 
        return None
19 19
 
 
20 20
 
 
21 21
 
def _parse_int_list(value: str | None) -> list[int]:
22 22
 
    if not value:
23 23
 
        return []
24 24
 
    out: list[int] = []
25 25
 
    for part in value.split(","):
26 26
 
        part = part.strip()
27 27
 
        if not part:
28 28
 
            continue
29 29
 
        try:
30 30
 
            out.append(int(part))
31 31
 
        except ValueError:
32 32
 
            continue
33 33
 
    return out
34 34
 
 
35 35
 
 
36 36
 
@dataclass(frozen=True)
37 37
 
class Settings:
38 38
 
    telegram_bot_token: str
39 39
 
    webhook_base_url: str
40 40
 
    webhook_path: str
41 41
 
    webhook_secret_token: str | None
42 42
 
    admins: list[int]
43 43
 
    database_path: str
44
+
    gemini_api_key: str | None
45
+
    gemini_model: str
46
+
    quiz_max_questions: int
44 47
 
 
45 48
 
 
46 49
 
def load_settings() -> Settings:
47 50
 
    token = _getenv("TELEGRAM_BOT_TOKEN")
48 51
 
    if not token:
49 52
 
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
50 53
 
 
51 54
 
    base_url = _getenv("WEBHOOK_BASE_URL")
52 55
 
    if not base_url:
53 56
 
        raise RuntimeError("WEBHOOK_BASE_URL is required")
54 57
 
 
55 58
 
    webhook_path = _getenv("WEBHOOK_PATH", "/webhook") or "/webhook"
56 59
 
    if not webhook_path.startswith("/"):
57 60
 
        webhook_path = f"/{webhook_path}"
58 61
 
 
59 62
 
    return Settings(
60 63
 
        telegram_bot_token=token,
61 64
 
        webhook_base_url=base_url.rstrip("/"),
62 65
 
        webhook_path=webhook_path,
63 66
 
        webhook_secret_token=_getenv("TELEGRAM_WEBHOOK_SECRET"),
64 67
 
        admins=_parse_int_list(_getenv("ADMIN_IDS")),
65 68
 
        database_path=_getenv("DATABASE_PATH", "bot.db") or "bot.db",
69
+
        gemini_api_key=_getenv("GEMINI_API_KEY"),
70
+
        gemini_model=_getenv("GEMINI_MODEL", "gemini-1.5-flash") or "gemini-1.5-flash",
71
+
        quiz_max_questions=_parse_int(_getenv("QUIZ_MAX_QUESTIONS")) or 10,
66 72
 
    )
1 1
 
import os
2 2
 
from dataclasses import dataclass
3 3
 
 
4 4
 
 
5 5
 
def _getenv(name: str, default: str | None = None) -> str | None:
6 6
 
    value = os.getenv(name)
7 7
 
    if value is None or value == "":
8 8
 
        return default
9 9
 
    return value
10 10
 
 
11 11
 
 
12 12
 
def _parse_int(value: str | None) -> int | None:
13 13
 
    if value is None:
14 14
 
        return None
15 15
 
    try:
16 16
 
        return int(value)
17 17
 
    except ValueError:
18 18
 
        return None
19 19
 
 
20 20
 
 
21 21
 
def _parse_int_list(value: str | None) -> list[int]:
22 22
 
    if not value:
23 23
 
        return []
24 24
 
    out: list[int] = []
25 25
 
    for part in value.split(","):
26 26
 
        part = part.strip()
27 27
 
        if not part:
28 28
 
            continue
29 29
 
        try:
30 30
 
            out.append(int(part))
31 31
 
        except ValueError:
32 32
 
            continue
33 33
 
    return out
34 34
 
 
35 35
 
 
36 36
 
@dataclass(frozen=True)
37 37
 
class Settings:
38 38
 
    telegram_bot_token: str
39 39
 
    webhook_base_url: str | None
40 40
 
    webhook_path: str
41 41
 
    webhook_secret_token: str | None
42 42
 
    admins: list[int]
43 43
 
    database_path: str
44 44
 
    gemini_api_key: str | None
45 45
 
    gemini_model: str
46 46
 
    quiz_max_questions: int
47 47
 
    run_mode: str
48
+
    finnhub_api_key: str | None
49
+
    ict_symbol_map_json: str | None
48 50
 
 
49 51
 
 
50 52
 
def load_settings() -> Settings:
51 53
 
    token = _getenv("TELEGRAM_BOT_TOKEN")
52 54
 
    if not token:
53 55
 
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
54 56
 
 
55 57
 
    run_mode = (_getenv("RUN_MODE", "webhook") or "webhook").strip().lower()
56 58
 
    if run_mode not in {"webhook", "polling"}:
57 59
 
        run_mode = "webhook"
58 60
 
 
59 61
 
    base_url = _getenv("WEBHOOK_BASE_URL")
60 62
 
    if run_mode == "webhook" and not base_url:
61 63
 
        raise RuntimeError("WEBHOOK_BASE_URL is required for webhook mode")
62 64
 
 
63 65
 
    webhook_path = _getenv("WEBHOOK_PATH", "/webhook") or "/webhook"
64 66
 
    if not webhook_path.startswith("/"):
65 67
 
        webhook_path = f"/{webhook_path}"
66 68
 
 
67 69
 
    return Settings(
68 70
 
        telegram_bot_token=token,
69 71
 
        webhook_base_url=base_url.rstrip("/") if base_url else None,
70 72
 
        webhook_path=webhook_path,
71 73
 
        webhook_secret_token=_getenv("TELEGRAM_WEBHOOK_SECRET"),
72 74
 
        admins=_parse_int_list(_getenv("ADMIN_IDS")),
73 75
 
        database_path=_getenv("DATABASE_PATH", "bot.db") or "bot.db",
74 76
 
        gemini_api_key=_getenv("GEMINI_API_KEY"),
75 77
 
        gemini_model=_getenv("GEMINI_MODEL", "gemini-1.5-flash") or "gemini-1.5-flash",
76 78
 
        quiz_max_questions=_parse_int(_getenv("QUIZ_MAX_QUESTIONS")) or 10,
77 79
 
        run_mode=run_mode,
80
+
        finnhub_api_key=_getenv("FINNHUB_API_KEY"),
81
+
        ict_symbol_map_json=_getenv("ICT_SYMBOL_MAP_JSON"),
78 82
 
    )
