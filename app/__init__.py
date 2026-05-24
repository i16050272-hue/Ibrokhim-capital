config.py
/workspace/app

 
import os
 
from dataclasses import dataclass

 
 

 
 

 
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
67
-
 
ai.py
/workspace/app

+
import json
2
+
from typing import Any
3
+
 
4
+
import aiohttp
5
+
 
6
+
 
7
+
class GeminiClient:
8
+
    def __init__(self, api_key: str, model: str) -> None:
9
+
        self._api_key = api_key
10
+
        self._model = model
11
+
 
12
+
    async def generate_text(self, prompt: str) -> str:
13
+
        url = (
14
+
            "https://generativelanguage.googleapis.com/v1beta/models/"
15
+
            f"{self._model}:generateContent?key={self._api_key}"
16
+
        )
17
+
        payload = {
18
+
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
19
+
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
20
+
        }
21
+
        timeout = aiohttp.ClientTimeout(total=60)
22
+
        async with aiohttp.ClientSession(timeout=timeout) as session:
23
+
            async with session.post(url, json=payload) as resp:
24
+
                data = await resp.json(content_type=None)
25
+
                if resp.status >= 400:
26
+
                    raise RuntimeError(f"Gemini error: {resp.status} {data}")
27
+
 
28
+
        candidates = data.get("candidates") or []
29
+
        if not candidates:
30
+
            return ""
31
+
        content = candidates[0].get("content") or {}
32
+
        parts = content.get("parts") or []
33
+
        texts = []
34
+
        for p in parts:
35
+
            t = p.get("text")
36
+
            if isinstance(t, str):
37
+
                texts.append(t)
38
+
        return "".join(texts).strip()
39
+
 
40
+
 
41
+
def _strip_code_fences(text: str) -> str:
42
+
    t = text.strip()
43
+
    if t.startswith("```"):
44
+
        lines = t.splitlines()
45
+
        if len(lines) >= 3 and lines[-1].strip() == "```":
46
+
            return "\n".join(lines[1:-1]).strip()
47
+
    return t
48
+
 
49
+
 
50
+
def parse_quiz_json(text: str) -> dict[str, Any]:
51
+
    cleaned = _strip_code_fences(text)
52
+
    return json.loads(cleaned)
53
+
 
storage.py
/workspace/app
+109
-0

 
import asyncio
2
+
import json
2 3
 
import sqlite3
3 4
 
from dataclasses import dataclass
4 5
 
 
5 6
 
 
6 7
 
@dataclass(frozen=True)
7 8
 
class ForwardConfig:
8 9
 
    source_chat_id: int | None
9 10
 
    target_chat_id: int | None
10 11
 
    keywords: list[str]
11 12
 
    mode: str
12 13
 
 
13 14
 
 
15
+
@dataclass(frozen=True)
16
+
class QuizRow:
17
+
    quiz_id: int
18
+
    title: str
19
+
 
20
+
 
21
+
@dataclass(frozen=True)
22
+
class QuizQuestionRow:
23
+
    idx: int
24
+
    question: str
25
+
    options: list[str]
26
+
    answer_index: int
27
+
 
28
+
 
14 29
 
class SettingsStore:
15 30
 
    def __init__(self, db_path: str) -> None:
16 31
 
        self._db_path = db_path
17 32
 
 
18 33
 
    def _connect(self) -> sqlite3.Connection:
19 34
 
        conn = sqlite3.connect(self._db_path)
20 35
 
        conn.execute(
21 36
 
            "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
22 37
 
        )
38
+
        conn.execute(
39
+
            "CREATE TABLE IF NOT EXISTS quizzes ("
40
+
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
41
+
            "title TEXT NOT NULL, "
42
+
            "created_by INTEGER, "
43
+
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP"
44
+
            ")"
45
+
        )
46
+
        conn.execute(
47
+
            "CREATE TABLE IF NOT EXISTS quiz_questions ("
48
+
            "quiz_id INTEGER NOT NULL, "
49
+
            "idx INTEGER NOT NULL, "
50
+
            "question TEXT NOT NULL, "
51
+
            "options_json TEXT NOT NULL, "
52
+
            "answer_index INTEGER NOT NULL, "
53
+
            "PRIMARY KEY (quiz_id, idx)"
54
+
            ")"
55
+
        )
23 56
 
        return conn
24 57
 
 
25 58
 
    def _get(self, key: str) -> str | None:
26 59
 
        conn = self._connect()
27 60
 
        try:
28 61
 
            row = conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
29 62
 
            return row[0] if row else None
30 63
 
        finally:
31 64
 
            conn.close()
32 65
 
 
33 66
 
    def _set(self, key: str, value: str) -> None:
34 67
 
        conn = self._connect()
35 68
 
        try:
36 69
 
            conn.execute(
37 70
 
                "INSERT INTO kv(key, value) VALUES(?, ?) "
38 71
 
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
39 72
 
                (key, value),
40 73
 
            )
41 74
 
            conn.commit()
42 75
 
        finally:
43 76
 
            conn.close()
44 77
 
 
45 78
 
    async def get(self, key: str) -> str | None:
46 79
 
        return await asyncio.to_thread(self._get, key)
47 80
 
 
48 81
 
    async def set(self, key: str, value: str) -> None:
49 82
 
        await asyncio.to_thread(self._set, key, value)
50 83
 
 
51 84
 
    async def get_forward_config(self) -> ForwardConfig:
52 85
 
        source = await self.get("source_chat_id")
53 86
 
        target = await self.get("target_chat_id")
54 87
 
        keywords = await self.get("filter_keywords")
55 88
 
        mode = (await self.get("filter_mode")) or "include"
56 89
 
 
57 90
 
        source_id = None
58 91
 
        target_id = None
59 92
 
        try:
60 93
 
            if source is not None:
61 94
 
                source_id = int(source)
62 95
 
        except ValueError:
63 96
 
            source_id = None
64 97
 
        try:
65 98
 
            if target is not None:
66 99
 
                target_id = int(target)
67 100
 
        except ValueError:
68 101
 
            target_id = None
69 102
 
 
70 103
 
        kw_list: list[str] = []
71 104
 
        if keywords:
72 105
 
            for k in keywords.split(","):
73 106
 
                k = k.strip()
74 107
 
                if k:
75 108
 
                    kw_list.append(k.lower())
76 109
 
 
77 110
 
        if mode not in {"include", "exclude"}:
78 111
 
            mode = "include"
79 112
 
 
80 113
 
        return ForwardConfig(
81 114
 
            source_chat_id=source_id,
82 115
 
            target_chat_id=target_id,
83 116
 
            keywords=kw_list,
84 117
 
            mode=mode,
85 118
 
        )
86 119
 
 
120
+
    def _create_quiz(self, title: str, created_by: int | None) -> int:
121
+
        conn = self._connect()
122
+
        try:
123
+
            cur = conn.execute(
124
+
                "INSERT INTO quizzes(title, created_by) VALUES(?, ?)",
125
+
                (title, created_by),
126
+
            )
127
+
            conn.commit()
128
+
            return int(cur.lastrowid)
129
+
        finally:
130
+
            conn.close()
131
+
 
132
+
    def _add_question(
133
+
        self, quiz_id: int, idx: int, question: str, options: list[str], answer_index: int
134
+
    ) -> None:
135
+
        conn = self._connect()
136
+
        try:
137
+
            conn.execute(
138
+
                "INSERT INTO quiz_questions(quiz_id, idx, question, options_json, answer_index) "
139
+
                "VALUES(?, ?, ?, ?, ?)",
140
+
                (quiz_id, idx, question, json.dumps(options), answer_index),
141
+
            )
142
+
            conn.commit()
143
+
        finally:
144
+
            conn.close()
145
+
 
146
+
    def _list_quizzes(self, limit: int) -> list[QuizRow]:
147
+
        conn = self._connect()
148
+
        try:
149
+
            rows = conn.execute(
150
+
                "SELECT id, title FROM quizzes ORDER BY id DESC LIMIT ?", (limit,)
151
+
            ).fetchall()
152
+
            return [QuizRow(quiz_id=int(r[0]), title=str(r[1])) for r in rows]
153
+
        finally:
154
+
            conn.close()
155
+
 
156
+
    def _get_questions(self, quiz_id: int) -> list[QuizQuestionRow]:
157
+
        conn = self._connect()
158
+
        try:
159
+
            rows = conn.execute(
160
+
                "SELECT idx, question, options_json, answer_index "
161
+
                "FROM quiz_questions WHERE quiz_id = ? ORDER BY idx ASC",
162
+
                (quiz_id,),
163
+
            ).fetchall()
164
+
            out: list[QuizQuestionRow] = []
