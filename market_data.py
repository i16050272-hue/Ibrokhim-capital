1
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
 
