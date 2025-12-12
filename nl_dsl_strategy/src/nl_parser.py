import re


def normalize_text(text):
    """Lowercase and normalize whitespace."""
    return re.sub(r'\s+', ' ', text.strip().lower())


def _extract_segment(text: str, patterns: list) -> str:
    """Try multiple regex patterns and return the first matching segment."""
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return ""


def parse_natural_language_to_structured(nl_text: str) -> dict:
    """
    Parse natural language into a canonical structured JSON dict without converting to DSL.

    Schema:
      {
        "entry": [condition, ...],
        "exit": [condition, ...]
      }
    where each condition is:
      {
        "left": <string or {"type":"indicator","name":..., "args":[...]}>,
        "operator": one of [">","<",">=","<=","=="],
        "right": <number or string or indicator dict>,
        "modifiers": optional dict like {"lag":5, "percent":0.3, "cross":true}
      }

    Example:
      Input: "Buy when the close price is above the 20-day moving average and volume is above 1 million."
      Returns (entry shown):
        [
          {"left": "close", "operator": ">", "right": {"type":"indicator","name":"sma","args":["close",20]}},
          {"left": "volume", "operator": ">", "right": 1000000}
        ]
    """

    text = normalize_text(nl_text)

    def indicator(name: str, *args):
        return {"type": "indicator", "name": name, "args": list(args)}

    def parse_segment(seg_text: str) -> list:
        if not seg_text:
            return []
        # Strengthened splitting: capture phrases with their connective
        tokens = re.split(r"\s+(and|or)\s+", seg_text)
        phrase_chain = []  # list of (clause_text, connective_before)
        current_bool = None
        for tok in tokens:
            tok = tok.strip()
            if tok in ("and", "or"):
                current_bool = tok.upper()
            elif tok:
                phrase_chain.append((tok, current_bool or "AND"))
                current_bool = None

        clauses = []
        for (c, connective) in phrase_chain:

            # 1) close above/below N-day moving average
            if ("close price" in c or "close" in c) and ("moving average" in c or "ma" in c):
                m = re.search(r"(\d+)[-\s]*day\s+(moving average|ma)", c)
                if m and ("above" in c or "below" in c):
                    window = int(m.group(1))
                    op = ">" if "above" in c else "<"
                    clauses.append({
                        "left": "close",
                        "operator": op,
                        "right": indicator("sma", "close", window),
                        "bool_with_prev": connective
                    })
                    continue

            # 2) volume threshold (e.g., above 1 million)
            if "volume" in c and ("above" in c or "below" in c or "greater than" in c or "less than" in c or "over" in c or "under" in c or "exceeds" in c or "drops below" in c or "breaches" in c or "pierces" in c):
                m = re.search(r"(?:above|greater than|over|below|less than|under)\s+((?:[0-9]+\s+million)|(?:[0-9.]+m)|(?:[0-9.]+k)|(?:[0-9]+\s+thousand)|(?:[0-9,.]+))", c)
                if m:
                    raw = m.group(1)
                    raw_clean = raw.strip().rstrip(".,")
                    if raw_clean.endswith("m"):
                        val = float(raw_clean[:-1]) * 1_000_000
                    elif raw_clean.endswith("k"):
                        val = float(raw_clean[:-1]) * 1_000
                    elif (raw_clean.endswith(" million") or " million" in raw_clean):
                        try:
                            num = float(raw_clean.split()[0])
                        except Exception:
                            num = float(re.findall(r"\d+(?:\.\d+)?", raw_clean)[0])
                        val = num * 1_000_000
                    elif (raw_clean.endswith(" thousand") or " thousand" in raw_clean):
                        try:
                            num = float(raw_clean.split()[0])
                        except Exception:
                            num = float(re.findall(r"\d+(?:\.\d+)?", raw_clean)[0])
                        val = num * 1_000
                    else:
                        val = float(raw_clean.replace(",", ""))
                    is_above = any(kw in c for kw in ("above", "greater than", "over", "exceeds", "breaches", "pierces")) and ("drops below" not in c)
                    op = ">" if is_above else "<"
                    clauses.append({
                        "left": "volume",
                        "operator": op,
                        "right": val,
                        "bool_with_prev": connective
                    })
                    continue

            # 3) Enter when price crosses above yesterday's high -> use modifiers lag=1 and cross=true
            if (re.search(r"\bcross(?:es|ed)?\s+over\b", c) or re.search(r"\bcross(?:es|ed)?\s+under\b", c) or "crosses above" in c or "crosses below" in c or re.search(r"\bbreaks\s+(above|below)\b", c)) and "yesterday" in c and ("high" in c or "low" in c):
                clauses.append({
                    "left": "close",
                    "operator": ">" if ("above" in c or re.search(r"over", c)) else "<",
                    "right": "high" if "high" in c else "low",
                    "modifiers": {"lag": 1, "cross": True},
                    "bool_with_prev": connective
                })
                continue

            # 4) Exit when RSI(14) is below/above X
            if "rsi" in c:
                m = re.search(r"rsi\s*\(\s*(\d+)\s*\)", c)
                window = int(m.group(1)) if m else 14
                # aliases: overbought/oversold
                # support custom thresholds/periods like "RSI(7) overbought at 80"
                if "overbought" in c:
                    thr_match = re.search(r"overbought\s+(?:at|above)\s+(\d+(\.\d+)?)", c)
                    thr = float(thr_match.group(1)) if thr_match else 70.0
                    clauses.append({
                        "left": indicator("rsi", "close", window),
                        "operator": ">",
                        "right": thr,
                        "bool_with_prev": connective
                    })
                    continue
                if "oversold" in c:
                    thr_match = re.search(r"oversold\s+(?:at|below)\s+(\d+(\.\d+)?)", c)
                    thr = float(thr_match.group(1)) if thr_match else 30.0
                    clauses.append({
                        "left": indicator("rsi", "close", window),
                        "operator": "<",
                        "right": thr,
                        "bool_with_prev": connective
                    })
                    continue
                if "below" in c:
                    thr_match = re.search(r"below\s+(\d+(\.\d+)?)", c)
                    if thr_match:
                        thr = float(thr_match.group(1))
                        clauses.append({
                            "left": indicator("rsi", "close", window),
                            "operator": "<",
                            "right": thr,
                            "bool_with_prev": connective
                        })
                        continue
                if "above" in c:
                    thr_match = re.search(r"above\s+(\d+(\.\d+)?)", c)
                    if thr_match:
                        thr = float(thr_match.group(1))
                        clauses.append({
                            "left": indicator("rsi", "close", window),
                            "operator": ">",
                            "right": thr,
                            "bool_with_prev": connective
                        })
                        continue

            # 5) Volume increases by more than X percent compared to last week -> modifiers percent, lag
            if "volume" in c and "percent" in c and ("last week" in c or "previous week" in c):
                m = re.search(r"more than\s+(\d+(\.\d+)?)\s*percent", c)
                if m:
                    pct = float(m.group(1)) / 100.0
                    clauses.append({
                        "left": "volume",
                        "operator": ">",
                        "right": "volume",
                        "modifiers": {"percent": pct, "lag": 5},
                        "bool_with_prev": connective
                    })
                    continue

            # 6) Moving average cross phrases: cross above/below the N-day MA
            if (("cross" in c or re.search(r"\bcross(?:es|ed)?\b", c)) and ("above" in c or "below" in c or "over" in c or "under" in c)) and ("moving average" in c or "ma" in c or "ema" in c or re.search(r"\bema\b", c)):
                m = re.search(r"(\d+)[-\s]*day\s+(moving average|ma|ema)", c)
                if m:
                    window = int(m.group(1))
                    is_above = "above" in c
                    clauses.append({
                        "left": "close",
                        "operator": ">" if is_above else "<",
                        "right": indicator("sma", "close", window) if "moving average" in c or "ma" in c else indicator("ema", "close", window),
                        "modifiers": {"cross": True},
                        "bool_with_prev": connective
                    })
                    continue

            # 7) Last X days -> lag
            m_last = re.search(r"last\s+(\d+)\s+(days|day|sessions|bars|trading days)", c)
            if m_last and ("above" in c or "below" in c):
                lag_x = int(m_last.group(1))
                # simplistic: compare field to its lagged value
                fm = re.search(r"(close|price|volume|high|low)\s+is\s+(above|below)\s+", c)
                if fm:
                    field_raw, cmp_raw = fm.groups()
                    field = "close" if field_raw in ("price", "close") else (field_raw)
                    op = ">" if cmp_raw == "above" else "<"
                    clauses.append({
                        "left": field,
                        "operator": op,
                        "right": field,
                        "modifiers": {"lag": lag_x},
                        "bool_with_prev": connective
                    })
                    continue

            # 8) Generic pattern: <field> is above/below <number>
            gm = re.search(r"(close|price|volume)\s+is\s+(above|below)\s+([0-9,.]+)", c)
            if gm:
                field_raw, cmp_raw, val_raw = gm.groups()
                field = "close" if field_raw in ("price", "close") else "volume"
                op = ">" if cmp_raw == "above" else "<"
                val = float(val_raw.replace(",", ""))
                clauses.append({
                    "left": field,
                    "operator": op,
                    "right": val,
                    "bool_with_prev": connective
                })
                continue

            # 9) EMA direct mapping: EMA(N) or N-day EMA
            m_ema = re.search(r"ema\s*\(\s*(\d+)\s*\)|\b(\d+)[-\s]*day\s+ema\b", c)
            if m_ema and ("above" in c or "below" in c):
                window = int(next(g for g in m_ema.groups() if g))
                op = ">" if "above" in c else "<"
                clauses.append({
                    "left": "close",
                    "operator": op,
                    "right": indicator("ema", "close", window),
                    "bool_with_prev": connective
                })
                continue

            # 10) MACD vs signal and histogram
            if "macd" in c:
                # macd above/below signal line
                if re.search(r"macd\s+(?:line\s+)?(?:is\s+)?(above|below)\s+(?:the\s+)?signal(?:\s+line)?", c):
                    is_above = "above" in c
                    clauses.append({
                        "left": indicator("macd", "close"),
                        "operator": ">" if is_above else "<",
                        "right": indicator("macd_signal", "close"),
                        "bool_with_prev": connective
                    })
                    continue
                # macd histogram above/below 0
                mh = re.search(r"macd\s+hist(?:ogram)?\s+(?:is\s+)?(above|below)\s+0", c)
                if mh:
                    is_above = mh.group(1) == "above"
                    clauses.append({
                        "left": indicator("macd_hist", "close"),
                        "operator": ">" if is_above else "<",
                        "right": 0.0,
                        "bool_with_prev": connective
                    })
                    continue

            # 11) Bollinger Bands upper/lower comparisons
            if "bollinger" in c or "band" in c:
                # Capture optional params: window/stddev from forms like '(20,2)' or '20-day ... 2 std'
                params_tuple = re.search(r"\((\d+)\s*,\s*(\d+(?:\.\d+)?)\)", c)
                window_std_phrase = re.search(r"(\d+)[-\s]*day\s+bollinger\s+band\s*(\d+(?:\.\d+)?)\s*std", c)
                bb_window = None
                bb_std = None
                if params_tuple:
                    bb_window = int(params_tuple.group(1))
                    bb_std = float(params_tuple.group(2))
                elif window_std_phrase:
                    bb_window = int(window_std_phrase.group(1))
                    bb_std = float(window_std_phrase.group(2))
                else:
                    # default
                    bb_window = 20
                    bb_std = 2.0
                # price above/below upper/lower band with synonyms
                b = re.search(r"(above|below|exceeds|drops below|breaches|pierces)\s+(upper|lower)\s+bollinger\s+band", c)
                if b:
                    cmp, which = b.groups()
                    is_above = cmp in ("above", "exceeds", "breaches", "pierces")
                    op = ">" if is_above else "<"
                    rhs = indicator("bbupper", "close", bb_window, bb_std) if which == "upper" else indicator("bblower", "close", bb_window, bb_std)
                    clauses.append({
                        "left": "close",
                        "operator": op,
                        "right": rhs,
                        "bool_with_prev": connective
                    })
                    continue

        return clauses

    # Try to use spaCy if available and text suggests complex structure; fall back to regex
    structured_entry = []
    structured_exit = []

    # Attempt spaCy optional backend first
    try:
        from . import nlp_spacy  # type: ignore
        spacy_struct = nlp_spacy.spacy_parse_nl(nl_text)
        if spacy_struct and (spacy_struct.get("entry") or spacy_struct.get("exit")):
            # Map spaCy structured into canonical indicator dicts where possible
            def map_clause(cl):
                left = cl.get("left")
                right = cl.get("right")
                op = cl.get("operator")
                mapped = {"left": left, "operator": op, "right": right}
                if "modifiers" in cl:
                    mapped["modifiers"] = cl["modifiers"]
                return mapped
            structured_entry = [map_clause(c) for c in spacy_struct.get("entry", [])]
            structured_exit = [map_clause(c) for c in spacy_struct.get("exit", [])]
    except Exception:
        # spaCy not available; proceed with regex-only
        pass

    if not structured_entry and not structured_exit:
        # Regex pathway: extract entry/exit segments, then parse
        entry_text = _extract_segment(text, [
            r'(buy when .+?)(?:\.|$)',
            r'(enter when .+?)(?:\.|$)',
            r'(trigger entry when .+?)(?:\.|$)',
            r'(buy .+?)(?:\.|$)'
        ])
        exit_text = _extract_segment(text, [
            r'(exit when .+?)(?:\.|$)',
            r'(sell when .+?)(?:\.|$)',
            r'(exit .+?)(?:\.|$)',
            r'(sell .+?)(?:\.|$)'
        ])

        # If nothing explicit, treat whole as entry
        if not entry_text and not exit_text:
            entry_text = text

        def strip_lead(seg: str) -> str:
            if not seg:
                return ""
            seg = seg.strip()
            m = re.search(r"when (.+)", seg)
            if m:
                return m.group(1)
            return re.sub(r"^(buy|enter|trigger entry|exit|sell)\s+", "", seg)

        structured_entry = parse_segment(strip_lead(entry_text))
        structured_exit = parse_segment(strip_lead(exit_text))

    return {"entry": structured_entry, "exit": structured_exit}


