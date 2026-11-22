"""In-memory URL shortener backed by custom hash tables."""

from urllib.parse import urlsplit

from src.base62 import decode, encode
from src.hash_table import HashTable


class URLShortener:
    """Shorten absolute HTTP(S) URLs and expand their Base62 codes."""

    def __init__(self):
        self._url_to_code: HashTable[str] = HashTable()
        self._code_to_url: HashTable[str] = HashTable()
        self._next_id = 0

    def shorten(self, url: str) -> str:
        """Return a stable Base62 code for a valid absolute HTTP(S) URL."""
        self._validate_url(url)
        exists, existing_code, _ = self._url_to_code.search(url)
        if exists:
            if existing_code is None:
                raise RuntimeError("stored URL has no short code")
            return existing_code

        code = encode(self._next_id)
        self._next_id += 1
        self._url_to_code.put(url, code)
        self._code_to_url.put(code, url)
        return code

    def expand(self, code: str) -> str:
        """Return the original URL for a registered Base62 code."""
        if not isinstance(code, str):
            raise ValueError("code must be a Base62 string")
        decode(code)
        try:
            return self._code_to_url.get(code)
        except KeyError:
            raise ValueError(f"unknown short code: {code!r}") from None

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str):
            raise ValueError("URL must be a string")
        if not url or url != url.strip() or any(character.isspace() for character in url):
            raise ValueError("URL must not be empty or contain whitespace")

        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            parsed.port
        except ValueError as error:
            raise ValueError(f"invalid URL: {error}") from None

        if parsed.scheme not in ("http", "https") or not parsed.netloc or not hostname:
            raise ValueError("URL must be an absolute HTTP or HTTPS URL with a hostname")
        authority = parsed.netloc.rsplit("@", 1)[-1]
        if authority.endswith(":"):
            raise ValueError("URL port must not be empty")
