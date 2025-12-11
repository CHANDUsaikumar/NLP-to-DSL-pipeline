"""
Validation utilities for field names and indicators.

- validate_field_name(name): ensures name is one of allowed data fields
- validate_indicator(name, argc): ensures indicator exists and arity is valid
"""
from typing import Set, Dict, Tuple

# Allowed base fields from market data
ALLOWED_FIELDS: Set[str] = {"open", "high", "low", "close", "volume", "date"}

# Indicator allowed arities (number of arguments). Some indicators accept 1 or 2 args.
# For example: SMA(series, window) or SMA(window) depending on pipeline; we treat as 1|2.
ALLOWED_INDICATORS: Dict[str, Tuple[int, ...]] = {
    "sma": (1, 2),
    "ema": (1, 2),
    "rsi": (1, 2),
    "shift": (2,),
}


def validate_field_name(name: str) -> None:
    """
    Validate a field name.

    Raises ValueError if the name is not in ALLOWED_FIELDS.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("Field name must be a non-empty string.")
    n = name.strip().lower()
    if n not in ALLOWED_FIELDS:
        raise ValueError(
            f"Unknown field name '{name}'. Allowed fields: {sorted(ALLOWED_FIELDS)}"
        )


def validate_indicator(name: str, argc: int) -> None:
    """
    Validate an indicator name and argument count.

    Allowed indicators:
      - sma: accepts 1 or 2 args (series, window)
      - ema: accepts 1 or 2 args
      - rsi: accepts 1 or 2 args

    Raises ValueError with an informative message on failure.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("Indicator name must be a non-empty string.")
    if not isinstance(argc, int) or argc < 0:
        raise ValueError("Indicator argc must be a non-negative integer.")

    n = name.strip().lower()
    allowed = ALLOWED_INDICATORS.get(n)
    if allowed is None:
        raise ValueError(
            f"Unknown indicator '{name}'. Allowed indicators: "
            f"{', '.join(sorted(ALLOWED_INDICATORS.keys()))}"
        )
    if argc not in allowed:
        raise ValueError(
            f"Indicator '{name}' received {argc} args; allowed arities: {allowed}"
        )
