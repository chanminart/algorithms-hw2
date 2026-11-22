import http.client
import threading
import unittest
from urllib.parse import urlencode

from src.server import ShortenerHTTPServer


class ShortenerServerTests(unittest.TestCase):
    def setUp(self):
        self.server = ShortenerHTTPServer(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.getheaders(), response.read().decode("utf-8")
        connection.close()
        return result

    def test_home_page_has_url_form(self):
        status, _, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn('action="/shorten"', body)
        self.assertIn('name="url"', body)

    def test_shorten_and_redirect(self):
        url = "https://example.com/path?q=one"
        status, _, body = self.request(
            "POST",
            "/shorten",
            body=urlencode({"url": url}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        self.assertEqual(status, 200)
        self.assertIn('href="/0"', body)
        self.assertIn(url, body)

        status, headers, _ = self.request("GET", "/0")

        self.assertEqual(status, 302)
        self.assertIn(("Location", url), headers)

    def test_invalid_url_and_unknown_short_link_return_errors(self):
        status, _, _ = self.request(
            "POST",
            "/shorten",
            body=urlencode({"url": "/relative"}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 400)

        status, _, _ = self.request("GET", "/unknown")
        self.assertEqual(status, 404)

    def test_table_shows_chained_entry_and_horner_calculation(self):
        url = "https://example.com/a?x=1&y=2"
        self.request(
            "POST",
            "/shorten",
            body=urlencode({"url": url}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("Bucket 0", body)
        self.assertIn("URL key:", body)
        self.assertIn("Short code:", body)
        self.assertIn('href="/0"', body)
        self.assertIn("<details>", body)
        self.assertIn("Horner hash calculation", body)
        self.assertIn("Final bucket index:", body)
        self.assertIn("&amp;", body)


if __name__ == "__main__":
    unittest.main()