165
+
            for r in rows:
166
+
                options = json.loads(r[2])
167
+
                if not isinstance(options, list):
168
+
                    options = []
169
+
                out.append(
170
+
                    QuizQuestionRow(
171
+
                        idx=int(r[0]),
172
+
                        question=str(r[1]),
173
+
                        options=[str(x) for x in options],
174
+
                        answer_index=int(r[3]),
175
+
                    )
176
+
                )
177
+
            return out
178
+
        finally:
179
+
            conn.close()
180
+
 
181
+
    async def create_quiz(self, title: str, created_by: int | None) -> int:
182
+
        return await asyncio.to_thread(self._create_quiz, title, created_by)
183
+
 
184
+
    async def add_question(
185
+
        self, quiz_id: int, idx: int, question: str, options: list[str], answer_index: int
186
+
    ) -> None:
187
+
        await asyncio.to_thread(
188
+
            self._add_question, quiz_id, idx, question, options, answer_index
189
+
        )
190
+
 
191
+
    async def list_quizzes(self, limit: int = 20) -> list[QuizRow]:
192
+
        return await asyncio.to_thread(self._list_quizzes, limit)
193
+
 
194
+
    async def get_quiz_questions(self, quiz_id: int) -> list[QuizQuestionRow]:
195
+
        return await asyncio.to_thread(self._get_questions, quiz_id)
main.py
/workspace/app
+7

 
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
handlers.py
/workspace/app
+291
-4

 
import asyncio
2
+
import tempfile
2 3
 
import time
3 4
 
 
4
-
from telegram import Update
5
-
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
5
+
from pypdf import PdfReader
6
+
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
7
+
from telegram.ext import (
8
+
    Application,
9
+
    CallbackQueryHandler,
10
+
    CommandHandler,
11
+
    ContextTypes,
12
+
    MessageHandler,
13
+
    filters,
14
+
)
6 15
 
 
7
-
from .storage import ForwardConfig, SettingsStore
16
+
from .ai import GeminiClient, parse_quiz_json
17
+
from .storage import ForwardConfig, QuizQuestionRow, QuizRow, SettingsStore
8 18
 
 
9 19
 
 
10
-
def setup_application(app: Application, admins: set[int], store: SettingsStore) -> None:
20
+
def setup_application(
21
+
    app: Application,
22
+
    admins: set[int],
23
+
    store: SettingsStore,
24
+
    gemini: GeminiClient | None,
25
+
    quiz_max_questions: int,
26
+
) -> None:
11 27
 
    config_lock = asyncio.Lock()
12 28
 
    cached_config: ForwardConfig | None = None
13 29
 
    cached_at = 0.0
14 30
 
 
15 31
 
    async def get_config() -> ForwardConfig:
16 32
 
        nonlocal cached_config, cached_at
17 33
 
        now = time.time()
18 34
 
        if cached_config is not None and (now - cached_at) < 5:
19 35
 
            return cached_config
20 36
 
        async with config_lock:
21 37
 
            now = time.time()
22 38
 
            if cached_config is not None and (now - cached_at) < 5:
23 39
 
                return cached_config
24 40
 
            cached_config = await store.get_forward_config()
25 41
 
            cached_at = now
26 42
 
            return cached_config
27 43
 
 
28 44
 
    def is_admin(update: Update) -> bool:
29 45
 
        user = update.effective_user
30 46
 
        if not user:
31 47
 
            return False
32 48
 
        return user.id in admins
33 49
 
 
34 50
 
    def render_config(cfg: ForwardConfig) -> str:
35 51
 
        return (
36 52
 
            "Forward sozlamalari:\n"
37 53
 
            f"- source_chat_id: {cfg.source_chat_id}\n"
38 54
 
            f"- target_chat_id: {cfg.target_chat_id}\n"
39 55
 
            f"- mode: {cfg.mode}\n"
40 56
 
            f"- keywords: {', '.join(cfg.keywords) if cfg.keywords else '(bo‘sh)'}"
41 57
 
        )
42 58
 
 
43 59
 
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
44 60
 
        if not update.effective_message:
45 61
 
            return
46 62
 
        await update.effective_message.reply_text(
47 63
 
            "Salom. /help ni yuboring.\n"
48 64
 
            "Adminlar uchun: /admin\n"
49 65
 
            "Forward sozlamalari: /status"
50 66
 
        )
51 67
 
 
52 68
 
    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
53 69
 
        if not update.effective_message:
54 70
 
            return
55 71
 
        await update.effective_message.reply_text(
56 72
 
            "Buyruqlar:\n"
57 73
 
            "/start\n"
58 74
 
            "/help\n"
59 75
 
            "/id\n"
60 76
 
            "/status\n"
77
+
            "/quiznew\n"
78
+
            "/quizzes\n"
79
+
            "/quizstart <id>\n"
61 80
 
            "\n"
62 81
 
            "Admin buyruqlari:\n"
63 82
 
            "/admin\n"
64 83
 
            "/setsource <chat_id>\n"
65 84
 
            "/settarget <chat_id>\n"
66 85
 
            "/setkeywords <k1,k2,...>\n"
67 86
 
            "/mode <include|exclude>"
68 87
 
        )
69 88
 
 
70 89
 
    async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
71 90
 
        msg = update.effective_message
72 91
 
        chat = update.effective_chat
73 92
 
        user = update.effective_user
74 93
 
        if not msg or not chat:
75 94
 
            return
76 95
 
        lines = [f"chat_id: {chat.id}"]
77 96
 
        if user:
78 97
 
            lines.append(f"user_id: {user.id}")
79 98
 
        await msg.reply_text("\n".join(lines))
