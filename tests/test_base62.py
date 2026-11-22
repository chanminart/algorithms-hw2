import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_zero(self):
        self.assertEqual(encode(0), "0")

    def test_alphabet_order(self):
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")

    def test_round_trip(self):
        for value in (1, 10, 35, 36, 61, 62, 3843, 10**30):
            with self.subTest(value=value):
                self.assertEqual(decode(encode(value)), value)

    def test_decode_zero(self):
        self.assertEqual(decode("0"), 0)

    def test_encode_rejects_non_integer_and_negative_values(self):
        for value in (True, 1.5, "1"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    encode(value)
        with self.assertRaises(ValueError):
            encode(-1)

    def test_decode_rejects_non_string_empty_and_invalid_values(self):
        with self.assertRaises(TypeError):
            decode(1)
        for value in ("", "a!"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decode(value)


if __name__ == "__main__":
    unittest.main()
