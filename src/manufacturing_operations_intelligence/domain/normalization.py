"""Lossless RAW-to-CLEAN conversions permitted by the Data Contract."""

from __future__ import annotations

import math
import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
COUNT_PATTERN = re.compile(r"[0-9]+(?:\.0+)?\Z")
DECIMAL_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
MISSING_MARKERS = {"NULL", "NONE", "N/A", "NA", "NAN"}
THREE = Decimal("0.001")


class InvalidValue(ValueError):
    """A source value cannot be converted without changing its meaning."""


def is_missing(value: Any) -> bool:
    """Identify contract-defined blanks and explicit missing markers."""
    return (
        value is None
        or isinstance(value, str)
        and (not value.strip() or value.strip().upper() in MISSING_MARKERS)
    )


def normalize(value: Any, kind: str, *, excel: bool, unit: str | None = None) -> Any:
    """Return a canonical value or raise InvalidValue; never impute or round."""
    if isinstance(value, bool):
        raise InvalidValue("Boolean values are not valid business values.")
    if kind == "ID":
        if not isinstance(value, str) or not ID_PATTERN.fullmatch(value.strip()):
            raise InvalidValue("Expected a text identifier of 1–64 allowed ASCII characters.")
        return value.strip()
    if kind == "DATE":
        if excel and isinstance(value, datetime):
            if value.time() != time.min:
                raise InvalidValue("Excel date-time must be at midnight.")
            value = value.date()
        if excel and isinstance(value, date) and not isinstance(value, datetime):
            candidate = value
        elif isinstance(value, str) and DATE_PATTERN.fullmatch(value):
            try:
                candidate = date.fromisoformat(value)
            except ValueError as exc:
                raise InvalidValue("Expected a real ISO calendar date.") from exc
        else:
            raise InvalidValue("Expected ISO YYYY-MM-DD text or an Excel date cell.")
        if not date(2000, 1, 1) <= candidate <= date(2100, 12, 31):
            raise InvalidValue("Date is outside 2000-01-01 through 2100-12-31.")
        return candidate.isoformat()
    if kind == "UNIT":
        allowed = {"ea", "kg", "m", "l"} if unit == "inventory" else {"ea"}
        if not isinstance(value, str) or value.strip().lower() not in allowed:
            raise InvalidValue(f"Expected a unit from {sorted(allowed)}.")
        return value.strip().lower()
    if kind == "COUNT":
        if isinstance(value, str):
            if not COUNT_PATTERN.fullmatch(value):
                raise InvalidValue("Expected a nonnegative whole-number token.")
            number = Decimal(value)
        elif excel and isinstance(value, (int, float, Decimal)):
            if isinstance(value, float) and not math.isfinite(value):
                raise InvalidValue("Count must be finite.")
            number = Decimal(str(value))
        else:
            raise InvalidValue("Expected a whole-number count.")
        if number != number.to_integral_value() or not 0 <= number <= 1_000_000_000:
            raise InvalidValue("Count must be an integer from 0 to 1,000,000,000.")
        return int(number)
    if kind not in {"MINUTES", "STOCK"}:
        raise ValueError(f"Unknown field type: {kind}")
    if isinstance(value, str):
        if not DECIMAL_PATTERN.fullmatch(value):
            raise InvalidValue("Expected a nonnegative decimal token without units or exponent.")
        token = value
    elif excel and isinstance(value, (int, float, Decimal)):
        if isinstance(value, float) and not math.isfinite(value):
            raise InvalidValue("Decimal value must be finite.")
        token = str(value)
    else:
        raise InvalidValue("Expected a finite decimal quantity.")
    try:
        number = Decimal(token)
        if not number.is_finite() or number != number.quantize(THREE):
            raise InvalidValue("Value cannot be represented exactly to three decimal places.")
        maximum = Decimal("1440") if kind == "MINUTES" else Decimal("999999999.999")
        if not 0 <= number <= maximum:
            raise InvalidValue(f"Value must be between 0 and {maximum}.")
        if kind == "STOCK" and unit == "ea" and number != number.to_integral_value():
            raise InvalidValue("Unit 'ea' requires whole stock quantities.")
        return number.quantize(THREE)
    except InvalidOperation as exc:
        raise InvalidValue("Decimal quantity is invalid.") from exc