80 99
 
 
100
+
    async def quiznew(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
101
+
        msg = update.effective_message
102
+
        if not msg:
103
+
            return
104
+
        if gemini is None:
105
+
            await msg.reply_text("AI yoqilmagan. GEMINI_API_KEY kerak.")
106
+
            return
107
+
        context.user_data["awaiting_quiz_pdf"] = True
108
+
        await msg.reply_text("PDF fayl yuboring. Men savol-javoblarni quizga aylantiraman.")
109
+
 
110
+
    async def quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
111
+
        msg = update.effective_message
112
+
        if not msg:
113
+
            return
114
+
        rows: list[QuizRow] = await store.list_quizzes(limit=10)
115
+
        if not rows:
116
+
            await msg.reply_text("Hali quiz yo‘q. /quiznew qiling.")
117
+
            return
118
+
        text = "Quizlar:\n" + "\n".join([f"- {r.quiz_id}: {r.title}" for r in rows])
119
+
        await msg.reply_text(text)
120
+
 
121
+
    async def quizstart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
122
+
        msg = update.effective_message
123
+
        if not msg:
124
+
            return
125
+
        if not context.args:
126
+
            await msg.reply_text("Misol: /quizstart 1")
127
+
            return
128
+
        try:
129
+
            quiz_id = int(context.args[0])
130
+
        except ValueError:
131
+
            await msg.reply_text("id son bo‘lishi kerak.")
132
+
            return
133
+
        await start_quiz_session(update, context, quiz_id)
134
+
 
135
+
    async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
136
+
        msg = update.effective_message
137
+
        doc = update.effective_document
138
+
        if not msg or not doc:
139
+
            return
140
+
        if not context.user_data.get("awaiting_quiz_pdf"):
141
+
            return
142
+
        context.user_data["awaiting_quiz_pdf"] = False
143
+
        if gemini is None:
144
+
            await msg.reply_text("AI yoqilmagan. GEMINI_API_KEY kerak.")
145
+
            return
146
+
        if doc.mime_type != "application/pdf":
147
+
            await msg.reply_text("Faqat PDF kerak.")
148
+
            return
149
+
        await msg.reply_text("PDF o‘qilyapti...")
150
+
        file = await context.bot.get_file(doc.file_id)
151
+
        with tempfile.TemporaryDirectory() as td:
152
+
            path = f"{td}/quiz.pdf"
153
+
            await file.download_to_drive(custom_path=path)
154
+
            reader = PdfReader(path)
155
+
            pages = []
156
+
            for p in reader.pages[:30]:
157
+
                t = p.extract_text() or ""
158
+
                t = t.strip()
159
+
                if t:
160
+
                    pages.append(t)
161
+
            full_text = "\n\n".join(pages)
162
+
        if not full_text:
163
+
            await msg.reply_text("PDF dan matn olinmadi. PDF skan bo‘lsa OCR kerak bo‘ladi.")
164
+
            return
165
+
 
166
+
        title = doc.file_name or "Quiz"
167
+
        prompt = (
168
+
            "Quyidagi matndan test-quiz tayyorla.\n"
169
+
            f"Talablar:\n"
170
+
            f"- Maksimum {quiz_max_questions} ta savol\n"
171
+
            "- Har savolda 4 ta variant bo‘lsin\n"
172
+
            "- answer_index 0..3 oralig‘ida bo‘lsin\n"
173
+
            "- Faqat JSON qaytar, hech qanday izohsiz\n"
174
+
            'Format: {"title":"...","questions":[{"question":"...","options":["A","B","C","D"],"answer_index":0}]}\n'
175
+
            "\n"
176
+
            "Matn:\n"
177
+
            + full_text[:20000]
178
+
        )
179
+
        try:
180
+
            raw = await gemini.generate_text(prompt)
181
+
            quiz_obj = parse_quiz_json(raw)
182
+
        except Exception:
183
+
            await msg.reply_text("AI quiz yaratishda xatolik berdi. PDF formatini soddaroq qilib ko‘ring.")
184
+
            return
185
+
 
186
+
        q_title = str(quiz_obj.get("title") or title)
187
+
        questions = quiz_obj.get("questions") or []
188
+
        if not isinstance(questions, list) or not questions:
189
+
            await msg.reply_text("Quiz topilmadi. PDF ichida savollar aniq bo‘lsin.")
190
+
            return
191
+
 
192
+
        created_by = update.effective_user.id if update.effective_user else None
193
+
        quiz_id = await store.create_quiz(q_title, created_by)
194
+
        saved = 0
195
+
        for idx, q in enumerate(questions[:quiz_max_questions]):
196
+
            if not isinstance(q, dict):
197
+
                continue
198
+
            question = q.get("question")
199
+
            options = q.get("options")
200
+
            answer_index = q.get("answer_index")
201
+
            if not isinstance(question, str) or not question.strip():
202
+
                continue
203
+
            if not isinstance(options, list) or len(options) != 4:
204
+
                continue
205
+
            if not isinstance(answer_index, int) or not (0 <= answer_index <= 3):
206
+
                continue
207
+
            await store.add_question(
208
+
                quiz_id,
209
+
                idx,
210
+
                question.strip(),
211
+
                [str(x) for x in options],
212
+
                answer_index,
213
+
            )
214
+
            saved += 1
215
+
 
216
+
        if saved == 0:
217
+
            await msg.reply_text("Savollar saqlanmadi. PDF formati mos kelmadi.")
218
+
            return
219
+
 
220
+
        kb = InlineKeyboardMarkup(
221
+
            [[InlineKeyboardButton("Quizni boshlash", callback_data=f"quiz:start:{quiz_id}")]]
222
+
        )
223
+
        await msg.reply_text(f"Tayyor: quiz_id={quiz_id}, savollar={saved}", reply_markup=kb)
224
+
 
225
+
    async def start_quiz_session(
226
+
        update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_id: int
227
+
    ) -> None:
228
+
        msg = update.effective_message
229
+
        if not msg:
230
+
            return
231
+
        questions: list[QuizQuestionRow] = await store.get_quiz_questions(quiz_id)
232
+
        if not questions:
233
+
            await msg.reply_text("Bu quiz topilmadi.")
234
+
            return
235
+
        context.user_data["quiz_id"] = quiz_id
236
+
        context.user_data["quiz_idx"] = 0
237
+
        context.user_data["quiz_score"] = 0
238
+
        await send_quiz_question(update, context, questions[0], len(questions))
239
+
 
240
+
    async def send_quiz_question(
241
+
        update: Update,
242
+
        context: ContextTypes.DEFAULT_TYPE,
243
+
        q: QuizQuestionRow,
244
+
        total: int,
245
+
    ) -> None:
246
+
        msg = update.effective_message
247
+
        if not msg:
248
+
            return
249
+
        quiz_id = int(context.user_data.get("quiz_id"))
250
+
        buttons = [
251
+
            [
252
+
                InlineKeyboardButton(
253
+
                    q.options[0], callback_data=f"quiz:ans:{quiz_id}:{q.idx}:0"
254
+
                )
255
+
            ],
256
+
            [
257
+
                InlineKeyboardButton(
258
+
                    q.options[1], callback_data=f"quiz:ans:{quiz_id}:{q.idx}:1"
259
+
                )
260
+
            ],
261
+
            [
262
+
                InlineKeyboardButton(
263
+
                    q.options[2], callback_data=f"quiz:ans:{quiz_id}:{q.idx}:2"
264
+
                )
265
+
            ],
266
+
            [
267
+
                InlineKeyboardButton(
268
+
                    q.options[3], callback_data=f"quiz:ans:{quiz_id}:{q.idx}:3"
269
+
                )
270
+
            ],
271
+
        ]
272
+
        text = f"{q.idx + 1}/{total}\n\n{q.question}"
273
+
        await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
274
+
 
275
+
    async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
276
+
        q = update.callback_query
277
+
        if not q:
278
+
            return
279
+
        data = q.data or ""
280
+
        if data.startswith("quiz:start:"):
281
+
            await q.answer()
282
+
            try:
283
+
                quiz_id = int(data.split(":")[2])
284
+
            except Exception:
285
+
                return
286
+
            fake_update = Update(update.update_id, message=q.message)
287
+
            await start_quiz_session(fake_update, context, quiz_id)
288
+
            return
289
+
 
290
+
        if not data.startswith("quiz:ans:"):
291
+
            return
292
+
        await q.answer()
293
+
        parts = data.split(":")
294
+
        if len(parts) != 5:
295
+
            return
296
+
        try:
297
+
            quiz_id = int(parts[2])
298
+
            idx = int(parts[3])
299
+
            choice = int(parts[4])
300
+
        except ValueError:
301
+
            return
302
+
 
303
+
        current_quiz = context.user_data.get("quiz_id")
304
+
        current_idx = context.user_data.get("quiz_idx")
305
+
        if current_quiz != quiz_id or current_idx != idx:
306
+
            return
307
+
 
308
+
        questions: list[QuizQuestionRow] = await store.get_quiz_questions(quiz_id)
309
+
        if idx < 0 or idx >= len(questions):
310
+
            return
311
+
        correct = questions[idx].answer_index == choice
312
+
        if correct:
313
+
            context.user_data["quiz_score"] = int(context.user_data.get("quiz_score", 0)) + 1
314
+
        next_idx = idx + 1
315
+
        context.user_data["quiz_idx"] = next_idx
316
+
 
317
+
        if not q.message:
318
+
            return
319
+
        if next_idx >= len(questions):
320
+
            score = int(context.user_data.get("quiz_score", 0))
321
+
            total = len(questions)
322
+
            context.user_data.pop("quiz_id", None)
323
+
            context.user_data.pop("quiz_idx", None)
324
+
            context.user_data.pop("quiz_score", None)
325
+
            await q.message.reply_text(f"Natija: {score}/{total}")
326
+
            return
327
+
        next_q = questions[next_idx]
328
+
        fake_update = Update(update.update_id, message=q.message)
329
+
        await send_quiz_question(fake_update, context, next_q, len(questions))
330
+
 
331
+
    async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
332
+
        msg = update.effective_message
333
+
        chat = update.effective_chat
334
+
        if not msg or not chat:
335
+
            return
336
+
        if chat.type != "private":
337
+
            return
338
+
        if gemini is None:
339
+
            return
340
+
        if not msg.text:
341
+
            return
342
+
        if context.user_data.get("awaiting_quiz_pdf"):
343
+
            return
344
+
        text = msg.text.strip()
345
+
        if not text:
346
+
            return
347
+
        prompt = (
348
+
            "Sen Telegram botdagi sun'iy intellekt yordamchisisan. "
349
+
            "Foydalanuvchi savoliga qisqa va aniq javob ber.\n\n"
350
+
            f"Savol: {text}"
351
+
        )
352
+
        try:
353
+
            out = await gemini.generate_text(prompt)
354
+
        except Exception:
355
+
            await msg.reply_text("AI vaqtincha ishlamayapti.")
356
+
            return
357
+
        if not out:
358
+
            await msg.reply_text("Javob topilmadi.")
359
+
            return
360
+
        await msg.reply_text(out[:3500])
361
+
 
81 362
 
    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
82 363
 
        if not update.effective_message:
83 364
 
            return
84 365
 
        cfg = await get_config()
85 366
 
        await update.effective_message.reply_text(render_config(cfg))
86 367
 
 
87 368
 
    async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
88 369
 
        if not update.effective_message:
89 370
 
            return
90 371
 
        if not is_admin(update):
91 372
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
92 373
 
            return
93 374
 
        cfg = await get_config()
94 375
 
        await update.effective_message.reply_text(
95 376
 
            "Admin panel.\n\n"
96 377
 
            + render_config(cfg)
97 378
 
            + "\n\n"
98 379
 
            "O‘zgartirish:\n"
99 380
 
            "/setsource <chat_id>\n"
100 381
 
            "/settarget <chat_id>\n"
101 382
 
            "/setkeywords <k1,k2,...>\n"
102 383
 
            "/mode <include|exclude>"
103 384
 
        )
104 385
 
 
105 386
 
    async def set_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
106 387
 
        if not update.effective_message:
107 388
 
            return
108 389
 
        if not is_admin(update):
109 390
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
110 391
 
            return
111 392
 
        if not context.args:
112 393
 
            await update.effective_message.reply_text("Misol: /setsource -1001234567890")
113 394
 
            return
114 395
 
        try:
115 396
 
            chat_id = int(context.args[0])
116 397
 
        except ValueError:
117 398
 
            await update.effective_message.reply_text("chat_id son bo‘lishi kerak.")
118 399
 
            return
119 400
 
        await store.set("source_chat_id", str(chat_id))
120 401
 
        await update.effective_message.reply_text("OK.")
121 402
 
 
122 403
 
    async def set_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
123 404
 
        if not update.effective_message:
124 405
 
            return
125 406
 
        if not is_admin(update):
126 407
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
127 408
 
            return
128 409
 
        if not context.args:
129 410
 
            await update.effective_message.reply_text("Misol: /settarget -1001234567890")
130 411
 
            return
131 412
 
        try:
132 413
 
            chat_id = int(context.args[0])
133 414
 
        except ValueError:
134 415
 
            await update.effective_message.reply_text("chat_id son bo‘lishi kerak.")
135 416
 
            return
136 417
 
        await store.set("target_chat_id", str(chat_id))
137 418
 
        await update.effective_message.reply_text("OK.")
138 419
 
 
139 420
 
    async def set_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
140 421
 
        if not update.effective_message:
141 422
 
            return
142 423
 
        if not is_admin(update):
143 424
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
144 425
 
            return
145 426
 
        raw = " ".join(context.args) if context.args else ""
146 427
 
        await store.set("filter_keywords", raw.strip())
147 428
 
        await update.effective_message.reply_text("OK.")
148 429
 
 
149 430
 
    async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
150 431
 
        if not update.effective_message:
151 432
 
            return
152 433
 
        if not is_admin(update):
153 434
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
154 435
 
            return
155 436
 
        if not context.args:
156 437
 
            await update.effective_message.reply_text("Misol: /mode include")
157 438
 
            return
158 439
 
        mode = context.args[0].strip().lower()
159 440
 
        if mode not in {"include", "exclude"}:
160 441
 
            await update.effective_message.reply_text("Faqat include yoki exclude.")
161 442
 
            return
162 443
 
        await store.set("filter_mode", mode)
163 444
 
        await update.effective_message.reply_text("OK.")
164 445
 
 
165 446
 
    def extract_text(update: Update) -> str:
166 447
 
        msg = update.effective_message
167 448
 
        if not msg:
168 449
 
            return ""
169 450
 
        if msg.text:
170 451
 
            return msg.text
171 452
 
        if msg.caption:
172 453
 
            return msg.caption
173 454
 
        return ""
174 455
 
 
175 456
 
    def match(text: str, cfg: ForwardConfig) -> bool:
176 457
 
        if not cfg.keywords:
177 458
 
            return True
178 459
 
        text_l = text.lower()
179 460
 
        hit = any(k in text_l for k in cfg.keywords)
180 461
 
        if cfg.mode == "include":
181 462
 
            return hit
182 463
 
        return not hit
183 464
 
 
184 465
 
    async def forward_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
185 466
 
        chat = update.effective_chat
186 467
 
        msg = update.effective_message
187 468
 
        if not chat or not msg:
188 469
 
            return
189 470
 
        if chat.type == "private":
190 471
 
            return
191 472
 
 
192 473
 
        cfg = await get_config()
193 474
 
        if cfg.target_chat_id is None:
194 475
 
            return
195 476
 
        if cfg.source_chat_id is not None and chat.id != cfg.source_chat_id:
196 477
 
            return
197 478
 
 
198 479
 
        text = extract_text(update)
199 480
 
        if not match(text, cfg):
200 481
 
            return
201 482
 
 
202 483
 
        await context.bot.forward_message(
203 484
 
            chat_id=cfg.target_chat_id,
204 485
 
            from_chat_id=chat.id,
205 486
 
            message_id=msg.message_id,
206 487
 
        )
207 488
 
 
208 489
 
    app.add_handler(CommandHandler("start", start))
209 490
 
    app.add_handler(CommandHandler("help", help_cmd))
210 491
 
    app.add_handler(CommandHandler("id", id_cmd))
211 492
 
    app.add_handler(CommandHandler("status", status))
493
+
    app.add_handler(CommandHandler("quiznew", quiznew))
494
+
    app.add_handler(CommandHandler("quizzes", quizzes))
495
+
    app.add_handler(CommandHandler("quizstart", quizstart))
212 496
 
    app.add_handler(CommandHandler("admin", admin))
213 497
 
    app.add_handler(CommandHandler("setsource", set_source))
214 498
 
    app.add_handler(CommandHandler("settarget", set_target))
215 499
 
    app.add_handler(CommandHandler("setkeywords", set_keywords))
216 500
 
    app.add_handler(CommandHandler("mode", set_mode))
501
+
    app.add_handler(CallbackQueryHandler(quiz_callback))
502
+
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, handle_pdf))
503
+
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))
217 504
 
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_filter))
.env.example
/workspace
+3
-0

 
TELEGRAM_BOT_TOKEN=123456:ABCDEF
2 2
 
