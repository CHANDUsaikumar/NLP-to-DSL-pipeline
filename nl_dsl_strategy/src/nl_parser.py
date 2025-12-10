"""
Natural-language → structured JSON → DSL conversion.
"""

import re


class NLParseError(Exception):
    """Raised when the NL parser cannot extract any usable rule."""
    pass


def normalize_text(text):
    """Lowercase and normalize whitespace."""
    return re.sub(r'\s+', ' ', text.strip().lower())


def parse_natural_language(text):
    """
    Parse a natural-language description of entry/exit rules into a structured JSON format.

    Returns:
        {
            "entry": [ { "left": ..., "operator": ..., "right": ... }, ... ],
            "exit":  [ ... ]
        }
    """
    text_norm = normalize_text(text)

    entry_clauses = []
    exit_clauses = []

    # Identify entry/exit segments
    entry_text = _extract_segment(text_norm, [
        r'(buy when .+?)(?:\.|$)',
        r'(enter when .+?)(?:\.|$)',
        r'(trigger entry when .+?)(?:\.|$)',
        r'(buy .+?)(?:\.|$)',  # fallback
    ])

    exit_text = _extract_segment(text_norm, [
        r'(exit when .+?)(?:\.|$)',
        r'(sell when .+?)(?:\.|$)',
        r'(exit .+?)(?:\.|$)',
        r'(sell .+?)(?:\.|$)',
    ])

    # If no explicit entry/exit, treat whole text as entry
    if not entry_text and not exit_text:
        entry_text = text_norm

    def extract_condition(seg):
        if not seg:
            return ""
        seg = seg.strip()
        m = re.search(r'when (.+)', seg)
        if m:
            return m.group(1)
        # fallback: strip leading verb
        seg = re.sub(r'^(buy|enter|trigger entry|exit|sell)\s+', '', seg)
        return seg

    entry_cond = extract_condition(entry_text)
    exit_cond = extract_condition(exit_text)

    if entry_cond:
        entry_clauses = nl_condition_to_structured(entry_cond)
    if exit_cond:
        exit_clauses = nl_condition_to_structured(exit_cond)

    if not entry_clauses and not exit_clauses:
        raise NLParseError("Could not parse any entry/exit conditions from the input text.")

    return {
        "entry": entry_clauses,
        "exit": exit_clauses,
    }


def _extract_segment(text, patterns):
    """Try multiple regex patterns and return the first matching segment."""
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return ""


def nl_condition_to_structured(cond):
    """
    Convert a condition string (after 'when') into a list of atomic clauses.
    We split on 'and' / 'or'; boolean chaining is recorded in 'bool_with_prev'.
    """
    clauses = []

    parts = re.split(r'\s+(and|or)\s+', cond)
    current_op = "AND"

    for part in parts:
        token = part.strip()
        if token in ("and", "or"):
            current_op = token.upper()
            continue

        if not token:
            continue

        atomic = parse_atomic_clause(token)
        if atomic:
            atomic["bool_with_prev"] = current_op
            clauses.append(atomic)

    return clauses


