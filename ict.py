1
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
 
