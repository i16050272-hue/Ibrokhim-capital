1 1
 
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
