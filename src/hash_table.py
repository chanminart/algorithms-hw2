"""A string-keyed hash table using separate chaining and Horner hashing."""

from collections.abc import Iterator
from typing import Generic, TypeVar

V = TypeVar("V")


class _Node(Generic[V]):
    __slots__ = ("key", "value", "next")

    def __init__(self, key: str, value: V, next_node: "_Node[V] | None" = None):
        self.key = key
        self.value = value
        self.next = next_node


class HashTable(Generic[V]):
    """Store values by string key, with optional automatic resizing."""

    def __init__(self, capacity: int = 8, *, auto_resize: bool = True):
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if not isinstance(auto_resize, bool):
            raise TypeError("auto_resize must be a bool")

        self.capacity = capacity
        self.auto_resize = auto_resize
        self.size = 0
        self.buckets: list[_Node[V] | None] = [None] * capacity

    @property
    def load_factor(self) -> float:
        return self.size / self.capacity

    def hash_steps(self, key: str) -> tuple[tuple[str, int, int], ...]:
        """Return (character, prior hash, updated hash) for each key character."""
        self._validate_key(key)
        current = 0
        steps = []
        for character in key:
            previous = current
            current = (31 * current + ord(character)) % self.capacity
            steps.append((character, previous, current))
        return tuple(steps)

    def hash_key(self, key: str) -> int:
        """Return the bucket index produced by the specified Horner hash."""
        steps = self.hash_steps(key)
        return steps[-1][2] if steps else 0

    def search(self, key: str) -> tuple[bool, V | None, int]:
        """Return whether a key exists, its value, and nodes compared."""
        node, comparisons = self._find_node(key)
        if node is None:
            return False, None, comparisons
        return True, node.value, comparisons

    def get(self, key: str) -> V:
        """Return a value, raising KeyError when the key is absent."""
        node, _ = self._find_node(key)
        if node is None:
            raise KeyError(key)
        return node.value

    def put(self, key: str, value: V) -> None:
        """Insert or replace a value for a string key."""
        self._validate_key(key)
        index = self.hash_key(key)
        node = self.buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self.buckets[index] = _Node(key, value, self.buckets[index])
        self.size += 1
        if self.auto_resize and self.load_factor > 0.75:
            self._resize()

    def items(self) -> Iterator[tuple[str, V]]:
        """Iterate over key/value pairs in bucket and chain order."""
        for node in self.buckets:
            while node is not None:
                yield node.key, node.value
                node = node.next

    def _find_node(self, key: str) -> tuple[_Node[V] | None, int]:
        self._validate_key(key)
        node = self.buckets[self.hash_key(key)]
        comparisons = 0
        while node is not None:
            comparisons += 1
            if node.key == key:
                return node, comparisons
            node = node.next
        return None, comparisons

    def _resize(self) -> None:
        old_buckets = self.buckets
        self.capacity *= 2
        self.buckets = [None] * self.capacity
        for old_node in old_buckets:
            node = old_node
            while node is not None:
                next_node = node.next
                index = self.hash_key(node.key)
                node.next = self.buckets[index]
                self.buckets[index] = node
                node = next_node

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")
