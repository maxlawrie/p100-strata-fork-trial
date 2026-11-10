# More coding tasks for the repeated quality benchmark (bench/quality.py): 13 tasks checked against the stdlib, a
# brute-force search or a reference written out in the tests, on random inputs. Used together with the 8 tasks of
# coding_tasks_hard.py (same PRELUDE: forbid()/allow() and a seeded random). Reference solutions that pass every test
# are in coding_refs_v2.py; `python3 coding_refs_v2.py` checks tests against them.
from coding_tasks_hard import PRELUDE  # noqa: F401

TASKS = [
    {
        "name": "b64",
        "prompt": "Write two Python functions, b64encode(data: bytes) -> str and b64decode(s: str) -> bytes, implementing "
                  "standard Base64 (RFC 4648, alphabet A-Z a-z 0-9 + /, with '=' padding) without using the base64 or "
                  "binascii modules. b64decode must raise ValueError if the input length is not a multiple of 4 or it "
                  "contains a character outside the alphabet (other than valid trailing padding).",
        "tests": """
import base64
data = [bytes(random.randrange(256) for _ in range(random.randint(0, 40))) for _ in range(300)]
want = [base64.b64encode(d).decode() for d in data]
forbid('base64', 'binascii')
got = [b64encode(d) for d in data]
back = [b64decode(w) for w in want]
errs = []
for b in ['abc', 'ab!d', 'abcde', 'a b=']:
    try: b64decode(b); errs.append(b)
    except ValueError: pass
allow()
for d, g, w, bk in zip(data, got, want, back):
    assert g == w, (d, g, w)
    assert bytes(bk) == d, (w, bk, d)
assert not errs, 'accepted invalid: %r' % errs
""",
    },
    {
        "name": "glob_match",
        "prompt": "Write a Python function glob_match(pattern: str, name: str) -> bool for shell-style patterns, without "
                  "using the fnmatch, glob or re modules. '*' matches any sequence of characters (including none), '?' "
                  "matches exactly one character, '[seq]' matches one character that is in seq, where seq may contain "
                  "ranges such as a-c, and '[!seq]' matches one character that is not in seq. A ']' directly after '[' "
                  "or '[!' is a literal member of the set. Everything else matches itself. The pattern must match the "
                  "whole name, and matching is case-sensitive. Patterns can contain many '*', so avoid exponential time.",
        "tests": """
import fnmatch
parts = ['a', 'b', 'c', '*', '?', '[ab]', '[a-c]', '[!a]', '[!b-c]', '[]a]', '[!]b]', '**', 'ab']
cases = []
for _ in range(3000):
    p = ''.join(random.choice(parts) for _ in range(random.randint(0, 6)))
    n = ''.join(random.choice('abc]') for _ in range(random.randint(0, 7)))
    cases.append((p, n, fnmatch.fnmatchcase(n, p)))
cases += [('', '', True), ('*', '', True), ('?', '', False), ('a*b*c', 'aXbXc', True), ('A', 'a', False)]
forbid('fnmatch', 'glob', 're')
got = [glob_match(p, n) for p, n, _ in cases]
slow = glob_match('*a' * 14 + 'b', 'a' * 40)
allow()
for (p, n, w), g in zip(cases, got):
    assert bool(g) == w, (p, n, g, w)
assert slow is False or slow == False
""",
    },
    {
        "name": "fraction_to_decimal",
        "prompt": "Write a Python function fraction_to_decimal(n: int, d: int) -> str returning the exact decimal expansion "
                  "of n/d (d is never 0), with any repeating part in parentheses. Examples: (1, 2) -> '0.5', (1, 3) -> "
                  "'0.(3)', (1, 6) -> '0.1(6)', (2, 1) -> '2', (-1, 3) -> '-0.(3)', (22, 7) -> '3.(142857)', (0, -5) -> "
                  "'0', (-50, -8) -> '6.25'. No leading '+', no '-0', no trailing '.'.",
        "tests": """
def ref(n, d):
    if n == 0: return '0'
    s = '-' if (n < 0) != (d < 0) else ''
    n, d = abs(n), abs(d)
    q, r = divmod(n, d)
    if r == 0: return s + str(q)
    digits, seen = [], {}
    while r and r not in seen:
        seen[r] = len(digits)
        r *= 10
        digits.append(str(r // d)); r %= d
    if r:
        i = seen[r]
        return s + str(q) + '.' + ''.join(digits[:i]) + '(' + ''.join(digits[i:]) + ')'
    return s + str(q) + '.' + ''.join(digits)
for a, b, w in [(1, 2, '0.5'), (1, 3, '0.(3)'), (1, 6, '0.1(6)'), (2, 1, '2'), (-1, 3, '-0.(3)'), (22, 7, '3.(142857)'),
                (0, -5, '0'), (-50, -8, '6.25'), (1, 97, ref(1, 97)), (7, -12, '-0.58(3)'), (10**12, 3, '333333333333.(3)')]:
    assert fraction_to_decimal(a, b) == w, (a, b, fraction_to_decimal(a, b), w)
for _ in range(3000):
    a = random.randint(-500, 500); b = random.choice([-1, 1]) * random.randint(1, 400)
    assert fraction_to_decimal(a, b) == ref(a, b), (a, b, fraction_to_decimal(a, b), ref(a, b))
""",
    },
    {
        "name": "knapsack_pick",
        "prompt": "Write a Python function knapsack_pick(items: list[tuple[int, int]], capacity: int) -> tuple[int, list[int]] "
                  "for the 0/1 knapsack problem. Each item is (weight, value) with weight >= 0 and value >= 0; each item "
                  "can be used at most once and the total weight must not exceed capacity. Return (best_value, indices) "
                  "where indices is the sorted list of chosen item indices. Among all subsets that reach the best value, "
                  "return the one whose sorted index list is lexicographically smallest (compared as Python lists).",
        "tests": """
import itertools
def ref(items, cap):
    best = (0, [])
    for r in range(len(items) + 1):
        for c in itertools.combinations(range(len(items)), r):
            if sum(items[i][0] for i in c) <= cap:
                v = sum(items[i][1] for i in c)
                if v > best[0] or (v == best[0] and list(c) < best[1]): best = (v, list(c))
    return best
assert tuple(knapsack_pick([], 5)) == (0, [])
for _ in range(400):
    items = [(random.randint(0, 9), random.randint(0, 9)) for _ in range(random.randint(0, 10))]
    cap = random.randint(0, 25)
    g = knapsack_pick(items, cap); w = ref(items, cap)
    assert g[0] == w[0] and list(g[1]) == w[1], (items, cap, g, w)
big = [(random.randint(1, 50), random.randint(1, 99)) for _ in range(120)]
v, idx = knapsack_pick(big, 500)
assert sum(big[i][0] for i in idx) <= 500 and sum(big[i][1] for i in idx) == v and list(idx) == sorted(set(idx))
best = [0] * 501
for w, val in big:
    for c in range(500, w - 1, -1): best[c] = max(best[c], best[c - w] + val)
assert v == best[500], (v, best[500])
""",
    },
    {
        "name": "kth_permutation",
        "prompt": "Write a Python function kth_permutation(s: str, k: int) -> str returning the k-th (0-based) permutation, "
                  "in lexicographic order, of the DISTINCT permutations of the characters of s (s may contain repeated "
                  "characters). Raise IndexError if k is negative or not less than the number of distinct permutations. "
                  "It must be fast for strings of 25 characters, so do not enumerate the permutations.",
        "tests": """
import itertools, math
from collections import Counter
def ref(s, k):
    cnt = Counter(s); n = len(s)
    def ways(c, m):
        w = math.factorial(m)
        for v in c.values(): w //= math.factorial(v)
        return w
    if k < 0 or k >= ways(cnt, n): raise IndexError
    out = []
    for pos in range(n):
        for ch in sorted(cnt):
            if not cnt[ch]: continue
            cnt[ch] -= 1
            w = ways(cnt, n - pos - 1)
            if k < w: out.append(ch); break
            k -= w; cnt[ch] += 1
    return ''.join(out)
for s in ['', 'a', 'ab', 'aab', 'abca', 'bbaac', 'zzzz', 'dcba', 'aabbc', 'abcabc']:
    allp = sorted(set(''.join(p) for p in itertools.permutations(s)))
    for k, w in enumerate(allp):
        assert kth_permutation(s, k) == w, (s, k, kth_permutation(s, k), w)
    for bad in (-1, len(allp)):
        try: kth_permutation(s, bad); raise AssertionError('no IndexError for %r, %d' % (s, bad))
        except IndexError: pass
for _ in range(50):
    s = ''.join(random.choice('abcdefgh') for _ in range(25))
    total = math.factorial(25)
    for v in Counter(s).values(): total //= math.factorial(v)
    k = random.randrange(total)
    assert kth_permutation(s, k) == ref(s, k), (s, k)
""",
    },
    {
        "name": "text_justify",
        "prompt": "Write a Python function text_justify(words: list[str], width: int) -> list[str] that formats the words "
                  "into fully justified lines of exactly `width` characters. Pack as many words as fit on each line "
                  "(greedy, words separated by at least one space). Distribute extra spaces between words as evenly as "
                  "possible; if they don't divide evenly, the gaps on the left get more spaces than the gaps on the "
                  "right. A line with a single word, and the last line, are left-justified and padded with spaces on "
                  "the right (single spaces between words on the last line). Every word is non-empty and no longer "
                  "than width. An empty word list gives an empty list.",
        "tests": """
def ref(words, width):
    out, line, n = [], [], 0
    for w in words:
        if line and n + len(w) + len(line) > width:
            gaps = len(line) - 1; spare = width - n
            if gaps == 0: out.append(line[0].ljust(width))
            else:
                q, r = divmod(spare, gaps)
                out.append(''.join(x + ' ' * (q + (i < r)) for i, x in enumerate(line[:-1])) + line[-1])
            line, n = [], 0
        line.append(w); n += len(w)
    if line: out.append(' '.join(line).ljust(width))
    return out
assert text_justify(['This', 'is', 'an', 'example', 'of', 'text', 'justification.'], 16) == \\
    ['This    is    an', 'example  of text', 'justification.  ']
assert text_justify([], 5) == []
for _ in range(1500):
    width = random.randint(1, 20)
    words = [''.join(random.choice('ab') for _ in range(random.randint(1, min(width, 7)))) for _ in range(random.randint(0, 12))]
    g = text_justify(words, width); w = ref(words, width)
    assert g == w, (words, width, g, w)
""",
    },
    {
        "name": "add_days",
        "prompt": "Write a Python function add_days(date: str, n: int) -> tuple[str, str] without using the datetime "
                  "or calendar modules. `date` is 'YYYY-MM-DD' in the proleptic Gregorian calendar (years 0001 to "
                  "9999) and n is a possibly negative number of days. Return (new_date, weekday) where new_date is "
                  "'YYYY-MM-DD' (zero-padded, 4-digit year) and weekday is the English name of that day ('Monday' ... "
                  "'Sunday'). The result always stays within years 0001 to 9999.",
        "tests": """
import datetime as dt
names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
cases = [('2024-02-28', 1), ('2024-02-28', 2), ('1900-02-28', 1), ('2000-02-28', 1), ('0001-01-01', 0),
         ('9999-12-31', 0), ('2026-11-10', -1000000 // 3), ('2023-12-31', 1), ('2024-03-01', -1), ('0001-01-01', 3652058)]
for _ in range(3000):
    d = dt.date.fromordinal(random.randint(1, dt.date.max.toordinal()))
    lo, hi = 1 - d.toordinal(), dt.date.max.toordinal() - d.toordinal()
    if random.random() < 0.7: lo, hi = max(lo, -800), min(hi, 800)
    n = random.randint(lo, hi)
    cases.append((d.isoformat(), n))
want = []
for s, n in cases:
    r = dt.date.fromisoformat(s) + dt.timedelta(days=n)
    want.append(('%04d-%02d-%02d' % (r.year, r.month, r.day), names[r.weekday()]))
forbid('datetime', 'calendar')
got = [add_days(s, n) for s, n in cases]
allow()
for c, g, w in zip(cases, got, want):
    assert tuple(g) == w, (c, g, w)
""",
    },
    {
        "name": "crc32",
        "prompt": "Write a Python function crc32(data: bytes, value: int = 0) -> int computing the standard CRC-32 used by "
                  "zip, gzip and PNG (reflected polynomial 0xEDB88320, initial value and final XOR 0xFFFFFFFF), without "
                  "using the zlib or binascii modules. `value` is the CRC of the data seen so far, so that "
                  "crc32(b, crc32(a)) == crc32(a + b). The result is an unsigned 32-bit integer.",
        "tests": """
import zlib
data = [bytes(random.randrange(256) for _ in range(random.randint(0, 200))) for _ in range(200)]
data += [b'', b'123456789', bytes(100000)]
want = [zlib.crc32(d) for d in data]
forbid('zlib', 'binascii')
got = [crc32(d) for d in data]
chained = [crc32(d[len(d) // 2:], crc32(d[:len(d) // 2])) for d in data]
allow()
assert crc32(b'123456789') == 0xCBF43926
for d, g, c, w in zip(data, got, chained, want):
    assert g == w and c == w, (d[:20], g, c, w)
""",
    },
    {
        "name": "weighted_intervals",
        "prompt": "Write a Python function weighted_intervals(jobs: list[tuple[int, int, int]]) -> tuple[int, list[int]]. "
                  "Each job is (start, end, weight) with start < end and weight > 0, occupying the half-open interval "
                  "[start, end), so a job may start exactly when another ends. Return (best_total, indices): the "
                  "maximum total weight of a set of jobs no two of which overlap, and the sorted list of the indices of "
                  "one such set. It must handle 20,000 jobs quickly.",
        "tests": """
import itertools
def ok(jobs, idx):
    sel = sorted(jobs[i][:2] for i in idx)
    return all(a[1] <= b[0] for a, b in zip(sel, sel[1:])) and list(idx) == sorted(set(idx))
def brute(jobs):
    best = 0
    for r in range(len(jobs) + 1):
        for c in itertools.combinations(range(len(jobs)), r):
            if ok(jobs, list(c)): best = max(best, sum(jobs[i][2] for i in c))
    return best
assert tuple(weighted_intervals([])) == (0, [])
for _ in range(400):
    jobs = []
    for _ in range(random.randint(0, 9)):
        s = random.randint(0, 12); jobs.append((s, s + random.randint(1, 5), random.randint(1, 9)))
    v, idx = weighted_intervals(jobs)
    assert v == brute(jobs) and ok(jobs, idx) and sum(jobs[i][2] for i in idx) == v, (jobs, v, idx, brute(jobs))
jobs = []
for _ in range(20000):
    s = random.randint(0, 10**6); jobs.append((s, s + random.randint(1, 500), random.randint(1, 1000)))
v, idx = weighted_intervals(jobs)
assert ok(jobs, idx) and sum(jobs[i][2] for i in idx) == v
def dp(jobs):
    import bisect
    js = sorted(jobs, key=lambda j: j[1]); ends = [j[1] for j in js]; best = [0]
    for i, (s, e, w) in enumerate(js):
        k = bisect.bisect_right(ends, s, 0, i)
        best.append(max(best[-1], best[k] + w))
    return best[-1]
assert v == dp(jobs), (v, dp(jobs))
""",
    },
    {
        "name": "normpath",
        "prompt": "Write a Python function normpath(path: str) -> str that normalises a POSIX path exactly like "
                  "posixpath.normpath, but without using os, os.path, posixpath or pathlib: collapse repeated slashes "
                  "and '.' components, resolve '..' against the preceding component (at the root, '..' is dropped; in a "
                  "relative path leading '..' components are kept), remove any trailing slash, return '.' for an empty "
                  "result, and keep exactly two leading slashes if the path starts with exactly two (three or more "
                  "become one).",
        "tests": """
import os, posixpath, pathlib
fixed = [('', '.'), ('/', '/'), ('//', '//'), ('///', '/'), ('a/..', '.'), ('../a/..', '..'), ('/..', '/'),
         ('//a/../..', '//'), ('a//b/./c/', 'a/b/c'), ('./../..', '../..')]
parts = ['a', 'b', '..', '.', '', 'c.d', '...', '..a']
paths = [p for p, _ in fixed] + [random.choice(['', '/', '//', '///']) + '/'.join(random.choice(parts) for _ in range(random.randint(0, 7))) for _ in range(4000)]
want = [posixpath.normpath(p) for p in paths]
assert want[:len(fixed)] == [w for _, w in fixed]
def _no(*a, **k): raise RuntimeError('normpath/abspath/realpath/resolve are forbidden')
_keep = posixpath.normpath, posixpath.abspath, posixpath.realpath, pathlib.Path.resolve
posixpath.normpath = posixpath.abspath = posixpath.realpath = pathlib.Path.resolve = _no
got = [normpath(p) for p in paths]
posixpath.normpath, posixpath.abspath, posixpath.realpath, pathlib.Path.resolve = _keep
for p, g, w in zip(paths, got, want):
    assert g == w, (p, g, w)
""",
    },
    {
        "name": "min_window",
        "prompt": "Write a Python function min_window(s: str, t: str) -> str returning the shortest substring of s that "
                  "contains every character of t, counting repeats (if t has two 'a's the substring needs two). If "
                  "several substrings have that minimum length, return the leftmost. Return '' if there is none or if "
                  "t is empty. It must run in roughly linear time: s can have 200,000 characters.",
        "tests": """
from collections import Counter
def brute(s, t):
    if not t: return ''
    need = Counter(t); best = ''
    for i in range(len(s)):
        for j in range(i + len(t), len(s) + 1):
            if best and j - i >= len(best): break
            if not need - Counter(s[i:j]): best = s[i:j]; break
    return best
assert min_window('ADOBECODEBANC', 'ABC') == 'BANC' and min_window('a', 'aa') == '' and min_window('abc', '') == ''
for _ in range(1500):
    s = ''.join(random.choice('abc') for _ in range(random.randint(0, 14)))
    t = ''.join(random.choice('abcd' if random.random() < 0.1 else 'abc') for _ in range(random.randint(0, 5)))
    assert min_window(s, t) == brute(s, t), (s, t, min_window(s, t), brute(s, t))
s = ''.join(random.choice('abcdefghij') for _ in range(200000)) + 'xyz'
w = min_window(s, 'zyx')
assert w == 'xyz', w[:20]
w = min_window('a' * 100000 + 'b' + 'a' * 100000, 'b' + 'a' * 150000)
assert w == 'a' * 100000 + 'b' + 'a' * 50000, len(w)
""",
    },
    {
        "name": "int_to_words",
        "prompt": "Write a Python function int_to_words(n: int) -> str that spells out an integer in English, for "
                  "-999,999,999,999 <= n <= 999,999,999,999. Use lowercase, hyphens for 21-99 ('twenty-one'), no 'and', "
                  "no commas, single spaces, scale words thousand, million, billion, and 'minus ' before negative "
                  "numbers. Examples: 0 -> 'zero', 13 -> 'thirteen', 101 -> 'one hundred one', 1234 -> 'one thousand two "
                  "hundred thirty-four', -1000000 -> 'minus one million', 1000010 -> 'one million ten'.",
        "tests": """
ones = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
tens = '_ _ twenty thirty forty fifty sixty seventy eighty ninety'.split()
def sub(n):
    out = []
    if n >= 100: out.append(ones[n // 100] + ' hundred'); n %= 100
    if n >= 20: out.append(tens[n // 10] + ('-' + ones[n % 10] if n % 10 else ''))
    elif n or not out: out.append(ones[n])
    return ' '.join(out)
def ref(n):
    if n == 0: return 'zero'
    if n < 0: return 'minus ' + ref(-n)
    out = []
    for scale, word in [(10**9, ' billion'), (10**6, ' million'), (10**3, ' thousand'), (1, '')]:
        q, n = divmod(n, scale)
        if q: out.append(sub(q) + word)
    return ' '.join(out)
for n, w in [(0, 'zero'), (13, 'thirteen'), (101, 'one hundred one'), (1234, 'one thousand two hundred thirty-four'),
             (-1000000, 'minus one million'), (1000010, 'one million ten'), (40, 'forty'), (90, 'ninety'),
             (999999999999, ref(999999999999)), (-17, 'minus seventeen'), (800000000000, 'eight hundred billion')]:
    assert int_to_words(n) == w == ref(n), (n, int_to_words(n), w)
for n in list(range(-120, 1200)) + [random.randint(-10**12 + 1, 10**12 - 1) for _ in range(3000)] + \\
        [random.choice([1, -1]) * random.randint(0, 999) * 10 ** random.choice([3, 6, 9]) for _ in range(300)]:
    assert int_to_words(n) == ref(n), (n, int_to_words(n), ref(n))
""",
    },
    {
        "name": "big_mul",
        "prompt": "Write a Python function big_mul(a: str, b: str) -> str that multiplies two non-negative integers given as "
                  "decimal strings (no sign, no leading zeros except the number '0' itself) and returns the product as a "
                  "decimal string with no leading zeros. The inputs can have several thousand digits each. Python "
                  "refuses to convert between int and str beyond 4300 digits, and you must not change that limit, so "
                  "do the arithmetic on pieces of the strings. A 2,500-digit by 2,500-digit product must take at most "
                  "a few seconds.",
        "tests": """
import sys
assert sys.get_int_max_str_digits() == 4300
small = [(str(random.randint(0, 10**random.randint(0, 40))), str(random.randint(0, 10**random.randint(0, 40)))) for _ in range(400)]
small += [('0', '0'), ('0', '123'), ('1', '999'), ('99', '99'), ('1' + '0' * 30, '1' + '0' * 30)]
for a, b in small:
    assert big_mul(a, b) == str(int(a) * int(b)), (a, b, big_mul(a, b))
big = [(''.join(random.choice('123456789') + ''.join(random.choice('0123456789') for _ in range(n - 1))),
        ''.join(random.choice('123456789') + ''.join(random.choice('0123456789') for _ in range(m - 1))))
       for n, m in [(2500, 2500), (3000, 1), (2200, 2400)]]
got = [big_mul(a, b) for a, b in big]
assert sys.get_int_max_str_digits() == 4300, 'changed the int/str limit'
sys.set_int_max_str_digits(0)
for (a, b), g in zip(big, got):
    assert g == str(int(a) * int(b)), (len(a), len(b), g[:30])
""",
    },
]
