
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
