
 
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
   
1 1
 
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
