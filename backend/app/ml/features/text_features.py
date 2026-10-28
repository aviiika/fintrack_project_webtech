"""
Text preprocessing for transaction descriptions.
Bank descriptions contain reference numbers, UPI handles, truncation artefacts —
we strip these before vectorisation so the model learns merchant names, not noise.
"""
import re

# Regex patterns for noise commonly found in bank transaction descriptions
_RX_LONG_DIGITS   = re.compile(r"\b\d{6,}\b")           # 12+ digit refs: UTR, UPI txn IDs
_RX_UPI_HANDLE    = re.compile(r"@\w+")                 # @okaxis, @paytm, etc.
_RX_BANK_CODES    = re.compile(r"\b(?:NEFT|IMPS|RTGS|UPI|POS|ATM|CR|DR)\b", re.IGNORECASE)
_RX_PUNCT         = re.compile(r"[^\w\s&]")             # keep & for "Food & Dining" style
_RX_WHITESPACE    = re.compile(r"\s+")


def clean_description(text: str) -> str:
    """Normalise a bank description for ML consumption.

    Example:  "UPI/414823910292/ZOMATO/zomato@paytm/PAYMENT"
         ->  "zomato payment"
    """
    if not text:
        return ""
    s = text.lower()
    s = _RX_LONG_DIGITS.sub(" ", s)
    s = _RX_UPI_HANDLE.sub(" ", s)
    s = _RX_BANK_CODES.sub(" ", s)
    s = _RX_PUNCT.sub(" ", s)
    s = _RX_WHITESPACE.sub(" ", s).strip()
    return s


def clean_batch(descriptions: list[str]) -> list[str]:
    """Vectorised helper used by both training and inference."""
    return [clean_description(d) for d in descriptions]
