# Small coding tasks with unit tests, for comparing models (bench/bench.sh).
# Each task: a prompt asking for one Python function/class, and asserts run against the model's code.
TASKS = [
    {
        "name": "parse_duration",
        "prompt": "Write a Python function parse_duration(s: str) -> int that converts strings like '1h30m15s', "
                  "'45s', '2h', '90m' into total seconds. Units are h, m, s, each at most once, in that order. "
                  "Raise ValueError for an empty string or anything malformed (e.g. '1x', 'h', '10', '1s1h').",
        "tests": """
assert parse_duration('1h30m15s') == 5415
assert parse_duration('45s') == 45
assert parse_duration('2h') == 7200
assert parse_duration('90m') == 5400
for bad in ['', '1x', 'h', '10', '1s1h', '1h1h']:
    try:
        parse_duration(bad); raise SystemExit('no ValueError for %r' % bad)
    except ValueError:
        pass
""",
    },
    {
        "name": "merge_intervals",
        "prompt": "Write a Python function merge_intervals(intervals: list[list[int]]) -> list[list[int]] that merges "
                  "overlapping or touching closed intervals and returns them sorted by start. The input may be unsorted "
                  "and empty. Do not modify the input list.",
        "tests": """
x = [[8, 10], [1, 3], [2, 6], [15, 18]]
assert merge_intervals(x) == [[1, 6], [8, 10], [15, 18]]
assert x == [[8, 10], [1, 3], [2, 6], [15, 18]]
assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]
assert merge_intervals([]) == []
assert merge_intervals([[1, 10], [2, 3], [4, 5]]) == [[1, 10]]
""",
    },
    {
        "name": "lru_cache",
        "prompt": "Write a Python class LRUCache with __init__(self, capacity: int), get(self, key) -> value or -1 if "
                  "missing, and put(self, key, value). Both must be O(1). When over capacity, evict the least recently "
                  "used key; get and put both count as use. Do not use functools.",
        "tests": """
c = LRUCache(2)
c.put(1, 1); c.put(2, 2)
assert c.get(1) == 1
c.put(3, 3)
assert c.get(2) == -1
c.put(4, 4)
assert c.get(1) == -1 and c.get(3) == 3 and c.get(4) == 4
c.put(3, 30); c.put(5, 5)
assert c.get(4) == -1 and c.get(3) == 30
""",
    },
    {
        "name": "roman",
        "prompt": "Write two Python functions: int_to_roman(n: int) -> str for 1..3999, and roman_to_int(s: str) -> int "
                  "for valid standard Roman numerals (subtractive notation, e.g. 'MCMXCIV' = 1994).",
        "tests": """
assert int_to_roman(1994) == 'MCMXCIV' and int_to_roman(3999) == 'MMMCMXCIX' and int_to_roman(4) == 'IV'
assert roman_to_int('MCMXCIV') == 1994 and roman_to_int('LVIII') == 58
assert all(roman_to_int(int_to_roman(i)) == i for i in range(1, 4000))
""",
    },
    {
        "name": "toposort",
        "prompt": "Write a Python function toposort(deps: dict[str, list[str]]) -> list[str]. deps maps each node to "
                  "the nodes it depends on; dependencies may not appear as keys. Return all nodes so each comes after "
                  "everything it depends on; break ties alphabetically. Raise ValueError if there is a cycle.",
        "tests": """
assert toposort({'b': ['a'], 'c': ['a', 'b'], 'd': []}) == ['a', 'b', 'c', 'd']
assert toposort({'x': ['z', 'y']}) == ['y', 'z', 'x']
assert toposort({}) == []
try:
    toposort({'a': ['b'], 'b': ['c'], 'c': ['a']}); raise SystemExit('no ValueError for cycle')
except ValueError:
    pass
""",
    },
    {
        "name": "fix_bisect",
        "prompt": "This function should return the index of the FIRST occurrence of target in the sorted list a, or "
                  "-1 if absent, in O(log n). It has bugs. Return the corrected function, same name and signature.\n\n"
                  "def first_index(a, target):\n    lo, hi = 0, len(a)\n    while lo < hi:\n        mid = (lo + hi) // 2\n"
                  "        if a[mid] < target:\n            lo = mid\n        else:\n            hi = mid - 1\n"
                  "    return lo if a[lo] == target else -1",
        "tests": """
assert first_index([1, 2, 2, 2, 3], 2) == 1
assert first_index([1, 2, 3], 4) == -1
assert first_index([], 1) == -1
assert first_index([5, 5, 5], 5) == 0
assert first_index([1, 3, 5], 0) == -1
import random
for _ in range(300):
    a = sorted(random.randint(0, 9) for _ in range(random.randint(0, 12))); t = random.randint(-1, 10)
    assert first_index(a, t) == (a.index(t) if t in a else -1), (a, t)
""",
    },
    {
        "name": "calc",
        "prompt": "Write a Python function calc(expr: str) -> float that evaluates arithmetic with + - * / , "
                  "parentheses, unary minus, decimal numbers and arbitrary spaces, with normal precedence and left "
                  "associativity. Do not use eval, exec, ast or compile. Raise ValueError on malformed input.",
        "tests": """
assert calc('1 + 2 * 3') == 7
assert calc('(1 + 2) * 3') == 9
assert calc('8 / 4 / 2') == 1
assert calc('10 - 4 - 3') == 3
assert calc('-(2 + 3) * -2') == 10
assert abs(calc('3.5 * 2 - .5') - 6.5) < 1e-9
for bad in ['1 +', '(1 + 2', '2 * * 3', '']:
    try:
        calc(bad); raise SystemExit('no ValueError for %r' % bad)
    except ValueError:
        pass
""",
    },
    {
        "name": "wrap",
        "prompt": "Write a Python function wrap(text: str, width: int) -> list[str] that greedily word-wraps text into "
                  "lines of at most width characters. Words are separated by any whitespace, which collapses to single "
                  "spaces. A word longer than width is split into width-sized pieces. Do not use textwrap.",
        "tests": """
assert wrap('the quick brown fox', 10) == ['the quick', 'brown fox']
assert wrap('  a   b  ', 3) == ['a b']
assert wrap('abcdefghij', 4) == ['abcd', 'efgh', 'ij']
assert wrap('', 5) == []
assert wrap('aa bbbbbbb', 3) == ['aa', 'bbb', 'bbb', 'b']
""",
    },
]