def structured_to_dsl(structured: dict) -> str:
    """
    Convert structured JSON produced by parse_natural_language_to_structured into DSL text.

    Handles:
    - Indicators SMA/RSI
    - CROSSOVER/CROSSUNDER via modifiers {cross: true}
    - Percent and lag modifiers by expanding right-hand side with shift and scaling
    - Fallback to a safely-false comparison when a side has no clauses
    """

    def fmt_side(side):
        if isinstance(side, dict) and side.get("type") == "indicator":
            name = str(side.get("name", "")).upper()
            args = side.get("args", [])
            if name == "SMA" and len(args) >= 2:
                return f"SMA({args[0]}, {int(args[1])})"
            if name == "RSI" and len(args) >= 2:
                return f"RSI({args[0]}, {int(args[1])})"
            if name == "EMA" and len(args) >= 2:
                return f"EMA({args[0]}, {int(args[1])})"
            if name == "MACD_SIGNAL":
                return f"MACD_SIGNAL({args[0]})"
            if name == "MACD_HIST":
                return f"MACD_HIST({args[0]})"
            if name == "MACD":
                return f"MACD({args[0]})"
            if name == "BBUPPER":
                return f"BBUPPER({args[0]}, {int(args[1])}, {float(args[2])})"
            if name == "BBLOWER":
                return f"BBLOWER({args[0]}, {int(args[1])}, {float(args[2])})"
        return str(side)

    def clause_to_dsl(cl):
        left, op, right = cl.get("left"), cl.get("operator"), cl.get("right")
        mods = cl.get("modifiers", {}) or {}

        # CROSSOVER/CROSSUNDER mapping
        if mods.get("cross"):
            direction = "CROSSOVER" if (op is None or op == ">") else "CROSSUNDER"
            rhs = fmt_side(right)
            lag = int(mods.get("lag", 0))
            if lag > 0:
                rhs = f"SHIFT({rhs}, {lag})"
            return f"{fmt_side(left)} {direction} {rhs}"

        # Percent/lag mapping on right side
        rhs = fmt_side(right)
        lag = int(mods.get("lag", 0))
        pct = float(mods.get("percent", 0.0))
        if lag > 0:
            rhs = f"SHIFT({rhs}, {lag})"
        if pct:
            rhs = f"{rhs} * {1.0 + pct}"

        return f"{fmt_side(left)} {op} {rhs}"

    def join_clauses(clauses):
        if not clauses:
            return "FALSE"  # to be supported by DSL parser
        # preserve AND/OR order from bool_with_prev
        parts = []
        first = True
        for c in clauses:
            expr = clause_to_dsl(c)
            if first:
                parts.append(expr)
                first = False
            else:
                conj = c.get("bool_with_prev", "AND")
                parts.append(conj + " " + expr)
        return " ".join(parts)

    entry = join_clauses(structured.get("entry", []))
    exit_ = join_clauses(structured.get("exit", []))
    return f"ENTRY: {entry}\nEXIT:  {exit_}"

