"""HTTP server for the in-memory URL shortener."""

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from src.shortener import URLShortener

MAX_FORM_BYTES = 16_384


class ShortenerHTTPServer(HTTPServer):
    def __init__(self, server_address: tuple[str, int]):
        self.shortener = URLShortener()
        super().__init__(server_address, ShortenerRequestHandler)


class ShortenerRequestHandler(BaseHTTPRequestHandler):
    server: ShortenerHTTPServer

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self._send_html(200, self._home_page())
            return
        if path == "/table":
            self._send_html(200, self._table_page())
            return
        if path.startswith("/") and len(path) > 1 and "/" not in path[1:]:
            self._redirect(path[1:])
            return
        self._send_html(404, self._error_page("Not found", "Page not found."))

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/shorten":
            self._send_html(404, self._error_page("Not found", "Page not found."))
            return

        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type.lower() != "application/x-www-form-urlencoded":
            self._send_html(
                415,
                self._error_page("Unsupported media type", "Submit the URL form."),
            )
            return

        content_length = self.headers.get("Content-Length")
        try:
            body_length = int(content_length) if content_length is not None else -1
        except ValueError:
            body_length = -1
        if body_length < 0:
            self._send_html(400, self._error_page("Bad request", "Invalid form length."))
            return
        if body_length > MAX_FORM_BYTES:
            self._send_html(
                413,
                self._error_page("Request too large", "The form is too large."),
            )
            return

        try:
            form = parse_qs(
                self.rfile.read(body_length).decode("utf-8"),
                keep_blank_values=True,
                strict_parsing=True,
            )
        except (UnicodeDecodeError, ValueError):
            self._send_html(400, self._error_page("Bad request", "Invalid form data."))
            return

        urls = form.get("url", [])
        if len(urls) != 1:
            self._send_html(400, self._error_page("Bad request", "Enter one URL."))
            return

        try:
            code = self.server.shortener.shorten(urls[0])
        except ValueError as error:
            self._send_html(400, self._error_page("Invalid URL", str(error)))
            return

        self._send_html(200, self._result_page(urls[0], code))

    def _redirect(self, code: str) -> None:
        try:
            url = self.server.shortener.expand(code)
        except ValueError:
            self._send_html(
                404,
                self._error_page("Short link not found", "This code is not registered."),
            )
            return

        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _home_page(self) -> str:
        content = """
<main>
  <h1>URL shortener</h1>
  <form action="/shorten" method="post">
    <label for="url">URL to shorten</label>
    <input id="url" name="url" type="url" required>
    <button type="submit">Shorten</button>
  </form>
</main>
"""
        return self._page("URL shortener", content)

    def _result_page(self, url: str, code: str) -> str:
        safe_url = escape(url, quote=True)
        safe_code = escape(code, quote=True)
        link_path = f"/{safe_code}"
        content = f"""
<main>
  <h1>Short link created</h1>
  <p>Original URL: <a href="{safe_url}">{safe_url}</a></p>
  <p>Short code: <code>{safe_code}</code></p>
  <p>Short link: <a href="{link_path}">{link_path}</a></p>
  <p><a href="/">Shorten another URL</a></p>
</main>
"""
        return self._page("Short link created", content)

    def _table_page(self) -> str:
        table = self.server.shortener._url_to_code
        sections = []
        for bucket_index, first_node in enumerate(table.buckets):
            node_markup = []
            node = first_node
            while node is not None:
                node_markup.append(self._table_node(table, node.key, node.value))
                node = node.next
            chain = " &rarr; ".join(node_markup) if node_markup else "<em>Empty</em>"
            sections.append(
                f'<section class="bucket"><h2>Bucket {bucket_index}</h2>'
                f'<div class="chain">{chain}</div></section>'
            )

        content = (
            "<main><h1>Current hash table</h1>"
            f"<p>Capacity: {table.capacity}; entries: {table.size}; "
            f"load factor: {table.load_factor:.3f}</p>"
            f'{"".join(sections)}'
            '<p><a href="/">Back to URL shortener</a></p></main>'
        )
        return self._page("Current hash table", content)

    @staticmethod
    def _table_node(table, url: str, code: str) -> str:
        safe_url = escape(url, quote=True)
        safe_code = escape(code, quote=True)
        link_path = f"/{safe_code}"
        steps = table.hash_steps(url)
        calculations = []
        for index, (character, previous, value) in enumerate(steps, start=1):
            char = escape(repr(character), quote=True)
            calculations.append(
                f"<li><code>h{index} = (31 &times; {previous} + "
                f"ord({char}) = {ord(character)}) mod {table.capacity} = {value}"
                "</code></li>"
            )
        final_index = steps[-1][2] if steps else 0
        return (
            '<article class="node">'
            f"<p>URL key: <code>{safe_url}</code></p>"
            f"<p>Short code: <code>{safe_code}</code></p>"
            f'<p>Short link: <a href="{link_path}">{link_path}</a></p>'
            "<details><summary>Horner hash calculation</summary>"
            "<ol>"
            f'{"".join(calculations)}'
            "</ol>"
            f"<p>Final bucket index: {final_index}</p>"
            "</details></article>"
        )

    @staticmethod
    def _error_page(title: str, message: str) -> str:
        content = (
            f"<main><h1>{escape(title)}</h1>"
            f"<p>{escape(message)}</p>"
            '<p><a href="/">Back</a></p></main>'
        )
        return ShortenerRequestHandler._page(title, content)

    @staticmethod
    def _page(title: str, content: str) -> str:
        safe_title = escape(title, quote=True)
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{ font: 16px system-ui, sans-serif; margin: 2rem auto; max-width: 60rem; padding: 0 1rem; }}
    input {{ box-sizing: border-box; display: block; margin: .5rem 0 1rem; max-width: 100%; padding: .6rem; width: 36rem; }}
    button {{ padding: .6rem 1rem; }}
    .bucket {{ border-top: 1px solid #bbb; padding: .5rem 0; }}
    .chain {{ align-items: stretch; display: flex; flex-wrap: wrap; gap: .75rem; }}
    .node {{ border: 1px solid #aaa; border-radius: .4rem; max-width: 100%; overflow-wrap: anywhere; padding: .75rem; }}
    .node p {{ margin: .3rem 0; }}
    code {{ white-space: pre-wrap; }}
  </style>
</head>
<body>{content}</body>
</html>"""

    def _send_html(self, status: int, document: str) -> None:
        body = document.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    with ShortenerHTTPServer(("", args.port)) as server:
        print(f"Serving URL shortener on http://localhost:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server.")


if __name__ == "__main__":
    main()
