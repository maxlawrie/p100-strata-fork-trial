#!/usr/bin/env python3
# Reference solutions for coding_tasks_v2.py, and a check that each task's tests pass with its reference and fail with
# a broken one. Run: python3 coding_refs_v2.py   (runs the tests with this machine's python3, no container)
import subprocess, sys, tempfile, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coding_tasks_v2 import TASKS, PRELUDE

REFS = {
"b64": '''
A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
def b64encode(data):
    out = []
    for i in range(0, len(data), 3):
        c = data[i:i + 3]; n = int.from_bytes(c + b'\\0' * (3 - len(c)), 'big')
        s = ''.join(A[(n >> s) & 63] for s in (18, 12, 6, 0))
        out.append(s[:len(c) + 1] + '=' * (3 - len(c)))
    return ''.join(out)
def b64decode(s):
    if len(s) % 4: raise ValueError('length')
    out = bytearray()
    for i in range(0, len(s), 4):
        q = s[i:i + 4]; pad = len(q) - len(q.rstrip('='))
        if pad > 2 or (pad and i + 4 != len(s)): raise ValueError('padding')
        n = 0
        for ch in q[:4 - pad]:
            k = A.find(ch)
            if k < 0: raise ValueError('char')
            n = n << 6 | k
        n <<= 6 * pad
        out += n.to_bytes(3, 'big')[:3 - pad]
    return bytes(out)
''',
"glob_match": '''
def glob_match(pattern, name):
    toks, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if c == '*': toks.append(('*',)); i += 1
        elif c == '?': toks.append(('?',)); i += 1
        elif c == '[':
            j = i + 1
            neg = j < len(pattern) and pattern[j] == '!'
            if neg: j += 1
            k = j
            if k < len(pattern) and pattern[k] == ']': k += 1
            while k < len(pattern) and pattern[k] != ']': k += 1
            if k >= len(pattern): toks.append(('c', '[')); i += 1; continue
            body, members, m = pattern[j:k], set(), 0
            while m < len(body):
                if m + 2 < len(body) and body[m + 1] == '-':
                    members.update(chr(x) for x in range(ord(body[m]), ord(body[m + 2]) + 1)); m += 3
                else: members.add(body[m]); m += 1
            toks.append(('s', members, neg)); i = k + 1
        else: toks.append(('c', c)); i += 1
    def one(t, ch):
        if t[0] == '?': return True
        if t[0] == 'c': return t[1] == ch
        return (ch in t[1]) != t[2]
    ti = ni = 0; star = -1; mark = 0
    while ni < len(name):
        if ti < len(toks) and toks[ti][0] != '*' and one(toks[ti], name[ni]): ti += 1; ni += 1
        elif ti < len(toks) and toks[ti][0] == '*': star = ti; mark = ni; ti += 1
        elif star >= 0: ti = star + 1; mark += 1; ni = mark
        else: return False
    while ti < len(toks) and toks[ti][0] == '*': ti += 1
    return ti == len(toks)
''',
"fraction_to_decimal": '''
def fraction_to_decimal(n, d):
    if n == 0: return '0'
    s = '-' if (n < 0) != (d < 0) else ''
    n, d = abs(n), abs(d)
    q, r = divmod(n, d)
    if r == 0: return s + str(q)
    digits, seen = [], {}
    while r and r not in seen:
        seen[r] = len(digits); r *= 10; digits.append(str(r // d)); r %= d
    if r:
        i = seen[r]; return s + str(q) + '.' + ''.join(digits[:i]) + '(' + ''.join(digits[i:]) + ')'
    return s + str(q) + '.' + ''.join(digits)
''',
"knapsack_pick": '''
def knapsack_pick(items, capacity):
    n = len(items)
    best = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        w, v = items[i]
        for c in range(capacity + 1):
            best[i][c] = best[i + 1][c]
            if w <= c and best[i + 1][c - w] + v > best[i][c]: best[i][c] = best[i + 1][c - w] + v
    out, c = [], capacity
    for i in range(n):
        if best[i][c] == 0: break
        w, v = items[i]
        if w <= c and best[i + 1][c - w] + v == best[i][c]: out.append(i); c -= w
    return best[0][capacity], out
''',
"kth_permutation": '''
import math
from collections import Counter
def kth_permutation(s, k):
    cnt = Counter(s); n = len(s)
    def ways(m):
        w = math.factorial(m)
        for v in cnt.values(): w //= math.factorial(v)
        return w
    if k < 0 or k >= ways(n): raise IndexError(k)
    out = []
    for pos in range(n):
        for ch in sorted(cnt):
            if not cnt[ch]: continue
            cnt[ch] -= 1
            w = ways(n - pos - 1)
            if k < w: out.append(ch); break
            k -= w; cnt[ch] += 1
    return ''.join(out)
''',
"text_justify": '''
def text_justify(words, width):
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
''',
"add_days": '''
def add_days(date, n):
    y, m, d = int(date[:4]), int(date[5:7]), int(date[8:10])
    def leap(y): return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    ml = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    def to_ord(y, m, d):
        y1 = y - 1
        o = y1 * 365 + y1 // 4 - y1 // 100 + y1 // 400
        for i in range(m - 1): o += ml[i] + (i == 1 and leap(y))
        return o + d
    o = to_ord(y, m, d) + n
    y = max(1, (o - 1) // 366)
    while to_ord(y + 1, 1, 1) <= o: y += 1
    m = 1
    while True:
        dim = ml[m - 1] + (m == 2 and leap(y))
        if to_ord(y, m, 1) + dim > o: break
        m += 1
    d = o - to_ord(y, m, 1) + 1
    names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return '%04d-%02d-%02d' % (y, m, d), names[(o - 1) % 7]
''',
"crc32": '''
T = []
for i in range(256):
    c = i
    for _ in range(8): c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
    T.append(c)
def crc32(data, value=0):
    c = value ^ 0xFFFFFFFF
    for b in data: c = T[(c ^ b) & 255] ^ (c >> 8)
    return c ^ 0xFFFFFFFF
''',
"weighted_intervals": '''
import bisect
def weighted_intervals(jobs):
    order = sorted(range(len(jobs)), key=lambda i: jobs[i][1])
    ends = [jobs[i][1] for i in order]
    best, take = [0], []
    for n, i in enumerate(order):
        s, e, w = jobs[i]
        k = bisect.bisect_right(ends, s, 0, n)
        if best[k] + w > best[n]: best.append(best[k] + w); take.append(k)
        else: best.append(best[n]); take.append(-1)
    out, n = [], len(order)
    while n > 0:
        if take[n - 1] >= 0: out.append(order[n - 1]); n = take[n - 1]
        else: n -= 1
    return best[-1], sorted(out)
''',
"normpath": '''
def normpath(path):
    if not path: return '.'
    lead = 0
    if path.startswith('/'): lead = 2 if path.startswith('//') and not path.startswith('///') else 1
    out = []
    for c in path.split('/'):
        if c in ('', '.'): continue
        if c != '..' or (not lead and not out) or (out and out[-1] == '..'): out.append(c)
        elif out: out.pop()
    return '/' * lead + '/'.join(out) or '.'
''',
"min_window": '''
from collections import Counter
def min_window(s, t):
    if not t: return ''
    need = Counter(t); missing = len(t); best = None; i = 0
    for j, ch in enumerate(s):
        if need[ch] > 0: missing -= 1
        need[ch] -= 1
        if missing == 0:
            while need[s[i]] < 0: need[s[i]] += 1; i += 1
            if best is None or j - i < best[1] - best[0]: best = (i, j)
            need[s[i]] += 1; missing += 1; i += 1
    return '' if best is None else s[best[0]:best[1] + 1]
''',
"int_to_words": '''
O = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
T = '_ _ twenty thirty forty fifty sixty seventy eighty ninety'.split()
def _sub(n):
    out = []
    if n >= 100: out.append(O[n // 100] + ' hundred'); n %= 100
    if n >= 20: out.append(T[n // 10] + ('-' + O[n % 10] if n % 10 else ''))
    elif n or not out: out.append(O[n])
    return ' '.join(out)
def int_to_words(n):
    if n == 0: return 'zero'
    if n < 0: return 'minus ' + int_to_words(-n)
    out = []
    for scale, word in [(10**9, ' billion'), (10**6, ' million'), (10**3, ' thousand'), (1, '')]:
        q, n = divmod(n, scale)
        if q: out.append(_sub(q) + word)
    return ' '.join(out)
''',
"big_mul": '''
def big_mul(a, b):
    B = 10**9
    def limbs(s): return [int(s[max(0, i - 9):i]) for i in range(len(s), 0, -9)]
    x, y = limbs(a), limbs(b)
    r = [0] * (len(x) + len(y) + 1)
    for i, xi in enumerate(x):
        carry = 0
        for j, yj in enumerate(y):
            cur = r[i + j] + xi * yj + carry
            carry, r[i + j] = divmod(cur, B)
        k = i + len(y)
        while carry:
            cur = r[k] + carry; carry, r[k] = divmod(cur, B); k += 1
    while len(r) > 1 and r[-1] == 0: r.pop()
    return str(r[-1]) + ''.join('%09d' % v for v in reversed(r[:-1]))
''',
}

def run(code, tests):
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "t.py"), "w").write(code + "\n\n" + PRELUDE + "\n" + tests)
        r = subprocess.run([sys.executable, "-I", os.path.join(d, "t.py")], capture_output=True, text=True, timeout=120)
    return r.returncode == 0, ((r.stderr or r.stdout).strip().splitlines() or [""])[-1][:150]

if __name__ == "__main__":
    bad = 0
    for t in TASKS:
        ok, why = run(REFS[t["name"]], t["tests"])
        # a deliberately wrong solution: every function returns None
        import re
        stub = "\n".join("def %s(*a, **k): return None" % f for f in re.findall(r"^def (\w+)", REFS[t["name"]], re.M) if not f.startswith("_"))
        ok2, _ = run(stub, t["tests"])
        print("%-20s reference %s   stub %s   %s" % (t["name"], "PASS" if ok else "FAIL", "rejected" if not ok2 else "ACCEPTED", why if not ok else ""))
        bad += (not ok) or ok2
    sys.exit(1 if bad else 0)