def extract_phrases_with_spacy(nl_text: str) -> dict:
    """
    Extract key phrases from natural language using spaCy when available.

    Detects:
      - numeric tokens with units (e.g., "20-day moving average", "1 million")
      - comparative verbs: above/below/greater/less/crosses/increases
      - temporal words: yesterday, last week

    Falls back to simple regex if spaCy isn't installed or model isn't available.

    Returns a dict: {'indicators':[...], 'comparisons':[...], 'times':[...], 'numbers':[...]}
    """
    text = nl_text if isinstance(nl_text, str) else str(nl_text)

    result = {
        'indicators': [],
        'comparisons': [],
        'times': [],
        'numbers': []
    }

    try:
        import spacy  # type: ignore
        from spacy.matcher import PhraseMatcher  # type: ignore
        try:
            nlp = spacy.load('en_core_web_sm')
        except Exception:
            nlp = spacy.blank('en')

        doc = nlp(text)

        matcher = PhraseMatcher(nlp.vocab, attr='LOWER')
        comp_phrases = ["above", "below", "greater", "greater than", "less", "less than", "over", "under", "crosses", "increases"]
        time_phrases = ["yesterday", "last week", "previous week"]
        matcher.add("COMPARISON", [nlp.make_doc(p) for p in comp_phrases])
        matcher.add("TIME", [nlp.make_doc(p) for p in time_phrases])

        matches = matcher(doc)
        for mid, start, end in matches:
            label = nlp.vocab.strings[mid]
            span = doc[start:end]
            if label == "COMPARISON":
                result['comparisons'].append(span.text)
            elif label == "TIME":
                result['times'].append(span.text)

        for i, tok in enumerate(doc):
            if tok.like_num:
                num_text = tok.text
                unit = None
                lookahead = doc[i+1:i+4]
                la_text = " ".join(t.text for t in lookahead).lower()
                if any(u in la_text for u in ["million", "m", "day", "days"]):
                    unit = la_text.split()[0] if la_text else None
                window_phrase = None
                span3 = doc[i:i+5]
                span3_text = span3.text.lower()
                if re.search(r"\b\d+[-\s]*day\b", span3_text) and ("moving average" in span3_text or "ma" in span3_text):
                    window_phrase = span3.text
                    result['indicators'].append(window_phrase)
                num_entry = {'value': num_text}
                if unit:
                    num_entry['unit'] = unit
                result['numbers'].append(num_entry)

        for chunk in doc.noun_chunks:
            txt = chunk.text.lower()
            if "moving average" in txt or txt == "rsi" or txt.startswith("rsi("):
                result['indicators'].append(chunk.text)

    except ImportError:
        low = text.lower()
        for m in re.finditer(r"\b(\d+)[-\s]*day\s+(moving average|ma)\b", low):
            result['indicators'].append(m.group(0))
        for m in re.finditer(r"\brsi\s*\(\s*\d+\s*\)", low):
            result['indicators'].append(m.group(0))
        for m in re.finditer(r"\b(above|below|greater than|less than|over|under|crosses|increases)\b", low):
            result['comparisons'].append(m.group(0))
        for m in re.finditer(r"\b(yesterday|last week|previous week)\b", low):
            result['times'].append(m.group(0))
        for m in re.finditer(r"\b(\d+[,.]*\d*)\s*(million|m|day|days)\b", low):
            result['numbers'].append({'value': m.group(1), 'unit': m.group(2)})

    def dedupe(seq):
        seen = set()
        out = []
        for x in seq:
            key = x if isinstance(x, str) else tuple(sorted(x.items()))
            if key in seen:
                continue
            seen.add(key)
            out.append(x)
        return out

    result['indicators'] = dedupe(result['indicators'])
    result['comparisons'] = dedupe(result['comparisons'])
    result['times'] = dedupe(result['times'])
    result['numbers'] = dedupe(result['numbers'])

    return result
