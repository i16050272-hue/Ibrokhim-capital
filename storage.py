1 1
 
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
