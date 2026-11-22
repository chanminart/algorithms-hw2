import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_max_load_none_disables_resizing(self):
        table = HashTable(capacity=4, max_load=None)

        for key in ("a", "b", "c", "d", "e"):
            table.put(key, key)

        self.assertEqual(table.capacity, 4)
        self.assertEqual(table.size, 5)

    def test_default_max_load_preserves_automatic_resizing(self):
        table = HashTable(capacity=4)

        for key in ("a", "b", "c", "d"):
            table.put(key, key)

        self.assertEqual(table.capacity, 8)
        self.assertEqual(table.size, 4)


if __name__ == "__main__":
    unittest.main()
