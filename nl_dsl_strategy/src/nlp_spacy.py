from __future__ import annotations

import re
from typing import Dict, List, Any

try:
    import spacy
except ImportError:
    spacy = None  # type: ignore


def _ensure_nlp():
    if spacy is None:
        raise ImportError("spaCy is not installed. Please 'pip install spacy' and a model like 'python -m spacy download en_core_web_sm'.")
    try:
        return spacy.load("en_core_web_sm")
    except Exception:
        # try to download or guide user
        raise ImportError("spaCy model 'en_core_web_sm' not found. Install via: python -m spacy download en_core_web_sm")


def spacy_parse_nl(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse NL using spaCy and simple pattern rules.
    Returns structure compatible with structured_to_dsl:
    {"entry": [...], "exit": [...]} clauses with left/operator/right.
    """
    nlp = _ensure_nlp()
    doc = nlp(text)

    # Split into entry/exit sentences heuristically
    entry_sents: List[str] = []
    exit_sents: List[str] = []
    for sent in doc.sents:
        s = sent.text.strip().lower()
        if s.startswith("buy") or (" entry " in s) or s.startswith("enter"):
            entry_sents.append(s)
        elif s.startswith("sell") or s.startswith("exit"):
            exit_sents.append(s)
        else:
            # default to entry if nothing else
            entry_sents.append(s)

    def parse_sentence(s: str) -> List[Dict[str, Any]]:
        clauses: List[Dict[str, Any]] = []
        # detect SMA patterns: e.g., "20 day sma" or "sma( close , 20 )"
        sma_pat = re.findall(r"(\d+)\s*(?:day\s*)?sma", s)
        rsi_pat = re.findall(r"rsi\s*\(?\s*(\d+)?\s*\)?", s)
        # cross above/below
        cross_above = ("crosses above" in s) or ("cross above" in s) or ("crossover" in s)
        cross_below = ("crosses below" in s) or ("cross below" in s) or ("crossunder" in s)
        # thresholds
        m_above = re.findall(r"(close|price|volume|rsi)\s*(?:is\s*)?(?:above|over|>)\s*([0-9.]+m|[0-9.,]+)", s)
        m_below = re.findall(r"(close|price|volume|rsi)\s*(?:is\s*)?(?:below|under|<)\s*([0-9.]+m|[0-9.,]+)", s)

        # SMA crossover with two windows
        if len(sma_pat) >= 2 and (cross_above or cross_below):
            p1, p2 = int(sma_pat[0]), int(sma_pat[1])
            if cross_above:
                clauses.append({"left": f"SMA(close,{p1})", "operator": "CROSSOVER", "right": f"SMA(close,{p2})"})
            if cross_below:
                clauses.append({"left": f"SMA(close,{p1})", "operator": "CROSSUNDER", "right": f"SMA(close,{p2})"})

        # RSI threshold
        if rsi_pat:
            rsi_p = int(rsi_pat[0] or 14)
            # map above/below for RSI
            m = re.search(r"rsi.*?(above|over|>|below|under|<)\s*(\d+(?:\.\d+)?)", s)
            if m:
                comp = m.group(1)
                thr = float(m.group(2))
                op = ">" if comp in ("above", "over", ">") else "<"
                clauses.append({"left": f"RSI(close,{rsi_p})", "operator": op, "right": thr})

        # Generic thresholds for close/price/volume
        for field, val in m_above:
            v = float(val[:-1]) * 1_000_000 if val.endswith("m") else float(val.replace(",", ""))
            fld = "close" if field in ("close", "price") else ("rsi" if field == "rsi" else "volume")
            left = f"RSI(close,14)" if fld == "rsi" else fld
            clauses.append({"left": left, "operator": ">", "right": v})
        for field, val in m_below:
            v = float(val[:-1]) * 1_000_000 if val.endswith("m") else float(val.replace(",", ""))
            fld = "close" if field in ("close", "price") else ("rsi" if field == "rsi" else "volume")
            left = f"RSI(close,14)" if fld == "rsi" else fld
            clauses.append({"left": left, "operator": "<", "right": v})

        return clauses

    entry_clauses: List[Dict[str, Any]] = []
    for s in entry_sents:
        entry_clauses.extend(parse_sentence(s))
    exit_clauses: List[Dict[str, Any]] = []
    for s in exit_sents:
        exit_clauses.extend(parse_sentence(s))

    return {"entry": entry_clauses, "exit": exit_clauses}