WEBHOOK_BASE_URL=https://your-domain.example
3 3
 
WEBHOOK_PATH=/webhook
4 4
 
TELEGRAM_WEBHOOK_SECRET=change-me
5 5
 
ADMIN_IDS=123456789
6 6
 
DATABASE_PATH=bot.db
7
+
GEMINI_API_KEY=
8
+
GEMINI_MODEL=gemini-1.5-flash
9
+
QUIZ_MAX_QUESTIONS=10
requirements.txt
/workspace
+1
-0
1 1
 
aiohttp==3.9.5
2
+
pypdf==5.5.0
2 3
 
python-telegram-bot==21.6
README.md
/workspace
+11
-0
1 1
 
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
 
- `WEBHOOK_BASE_URL` (HTTPS domeningiz)
22 22
 
- `TELEGRAM_WEBHOOK_SECRET` (ixtiyoriy, tavsiya qilinadi)
23 23
 
- `ADMIN_IDS` (vergul bilan)
24
+
- `GEMINI_API_KEY` (AI uchun)
24 25
 
 
25 26
 
3) Server:
26 27
 
 
27 28
 
```bash
28 29
 
python -m app.main
29 30
 
```
30 31
 
 
31 32
 
## Telegram tomoni
32 33
 
 
33 34
 
- Webhook URL: `{WEBHOOK_BASE_URL}{WEBHOOK_PATH}` (default: `/webhook`)
34 35
 
- Agar `TELEGRAM_WEBHOOK_SECRET` qo‘ysangiz, so‘rovlar `X-Telegram-Bot-Api-Secret-Token` header orqali tekshiriladi
35 36
 
 
36 37
 
## Admin buyruqlari
37 38
 
 
38 39
 
- `/id`: chat_id/user_id ko‘rsatadi
39 40
 
- `/admin`
40 41
 
- `/status`
41 42
 
- `/setsource <chat_id>`: kuzatiladigan chat (kanal/guruh) id
42 43
 
- `/settarget <chat_id>`: forward qilinadigan chat id
43 44
 
- `/setkeywords <k1,k2,...>`: kalit so‘zlar
44 45
 
- `/mode <include|exclude>`
45 46
 
 
46 47
 
`include` bo‘lsa faqat kalit so‘z topilganda forward qiladi, `exclude` bo‘lsa kalit so‘z bor bo‘lsa forward qilmaydi.
47 48
 
 
49
+
## AI
50
+
 
51
+
- Private chatda oddiy matn yuborsangiz, bot Gemini orqali javob beradi (GEMINI_API_KEY bo‘lsa)
52
+
 
53
+
## Quiz
54
+
 
55
+
- `/quiznew` → keyin PDF yuboring (bot AI bilan savollarga ajratadi)
56
+
- `/quizzes` → mavjud quizlar ro‘yxati
57
+
- `/quizstart <id>` → quizni boshlash (inline tugmalar bilan)
58
+
 
48 59
 
## Docker
49 60
 
 
50 61
 
```bash
51 62
 
docker build -t tg-bot .
52 63
 
docker run --rm -p 8000:8000 --env-file .env tg-bot
53 64
 
```
config.py
/workspace/app
+4
-0

 
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
market_data.py
/workspace/app
+78
-0

