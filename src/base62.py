"""Base62 conversion using digits, lowercase letters, then uppercase letters."""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode(value: int) -> str:
    """Encode a non-negative integer as a Base62 string."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("value must be an integer")
    if value < 0:
        raise ValueError("value must be non-negative")
    if value == 0:
        return ALPHABET[0]

    encoded = []
    while value:
        value, remainder = divmod(value, BASE)
        encoded.append(ALPHABET[remainder])
    return "".join(reversed(encoded))


def decode(encoded: str) -> int:
    """Decode a Base62 string into a non-negative integer."""
    if not isinstance(encoded, str):
        raise TypeError("encoded value must be a string")
    if not encoded:
        raise ValueError("encoded value must not be empty")

    value = 0
    for character in encoded:
        digit = ALPHABET.find(character)
        if digit == -1:
            raise ValueError(f"invalid Base62 character: {character!r}")
        value = value * BASE + digit
    return value