def parse_atomic_clause(clause):
    """
    Parse a single atomic clause into a structured dict.
    """
    c = clause.strip()

    # 1) Close price vs moving average
    if "close price" in c or "price closes" in c or "close is" in c or "close price is" in c:
        m = re.search(r'(\d+)[-\s]*day moving average', c)
        if m:
            window = int(m.group(1))
            if "above" in c:
                return {"left": "close", "operator": ">", "right": f"sma(close,{window})"}
            if "below" in c:
                return {"left": "close", "operator": "<", "right": f"sma(close,{window})"}

    # 2) Volume above/below some threshold
    if "volume" in c and ("above" in c or "below" in c or "greater than" in c or "less than" in c):
        m = re.search(r'(?:above|greater than|over|below|less than|under)\s+([0-9,.]+|[0-9.]+m)', c)
        if m:
            raw = m.group(1)
            if raw.endswith("m"):
                val = float(raw[:-1]) * 1_000_000
            else:
                val = float(raw.replace(",", ""))
            is_above = any(kw in c for kw in ("above", "greater than", "over"))
            op = ">" if is_above else "<"
            return {"left": "volume", "operator": op, "right": val}

    # 3) RSI conditions
    if "rsi" in c:
        m = re.search(r'rsi\s*\(\s*(\d+)\s*\)', c)
        window = int(m.group(1)) if m else 14

        if "below" in c:
            thr_match = re.search(r'below\s+(\d+(\.\d+)?)', c)
            if thr_match:
                thr = float(thr_match.group(1))
                return {"left": f"rsi(close,{window})", "operator": "<", "right": thr}

        if "above" in c:
            thr_match = re.search(r'above\s+(\d+(\.\d+)?)', c)
            if thr_match:
                thr = float(thr_match.group(1))
                return {"left": f"rsi(close,{window})", "operator": ">", "right": thr}

    # 4) Cross above yesterday's high
    if "crosses above" in c and "yesterday" in c and "high" in c:
        return {"left": "close", "operator": "CROSSOVER", "right": "high[1]"}

    # 5) Volume increase by X percent compared to last week
    if "volume" in c and "percent" in c and "last week" in c:
        m = re.search(r'more than\s+(\d+(\.\d+)?)\s*percent', c)
        if m:
            pct = float(m.group(1))
            factor = 1.0 + pct / 100.0
            return {
                "left": "volume",
                "operator": ">",
                "right": f"sma(volume,5)*{factor}",
            }

    # 6) Generic "<field> is above/below <number>"
    m = re.search(r'(close|price|volume)\s+is\s+(above|below)\s+([0-9,.]+)', c)
    if m:
        field_raw, cmp_raw, val_raw = m.groups()
        field = "close" if field_raw in ("price", "close") else "volume"
        op = ">" if cmp_raw == "above" else "<"
        val = float(val_raw.replace(",", ""))
        return {"left": field, "operator": op, "right": val}

    return None


def structured_to_dsl(structured):
    """
    Convert the JSON-style structure into our DSL.
    """

    def conds_to_expr(conds):
        if not conds:
            return "False"
        exprs = []
        for cond in conds:
            left = cond["left"]
            op = cond["operator"]
            right = cond["right"]
            exprs.append(f"{left} {op} {right}")
        return " AND ".join(exprs)

    entry_expr = conds_to_expr(structured.get("entry", []))
    exit_expr = conds_to_expr(structured.get("exit", []))

    return f"ENTRY: {entry_expr}\nEXIT: {exit_expr}"


def nl_to_structured_and_dsl(nl_text):
    """
    Convenience function to go directly from natural language to:
    - structured JSON
    - DSL text
    """
    structured = parse_natural_language(nl_text)
    dsl = structured_to_dsl(structured)
    return structured, dsl
"""
Natural-language → structured JSON → DSL conversion.
"""

import re


class NLParseError(Exception):
    """Raised when the NL parser cannot extract any usable rule."""
    pass


def normalize_text(text):
    """Lowercase and normalize whitespace."""
    return re.sub(r'\s+', ' ', text.strip().lower())


def parse_natural_language(text):
    """
    Parse a natural-language description of entry/exit rules into a structured JSON format.

    Returns:
        {
            "entry": [ { "left": ..., "operator": ..., "right": ... }, ... ],
            "exit":  [ ... ]
        }
    """
    text_norm = normalize_text(text)

    entry_clauses = []
    exit_clauses = []

    # Identify entry/exit segments
    entry_text = _extract_segment(text_norm, [
        r'(buy when .+?)(?:\.|$)',
        r'(enter when .+?)(?:\.|$)',
        r'(trigger entry when .+?)(?:\.|$)',
        r'(buy .+?)(?:\.|$)',  # fallback
    ])

    exit_text = _extract_segment(text_norm, [
        r'(exit when .+?)(?:\.|$)',
        r'(sell when .+?)(?:\.|$)',
        r'(exit .+?)(?:\.|$)',
        r'(sell .+?)(?:\.|$)',
    ])

    # If no explicit entry/exit, treat whole text as entry
    if not entry_text and not exit_text:
        entry_text = text_norm

    def extract_condition(seg):
        if not seg:
            return ""
        seg = seg.strip()
        m = re.search(r'when (.+)', seg)
        if m:
            return m.group(1)
        # fallback: strip leading verb
        seg = re.sub(r'^(buy|enter|trigger entry|exit|sell)\s+', '', seg)
        return seg

    entry_cond = extract_condition(entry_text)
    exit_cond = extract_condition(exit_text)

    if entry_cond:
        entry_clauses = nl_condition_to_structured(entry_cond)
    if exit_cond:
        exit_clauses = nl_condition_to_structured(exit_cond)

    if not entry_clauses and not exit_clauses:
        raise NLParseError("Could not parse any entry/exit conditions from the input text.")

    return {
        "entry": entry_clauses,
        "exit": exit_clauses,
    }