+
import json
2
+
from dataclasses import dataclass
3
+
from typing import Any
4
+
 
5
+
import aiohttp
6
+
 
7
+
 
8
+
@dataclass(frozen=True)
9
+
class FinnhubSymbol:
10
+
    symbol: str
11
+
    kind: str
12
+
 
13
+
 
14
+
@dataclass(frozen=True)
15
+
class CandleSeries:
16
+
    o: list[float]
17
+
    h: list[float]
18
+
    l: list[float]
19
+
    c: list[float]
20
+
    t: list[int]
21
+
 
22
+
 
23
+
def parse_symbol_map(raw_json: str | None) -> dict[str, FinnhubSymbol]:
24
+
    if not raw_json:
25
+
        return {}
26
+
    obj = json.loads(raw_json)
27
+
    out: dict[str, FinnhubSymbol] = {}
28
+
    if isinstance(obj, dict):
29
+
        for k, v in obj.items():
30
+
            if isinstance(v, str):
31
+
                out[str(k).upper()] = FinnhubSymbol(symbol=v, kind="forex")
32
+
            elif isinstance(v, dict):
33
+
                sym = v.get("symbol")
34
+
                kind = v.get("kind") or v.get("type") or "forex"
35
+
                if isinstance(sym, str):
36
+
                    out[str(k).upper()] = FinnhubSymbol(symbol=sym, kind=str(kind))
37
+
    return out
38
+
 
39
+
 
40
+
class FinnhubClient:
41
+
    def __init__(self, api_key: str) -> None:
42
+
        self._api_key = api_key
43
+
 
44
+
    def _endpoint(self, kind: str) -> str:
45
+
        k = kind.lower()
46
+
        if k in {"forex", "fx"}:
47
+
            return "https://finnhub.io/api/v1/forex/candle"
48
+
        if k in {"crypto"}:
49
+
            return "https://finnhub.io/api/v1/crypto/candle"
50
+
        return "https://finnhub.io/api/v1/stock/candle"
51
+
 
52
+
    async def candles(
53
+
        self, *, kind: str, symbol: str, resolution: str, frm: int, to: int
54
+
    ) -> CandleSeries:
55
+
        url = self._endpoint(kind)
56
+
        params = {
57
+
            "symbol": symbol,
58
+
            "resolution": resolution,
59
+
            "from": str(frm),
60
+
            "to": str(to),
61
+
            "token": self._api_key,
62
+
        }
63
+
        timeout = aiohttp.ClientTimeout(total=30)
64
+
        async with aiohttp.ClientSession(timeout=timeout) as session:
65
+
            async with session.get(url, params=params) as resp:
66
+
                data: Any = await resp.json(content_type=None)
67
+
                if resp.status >= 400:
68
+
                    raise RuntimeError(f"Finnhub error: {resp.status} {data}")
69
+
        if not isinstance(data, dict) or data.get("s") != "ok":
70
+
            raise RuntimeError(f"Finnhub candles not ok: {data}")
71
+
        return CandleSeries(
72
+
            o=[float(x) for x in (data.get("o") or [])],
73
+
            h=[float(x) for x in (data.get("h") or [])],
74
+
            l=[float(x) for x in (data.get("l") or [])],
75
+
            c=[float(x) for x in (data.get("c") or [])],
76
+
            t=[int(x) for x in (data.get("t") or [])],
77
+
        )
78
+
 
ict.py
/workspace/app
+64
-0

+
from dataclasses import dataclass
2
+
 
3
+
from .market_data import CandleSeries
4
+
 
5
+
 
6
+
@dataclass(frozen=True)
7
+
class KeyLevels:
8
+
    pdh: float | None
9
+
    pdl: float | None
10
+
    daily_mid: float | None
11
+
    h4_swing_high: float | None
12
+
    h4_swing_low: float | None
13
+
    h1_swing_high: float | None
14
+
    h1_swing_low: float | None
15
+
    current: float | None
16
+
 
17
+
 
18
+
def _swing_high(series: CandleSeries, lookback: int) -> float | None:
19
+
    if not series.h:
20
+
        return None
21
+
    vals = series.h[-lookback:] if len(series.h) >= lookback else series.h
22
+
    return max(vals) if vals else None
23
+
 
24
+
 
25
+
def _swing_low(series: CandleSeries, lookback: int) -> float | None:
26
+
    if not series.l:
27
+
        return None
28
+
    vals = series.l[-lookback:] if len(series.l) >= lookback else series.l
29
+
    return min(vals) if vals else None
30
+
 
31
+
 
32
+
def _prev_day_levels(d1: CandleSeries) -> tuple[float | None, float | None, float | None]:
33
+
    if len(d1.h) < 2 or len(d1.l) < 2:
34
+
        return None, None, None
35
+
    pdh = d1.h[-2]
36
+
    pdl = d1.l[-2]
37
+
    mid = (pdh + pdl) / 2
38
+
    return pdh, pdl, mid
39
+
 
40
+
 
41
+
def compute_key_levels(d1: CandleSeries, h4: CandleSeries, h1: CandleSeries) -> KeyLevels:
42
+
    pdh, pdl, mid = _prev_day_levels(d1)
43
+
    current = h1.c[-1] if h1.c else (h4.c[-1] if h4.c else (d1.c[-1] if d1.c else None))
44
+
    return KeyLevels(
45
+
        pdh=pdh,
46
+
        pdl=pdl,
47
+
        daily_mid=mid,
48
+
        h4_swing_high=_swing_high(h4, 20),
49
+
        h4_swing_low=_swing_low(h4, 20),
50
+
        h1_swing_high=_swing_high(h1, 24),
51
+
        h1_swing_low=_swing_low(h1, 24),
52
+
        current=current,
53
+
    )
54
+
 
55
+
 
56
+
def compute_bias(levels: KeyLevels) -> str:
57
+
    if levels.current is None or levels.daily_mid is None:
58
+
        return "Neutral"
59
+
    if levels.current > levels.daily_mid:
60
+
        return "Bullish"
61
+
    if levels.current < levels.daily_mid:
62
+
        return "Bearish"
63
+
    return "Neutral"
64
+
 
handlers.py
/workspace/app
+69
-0

 
import asyncio
2 2
 
import tempfile
3 3
 
import time
4 4
 
 
5 5
 
from pypdf import PdfReader
6 6
 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
7 7
 
from telegram.ext import (
8 8
 
    Application,
9 9
 
    CallbackQueryHandler,
10 10
 
    CommandHandler,
11 11
 
    ContextTypes,
12 12
 
    MessageHandler,
13 13
 
    filters,
14 14
 
)
15 15
 
 
16 16
 
from .ai import GeminiClient, parse_quiz_json
17
+
from .ict import compute_bias, compute_key_levels
18
+
from .market_data import FinnhubClient, FinnhubSymbol
17 19
 
from .storage import ForwardConfig, QuizQuestionRow, QuizRow, SettingsStore
18 20
 
 
19 21
 
 
20 22
 
def setup_application(
21 23
 
    app: Application,
22 24
 
    admins: set[int],
23 25
 
    store: SettingsStore,
24 26
 
    gemini: GeminiClient | None,
25 27
 
    quiz_max_questions: int,
28
+
    finnhub: FinnhubClient | None,
29
+
    ict_symbols: dict[str, FinnhubSymbol],
26 30
 
) -> None:
27 31
 
    config_lock = asyncio.Lock()
28 32
 
    cached_config: ForwardConfig | None = None
29 33
 
    cached_at = 0.0
30 34
 
 
31 35
 
    async def get_config() -> ForwardConfig:
32 36
 
        nonlocal cached_config, cached_at
33 37
 
        now = time.time()
34 38
 
        if cached_config is not None and (now - cached_at) < 5:
35 39
 
            return cached_config
36 40
 
        async with config_lock:
37 41
 
            now = time.time()
38 42
 
            if cached_config is not None and (now - cached_at) < 5:
39 43
 
                return cached_config
40 44
 
            cached_config = await store.get_forward_config()
41 45
 
            cached_at = now
42 46
 
            return cached_config
43 47
 
 
44 48
 
    def is_admin(update: Update) -> bool:
45 49
 
        user = update.effective_user
46 50
 
        if not user:
47 51
 
            return False
48 52
 
        return user.id in admins
49 53
 
 
50 54
 
    def render_config(cfg: ForwardConfig) -> str:
51 55
 
        return (
52 56
 
            "Forward sozlamalari:\n"
53 57
 
            f"- source_chat_id: {cfg.source_chat_id}\n"
54 58
 
            f"- target_chat_id: {cfg.target_chat_id}\n"
55 59
 
            f"- mode: {cfg.mode}\n"
56 60
 
            f"- keywords: {', '.join(cfg.keywords) if cfg.keywords else '(bo‘sh)'}"
57 61
 
        )
58 62
 
 
59 63
 
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
60 64
 
        if not update.effective_message:
61 65
 
            return
62 66
 
        await update.effective_message.reply_text(
63 67
 
            "Salom. /help ni yuboring.\n"
64 68
 
            "Adminlar uchun: /admin\n"
65 69
 
            "Forward sozlamalari: /status"
66 70
 
        )
67 71
 
 
68 72
 
    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
69 73
 
        if not update.effective_message:
70 74
 
            return
71 75
 
        await update.effective_message.reply_text(
72 76
 
            "Buyruqlar:\n"
73 77
 
            "/start\n"
74 78
 
            "/help\n"
75 79
 
            "/chat\n"
76 80
 
            "/id\n"
77 81
 
            "/status\n"
78 82
 
            "/quiznew\n"
79 83
 
            "/quizzes\n"
80 84
 
            "/quizstart <id>\n"
81 85
 
            "\n"
82 86
 
            "Admin buyruqlari:\n"
87
+
            "/ict <symbol>\n"
83 88
 
            "/admin\n"
84 89
 
            "/setsource <chat_id>\n"
85 90
 
            "/settarget <chat_id>\n"
86 91
 
            "/setkeywords <k1,k2,...>\n"
87 92
 
            "/mode <include|exclude>"
88 93
 
        )
89 94
 
 
90 95
 
    async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
91 96
 
        msg = update.effective_message
92 97
 
        chat = update.effective_chat
93 98
 
        user = update.effective_user
94 99
 
        if not msg or not chat:
95 100
 
            return
96 101
 
        lines = [f"chat_id: {chat.id}"]
97 102
 
        if user:
98 103
 
            lines.append(f"user_id: {user.id}")
99 104
 
        await msg.reply_text("\n".join(lines))
100 105
 
 
101 106
 
    async def chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
102 107
 
        msg = update.effective_message
103 108
 
        chat = update.effective_chat
104 109
 
        if not msg or not chat:
105 110
 
            return
106 111
 
        if chat.type != "private":
107 112
 
            await msg.reply_text("Chat rejimi faqat private chatda.")
108 113
 
            return
109 114
 
        context.user_data["chat_mode"] = True
110 115
 
        await msg.reply_text("Chat rejimi. Savolingizni yozing:")