def _extract_segment(text, patterns):
    """Try multiple regex patterns and return the first matching segment."""
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return ""


def nl_condition_to_structured(cond):
    """
    Convert a condition string (after 'when') into a list of atomic clauses.
    We split on 'and' / 'or'; boolean chaining is recorded in 'bool_with_prev'.
    """
    clauses = []

    parts = re.split(r'\s+(and|or)\s+', cond)
    current_op = "AND"

    for part in parts:
        token = part.strip()
        if token in ("and", "or"):
            current_op = token.upper()
            continue

        if not token:
            continue

        atomic = parse_atomic_clause(token)
        if atomic:
            atomic["bool_with_prev"] = current_op
            clauses.append(atomic)

    return clauses


def parse_atomic_clause(clause):
    """
    Parse a single atomic clause into a structured dict.
    """
    c = clause.strip()

    # 1) Close price vs moving average
    if "close price" in c or "price closes" in c or "close is" in c or "close price is" in c:
        m = re.search(r'(\d+)[-\s]*day moving average', c)
        if m:
            window = int(m.group(1))
            if "above" in c:
                return {"left": "close", "operator": ">", "right": f"sma(close,{window})"}
            if "below" in c:
                return {"left": "close", "operator": "<", "right": f"sma(close,{window})"}

    # 2) Volume above/below some threshold
    if "volume" in c and ("above" in c or "below" in c or "greater than" in c or "less than" in c):
        m = re.search(r'(?:above|greater than|over|below|less than|under)\s+([0-9,.]+|[0-9.]+m)', c)
        if m:
            raw = m.group(1)
            if raw.endswith("m"):
                val = float(raw[:-1]) * 1_000_000
            else:
                val = float(raw.replace(",", ""))
            is_above = any(kw in c for kw in ("above", "greater than", "over"))
            op = ">" if is_above else "<"
            return {"left": "volume", "operator": op, "right": val}

    # 3) RSI conditions
    if "rsi" in c:
        m = re.search(r'rsi\s*\(\s*(\d+)\s*\)', c)
        window = int(m.group(1)) if m else 14

        if "below" in c:
            thr_match = re.search(r'below\s+(\d+(\.\d+)?)', c)
            if thr_match:
                thr = float(thr_match.group(1))
                return {"left": f"rsi(close,{window})", "operator": "<", "right": thr}

        if "above" in c:
            thr_match = re.search(r'above\s+(\d+(\.\d+)?)', c)
            if thr_match:
                thr = float(thr_match.group(1))
                return {"left": f"rsi(close,{window})", "operator": ">", "right": thr}

    # 4) Cross above yesterday's high
    if "crosses above" in c and "yesterday" in c and "high" in c:
        return {"left": "close", "operator": "CROSSOVER", "right": "high[1]"}

    # 5) Volume increase by X percent compared to last week
    if "volume" in c and "percent" in c and "last week" in c:
        m = re.search(r'more than\s+(\d+(\.\d+)?)\s*percent', c)
        if m:
            pct = float(m.group(1))
            factor = 1.0 + pct / 100.0
            return {
                "left": "volume",
                "operator": ">",
                "right": f"sma(volume,5)*{factor}",
            }

    # 6) Generic "<field> is above/below <number>"
    m = re.search(r'(close|price|volume)\s+is\s+(above|below)\s+([0-9,.]+)', c)
    if m:
        field_raw, cmp_raw, val_raw = m.groups()
        field = "close" if field_raw in ("price", "close") else "volume"
        op = ">" if cmp_raw == "above" else "<"
        val = float(val_raw.replace(",", ""))
        return {"left": field, "operator": op, "right": val}

    return None


def structured_to_dsl(structured):
    """
    Convert the JSON-style structure into our DSL.
    """

    def conds_to_expr(conds):
        if not conds:
            return "False"
        exprs = []
        for cond in conds:
            left = cond["left"]
            op = cond["operator"]
            right = cond["right"]
            exprs.append(f"{left} {op} {right}")
        return " AND ".join(exprs)

    entry_expr = conds_to_expr(structured.get("entry", []))
    exit_expr = conds_to_expr(structured.get("exit", []))

    return f"ENTRY: {entry_expr}\nEXIT: {exit_expr}"


def nl_to_structured_and_dsl(nl_text):
    """
    Convenience function to go directly from natural language to:
    - structured JSON
    - DSL text
    """
    structured = parse_natural_language(nl_text)
    dsl = structured_to_dsl(structured)
    return structured, dsl