111 116
 
 
112 117
 
    async def quiznew(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
113 118
 
        msg = update.effective_message
114 119
 
        if not msg:
115 120
 
            return
116 121
 
        if gemini is None:
117 122
 
            await msg.reply_text("AI yoqilmagan. GEMINI_API_KEY kerak.")
118 123
 
            return
119 124
 
        context.user_data["awaiting_quiz_pdf"] = True
120 125
 
        await msg.reply_text("PDF fayl yuboring. Men savol-javoblarni quizga aylantiraman.")
121 126
 
 
122 127
 
    async def quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
123 128
 
        msg = update.effective_message
124 129
 
        if not msg:
125 130
 
            return
126 131
 
        rows: list[QuizRow] = await store.list_quizzes(limit=10)
127 132
 
        if not rows:
128 133
 
            await msg.reply_text("Hali quiz yo‘q. /quiznew qiling.")
129 134
 
            return
130 135
 
        text = "Quizlar:\n" + "\n".join([f"- {r.quiz_id}: {r.title}" for r in rows])
131 136
 
        await msg.reply_text(text)
132 137
 
 
133 138
 
    async def quizstart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
134 139
 
        msg = update.effective_message
135 140
 
        if not msg:
136 141
 
            return
137 142
 
        if not context.args:
138 143
 
            await msg.reply_text("Misol: /quizstart 1")
139 144
 
            return
140 145
 
        try:
141 146
 
            quiz_id = int(context.args[0])
142 147
 
        except ValueError:
143 148
 
            await msg.reply_text("id son bo‘lishi kerak.")
144 149
 
            return
145 150
 
        await start_quiz_session(update, context, quiz_id)
146 151
 
 
152
+
    async def ict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
153
+
        msg = update.effective_message
154
+
        if not msg:
155
+
            return
156
+
        if not is_admin(update):
157
+
            await msg.reply_text("Ruxsat yo‘q.")
158
+
            return
159
+
        if finnhub is None or not ict_symbols:
160
+
            await msg.reply_text("ICT yoqilmagan. FINNHUB_API_KEY va ICT_SYMBOL_MAP_JSON kerak.")
161
+
            return
162
+
        if not context.args:
163
+
            supported = ", ".join(sorted(ict_symbols.keys()))
164
+
            await msg.reply_text(f"Misol: /ict XAUUSD\nMavjud: {supported}")
165
+
            return
166
+
        key = context.args[0].strip().upper()
167
+
        sym = ict_symbols.get(key)
168
+
        if sym is None:
169
+
            supported = ", ".join(sorted(ict_symbols.keys()))
170
+
            await msg.reply_text(f"Topilmadi: {key}\nMavjud: {supported}")
171
+
            return
172
+
 
173
+
        now = int(time.time())
174
+
        frm = now - 60 * 60 * 24 * 90
175
+
        try:
176
+
            d1 = await finnhub.candles(
177
+
                kind=sym.kind, symbol=sym.symbol, resolution="D", frm=frm, to=now
178
+
            )
179
+
            h4 = await finnhub.candles(
180
+
                kind=sym.kind, symbol=sym.symbol, resolution="240", frm=frm, to=now
181
+
            )
182
+
            h1 = await finnhub.candles(
183
+
                kind=sym.kind, symbol=sym.symbol, resolution="60", frm=frm, to=now
184
+
            )
185
+
        except Exception:
186
+
            await msg.reply_text("Market data olinmadi. Symbol/resolution yoki API key tekshiring.")
187
+
            return
188
+
 
189
+
        levels = compute_key_levels(d1, h4, h1)
190
+
        bias = compute_bias(levels)
191
+
        premium_discount = (
192
+
            "Premium"
193
+
            if levels.current is not None
194
+
            and levels.daily_mid is not None
195
+
            and levels.current > levels.daily_mid
196
+
            else "Discount"
197
+
        )
198
+
        if levels.current is None or levels.daily_mid is None:
199
+
            premium_discount = "Unknown"
200
+
 
201
+
        text = (
202
+
            f"ICT {key} (D1/H4/H1)\n"
203
+
            f"Current: {levels.current}\n"
204
+
            f"D1 bias: {bias} ({premium_discount})\n"
205
+
            f"PDH: {levels.pdh}\n"
206
+
            f"PDL: {levels.pdl}\n"
207
+
            f"EQ(mid): {levels.daily_mid}\n"
208
+
            f"H4 swing high: {levels.h4_swing_high}\n"
209
+
            f"H4 swing low: {levels.h4_swing_low}\n"
210
+
            f"H1 swing high: {levels.h1_swing_high}\n"
211
+
            f"H1 swing low: {levels.h1_swing_low}"
212
+
        )
213
+
        await msg.reply_text(text)
214
+
 
147 215
 
    async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
148 216
 
        msg = update.effective_message
149 217
 
        doc = update.effective_document
150 218
 
        if not msg or not doc:
151 219
 
            return
152 220
 
        if not context.user_data.get("awaiting_quiz_pdf"):
153 221
 
            return
154 222
 
        context.user_data["awaiting_quiz_pdf"] = False
155 223
 
        if gemini is None:
156 224
 
            await msg.reply_text("AI yoqilmagan. GEMINI_API_KEY kerak.")
157 225
 
            return
158 226
 
        if doc.mime_type != "application/pdf":
159 227
 
            await msg.reply_text("Faqat PDF kerak.")
160 228
 
            return
161 229
 
        await msg.reply_text("PDF o‘qilyapti...")
162 230
 
        file = await context.bot.get_file(doc.file_id)
163 231
 
        with tempfile.TemporaryDirectory() as td:
164 232
 
            path = f"{td}/quiz.pdf"
165 233
 
            await file.download_to_drive(custom_path=path)
166 234
 
            reader = PdfReader(path)
167 235
 
            pages = []
168 236
 
            for p in reader.pages[:30]:
169 237
 
                t = p.extract_text() or ""
170 238
 
                t = t.strip()
171 239
 
                if t:
172 240
 
                    pages.append(t)
173 241
 
            full_text = "\n\n".join(pages)
174 242
 
        if not full_text:
175 243
 
            await msg.reply_text("PDF dan matn olinmadi. PDF skan bo‘lsa OCR kerak bo‘ladi.")
176 244
 
            return
177 245
 
 
178 246
 
        title = doc.file_name or "Quiz"
179 247
 
        prompt = (
180 248
 
            "Quyidagi matndan test-quiz tayyorla.\n"
181 249
 
            f"Talablar:\n"
182 250
 
            f"- Maksimum {quiz_max_questions} ta savol\n"
183 251
 
            "- Har savolda 4 ta variant bo‘lsin\n"
184 252
 
            "- answer_index 0..3 oralig‘ida bo‘lsin\n"
185 253
 
            "- Faqat JSON qaytar, hech qanday izohsiz\n"
186 254
 
            'Format: {"title":"...","questions":[{"question":"...","options":["A","B","C","D"],"answer_index":0}]}\n'
187 255
 
            "\n"
188 256
 
            "Matn:\n"
189 257
 
            + full_text[:20000]
190 258
 
        )
191 259
 
        try:
192 260
 
            raw = await gemini.generate_text(prompt)
193 261
 
            quiz_obj = parse_quiz_json(raw)
194 262
 
        except Exception:
195 263
 
            await msg.reply_text("AI quiz yaratishda xatolik berdi. PDF formatini soddaroq qilib ko‘ring.")
196 264
 
            return
197 265
 
 
198 266
 
        q_title = str(quiz_obj.get("title") or title)
199 267
 
        questions = quiz_obj.get("questions") or []
200 268
 
        if not isinstance(questions, list) or not questions:
201 269
 
            await msg.reply_text("Quiz topilmadi. PDF ichida savollar aniq bo‘lsin.")
202 270
 
            return
203 271
 
 
204 272
 
        created_by = update.effective_user.id if update.effective_user else None
205 273
 
        quiz_id = await store.create_quiz(q_title, created_by)
206 274
 
        saved = 0
207 275
 
        for idx, q in enumerate(questions[:quiz_max_questions]):
208 276
 
            if not isinstance(q, dict):
209 277
 
                continue
210 278
 
            question = q.get("question")
211 279
 
            options = q.get("options")
212 280
 
            answer_index = q.get("answer_index")
213 281
 
            if not isinstance(question, str) or not question.strip():
214 282
 
                continue
215 283
 
            if not isinstance(options, list) or len(options) != 4:
216 284
 
                continue
217 285
 
            if not isinstance(answer_index, int) or not (0 <= answer_index <= 3):
218 286
 
                continue
219 287
 
            await store.add_question(
220 288
 
                quiz_id,
221 289
 
                idx,
222 290
 
                question.strip(),
223 291
 
                [str(x) for x in options],
224 292
 
                answer_index,
225 293
 
            )
226 294
 
            saved += 1
227 295
 
 
228 296
 
        if saved == 0:
229 297
 
            await msg.reply_text("Savollar saqlanmadi. PDF formati mos kelmadi.")
230 298
 
            return
231 299
 
 
232 300
 
        kb = InlineKeyboardMarkup(
233 301
 
            [[InlineKeyboardButton("Quizni boshlash", callback_data=f"quiz:start:{quiz_id}")]]
234 302
 
        )
235 303
 
        await msg.reply_text(f"Tayyor: quiz_id={quiz_id}, savollar={saved}", reply_markup=kb)
236 304
 
 
237 305
 
    async def start_quiz_session(
238 306
 
        update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_id: int
239 307
 
    ) -> None:
240 308
 
        msg = update.effective_message
241 309
 
        if not msg:
242 310
 
            return
243 311
 
        questions: list[QuizQuestionRow] = await store.get_quiz_questions(quiz_id)
244 312
 
        if not questions:
245 313
 
            await msg.reply_text("Bu quiz topilmadi.")
246 314
 
            return
247 315
 
        context.user_data["quiz_id"] = quiz_id
248 316
 
        context.user_data["quiz_idx"] = 0
249 317
 
        context.user_data["quiz_score"] = 0
250 318
 
        await send_quiz_question(update, context, questions[0], len(questions))
251 319
 
 
252 320
 
    async def send_quiz_question(
253 321
 
        update: Update,
254 322
 
        context: ContextTypes.DEFAULT_TYPE,
255 323
 
        q: QuizQuestionRow,
256 324
 
        total: int,
257 325
 
    ) -> None:
258 326
 
        msg = update.effective_message
259 327
 
        if not msg:
260 328
 
            return
261 329
 
        quiz_id = int(context.user_data.get("quiz_id"))
262 330
 
        buttons = [
263 331
 
            [
264 332
 
                InlineKeyboardButton(
265 333
 
                    q.options[0], callback_data=f"quiz:ans:{quiz_id}:{q.idx}:0"
266 334
 
                )
267 335
 
            ],
268 336
 
            [
269 337
 
                InlineKeyboardButton(
270 338
 
                    q.options[1], callback_data=f"quiz:ans:{quiz_id}:{q.idx}:1"
271 339
 
                )
272 340
 
            ],
273 341
 
            [
274 342
 
                InlineKeyboardButton(
275 343
 
                    q.options[2], callback_data=f"quiz:ans:{quiz_id}:{q.idx}:2"
276 344
 
                )
277 345
 
            ],
278 346
 
            [
279 347
 
                InlineKeyboardButton(
280 348
 
                    q.options[3], callback_data=f"quiz:ans:{quiz_id}:{q.idx}:3"
281 349
 
                )
282 350
 
            ],
283 351
 
        ]
284 352
 
        text = f"{q.idx + 1}/{total}\n\n{q.question}"
285 353
 
        await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
286 354
 
 
287 355
 
    async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
288 356
 
        q = update.callback_query
289 357
 
        if not q:
290 358
 
            return
291 359
 
        data = q.data or ""
292 360
 
        if data.startswith("quiz:start:"):
293 361
 
            await q.answer()
294 362
 
            try:
295 363
 
                quiz_id = int(data.split(":")[2])
296 364
 
            except Exception:
297 365
 
                return
298 366
 
            fake_update = Update(update.update_id, message=q.message)
299 367
 
            await start_quiz_session(fake_update, context, quiz_id)
300 368
 
            return
301 369
 
 
302 370
 
        if not data.startswith("quiz:ans:"):
303 371
 
            return
304 372
 
        await q.answer()
305 373
 
        parts = data.split(":")
306 374
 
        if len(parts) != 5:
307 375
 
            return
308 376
 
        try:
309 377
 
            quiz_id = int(parts[2])
310 378
 
            idx = int(parts[3])
311 379
 
            choice = int(parts[4])
312 380
 
        except ValueError:
313 381
 
            return
314 382
 
 
315 383
 
        current_quiz = context.user_data.get("quiz_id")
316 384
 
        current_idx = context.user_data.get("quiz_idx")
317 385
 
        if current_quiz != quiz_id or current_idx != idx:
318 386
 
            return
319 387
 
 
320 388
 
        questions: list[QuizQuestionRow] = await store.get_quiz_questions(quiz_id)
321 389
 
        if idx < 0 or idx >= len(questions):
322 390
 
            return
323 391
 
        correct = questions[idx].answer_index == choice
324 392
 
        if correct:
325 393
 
            context.user_data["quiz_score"] = int(context.user_data.get("quiz_score", 0)) + 1
326 394
 
        next_idx = idx + 1
327 395
 
        context.user_data["quiz_idx"] = next_idx
328 396
 
 
329 397
 
        if not q.message:
330 398
 
            return
331 399
 
        if next_idx >= len(questions):
332 400
 
            score = int(context.user_data.get("quiz_score", 0))
333 401
 
            total = len(questions)
334 402
 
            context.user_data.pop("quiz_id", None)
335 403
 
            context.user_data.pop("quiz_idx", None)
336 404
 
            context.user_data.pop("quiz_score", None)
337 405
 
            await q.message.reply_text(f"Natija: {score}/{total}")
338 406
 
            return
339 407
 
        next_q = questions[next_idx]
340 408
 
        fake_update = Update(update.update_id, message=q.message)
341 409
 
        await send_quiz_question(fake_update, context, next_q, len(questions))
342 410
 
 
343 411
 
    async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
344 412
 
        msg = update.effective_message
345 413
 
        chat = update.effective_chat
346 414
 
        if not msg or not chat:
347 415
 
            return
348 416
 
        if chat.type != "private":
349 417
 
            return
350 418
 
        if not context.user_data.get("chat_mode"):
351 419
 
            return
352 420
 
        if gemini is None:
353 421
 
            last = float(context.user_data.get("ai_missing_at", 0.0) or 0.0)
354 422
 
            now = time.time()
355 423
 
            if (now - last) >= 60:
356 424
 
                context.user_data["ai_missing_at"] = now
357 425
 
                await msg.reply_text("AI yoqilmagan. GEMINI_API_KEY sozlanmagan.")
358 426
 
            return
359 427
 
        if not msg.text:
360 428
 
            return
361 429
 
        if context.user_data.get("awaiting_quiz_pdf"):
362 430
 
            return
363 431
 
        text = msg.text.strip()
364 432
 
        if not text:
365 433
 
            return
366 434
 
        prompt = (
367 435
 
            "Sen Telegram botdagi sun'iy intellekt yordamchisisan. "
368 436
 
            "Foydalanuvchi savoliga qisqa va aniq javob ber.\n\n"
369 437
 
            f"Savol: {text}"
370 438
 
        )
371 439
 
        try:
372 440
 
            out = await gemini.generate_text(prompt)
373 441
 
        except Exception:
374 442
 
            await msg.reply_text("AI vaqtincha ishlamayapti.")
375 443
 
            return
376 444
 
        if not out:
377 445
 
            await msg.reply_text("Javob topilmadi.")
378 446
 
            return
379 447
 
        await msg.reply_text(out[:3500])
380 448
 
 
381 449
 
    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
382 450
 
        if not update.effective_message:
383 451
 
            return
384 452
 
        cfg = await get_config()
385 453
 
        await update.effective_message.reply_text(render_config(cfg))
386 454
 
 
387 455
 
    async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
388 456
 
        if not update.effective_message:
389 457
 
            return
390 458
 
        if not is_admin(update):
391 459
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
392 460
 
            return
393 461
 
        cfg = await get_config()
394 462
 
        await update.effective_message.reply_text(
395 463
 
            "Admin panel.\n\n"
396 464
 
            + render_config(cfg)
397 465
 
            + "\n\n"
398 466
 
            "O‘zgartirish:\n"
399 467
 
            "/setsource <chat_id>\n"
400 468
 
            "/settarget <chat_id>\n"
401 469
 
            "/setkeywords <k1,k2,...>\n"
402 470
 
            "/mode <include|exclude>"
403 471
 
        )
404 472
 
 
405 473
 
    async def set_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
406 474
 
        if not update.effective_message:
407 475
 
            return
408 476
 
        if not is_admin(update):
409 477
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
410 478
 
            return
411 479
 
        if not context.args:
412 480
 
            await update.effective_message.reply_text("Misol: /setsource -1001234567890")
413 481
 
            return
414 482
 
        try:
415 483
 
            chat_id = int(context.args[0])
416 484
 
        except ValueError:
417 485
 
            await update.effective_message.reply_text("chat_id son bo‘lishi kerak.")
418 486
 
            return
419 487
 
        await store.set("source_chat_id", str(chat_id))
420 488
 
        await update.effective_message.reply_text("OK.")
421 489
 
 
422 490
 
    async def set_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
423 491
 
        if not update.effective_message:
424 492
 
            return
425 493
 
        if not is_admin(update):
426 494
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
427 495
 
            return
428 496
 
        if not context.args:
429 497
 
            await update.effective_message.reply_text("Misol: /settarget -1001234567890")
430 498
 
            return
431 499
 
        try:
432 500
 
            chat_id = int(context.args[0])
433 501
 
        except ValueError:
434 502
 
            await update.effective_message.reply_text("chat_id son bo‘lishi kerak.")
435 503
 
            return
436 504
 
        await store.set("target_chat_id", str(chat_id))
437 505
 
        await update.effective_message.reply_text("OK.")
438 506
 
 
439 507
 
    async def set_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
440 508
 
        if not update.effective_message:
441 509
 
            return
442 510
 
        if not is_admin(update):
443 511
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
444 512
 
            return
445 513
 
        raw = " ".join(context.args) if context.args else ""
446 514
 
        await store.set("filter_keywords", raw.strip())
447 515
 
        await update.effective_message.reply_text("OK.")
448 516
 
 
449 517
 
    async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
450 518
 
        if not update.effective_message:
451 519
 
            return
452 520
 
        if not is_admin(update):
453 521
 
            await update.effective_message.reply_text("Ruxsat yo‘q.")
454 522
 
            return
455 523
 
        if not context.args:
456 524
 
            await update.effective_message.reply_text("Misol: /mode include")
457 525
 
            return
458 526
 
        mode = context.args[0].strip().lower()
459 527
 
        if mode not in {"include", "exclude"}:
460 528
 
            await update.effective_message.reply_text("Faqat include yoki exclude.")
461 529
 
            return
462 530
 
        await store.set("filter_mode", mode)
463 531
 
        await update.effective_message.reply_text("OK.")
464 532
 
 
465 533
 
    def extract_text(update: Update) -> str:
466 534
 
        msg = update.effective_message
467 535
 
        if not msg:
468 536
 
            return ""
469 537
 
        if msg.text:
470 538
 
            return msg.text
471 539
 
        if msg.caption:
472 540
 
            return msg.caption
473 541
 
        return ""
474 542
 
 
475 543
 
    def match(text: str, cfg: ForwardConfig) -> bool:
476 544
 
        if not cfg.keywords:
477 545
 
            return True
478 546
 
        text_l = text.lower()
479 547
 
        hit = any(k in text_l for k in cfg.keywords)
480 548
 
        if cfg.mode == "include":
481 549
 
            return hit
482 550
 
        return not hit
483 551
 
 
484 552
 
    async def forward_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
485 553
 
        chat = update.effective_chat
486 554
 
        msg = update.effective_message
487 555
 
        if not chat or not msg:
488 556
 
            return
489 557
 
        if chat.type == "private":
490 558
 
            return
491 559
 
 
492 560
 
        cfg = await get_config()
493 561
 
        if cfg.target_chat_id is None:
494 562
 
            return
495 563
 
        if cfg.source_chat_id is not None and chat.id != cfg.source_chat_id:
496 564
 
            return
497 565
 
 
498 566
 
        text = extract_text(update)
499 567
 
        if not match(text, cfg):
500 568
 
            return
501 569
 
 
502 570
 
        await context.bot.forward_message(
503 571
 
            chat_id=cfg.target_chat_id,
504 572
 
            from_chat_id=chat.id,
505 573
 
            message_id=msg.message_id,
506 574
 
        )
507 575
 
 
508 576
 
    app.add_handler(CommandHandler("start", start))
509 577
 
    app.add_handler(CommandHandler("help", help_cmd))
510 578
 
    app.add_handler(CommandHandler("chat", chat_cmd))
511 579
 
    app.add_handler(CommandHandler("id", id_cmd))
512 580
 
    app.add_handler(CommandHandler("status", status))
513 581
 
    app.add_handler(CommandHandler("quiznew", quiznew))
514 582
 
    app.add_handler(CommandHandler("quizzes", quizzes))
515 583
 
    app.add_handler(CommandHandler("quizstart", quizstart))
584
+
    app.add_handler(CommandHandler("ict", ict_cmd))
516 585
 
    app.add_handler(CommandHandler("admin", admin))
517 586
 
    app.add_handler(CommandHandler("setsource", set_source))
518 587
 
    app.add_handler(CommandHandler("settarget", set_target))
519 588
 
    app.add_handler(CommandHandler("setkeywords", set_keywords))
520 589
 
    app.add_handler(CommandHandler("mode", set_mode))
521 590
 
    app.add_handler(CallbackQueryHandler(quiz_callback))
522 591
 
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, handle_pdf))
523 592
 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))
524 593
 
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_filter))
main.py
/workspace/app
+12
-1

 
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
 
    main()
polling.py
/workspace/app
+12
-1

 
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
.env.example
/workspace
+2
-0

 
TELEGRAM_BOT_TOKEN=123456:ABCDEF
2 2
 
RUN_MODE=webhook
3 3
 
WEBHOOK_BASE_URL=https://your-domain.example
4 4
 
WEBHOOK_PATH=/webhook
5 5
 
TELEGRAM_WEBHOOK_SECRET=change-me
6 6
 
ADMIN_IDS=123456789
7 7
 
DATABASE_PATH=bot.db
8 8
 
GEMINI_API_KEY=
9 9
 
GEMINI_MODEL=gemini-1.5-flash
10 10
 
QUIZ_MAX_QUESTIONS=10
11
+
FINNHUB_API_KEY=
12
+
ICT_SYMBOL_MAP_JSON={"XAUUSD":{"kind":"forex","symbol":"OANDA:XAU_USD"},"XAGUSD":{"kind":"forex","symbol":"OANDA:XAG_USD"},"SPX500":{"kind":"stock","symbol":"OANDA:SPX500_USD"},"DXY":{"kind":"stock","symbol":"TVC:DXY"},"US30":{"kind":"stock","symbol":"OANDA:US30_USD"}}
README.md
/workspace
+3
-0
 
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
