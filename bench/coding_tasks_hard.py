# Harder coding tasks (CODING_SET=hard). Most are checked against the stdlib or a brute-force reference on random
# inputs. forbid() makes importing the named modules (and eval/exec) fail while the model's code runs, and fails the
# test if the model's code imported one at the top.
PRELUDE = """
import sys
_AT_START = set(sys.modules)  # what the model's code loaded; the tests' own imports come later
import builtins, random
random.seed(1234)
_real_import, _real_eval, _real_exec = builtins.__import__, builtins.eval, builtins.exec
def forbid(*mods):
    bad = [m for m in mods if m in _AT_START]
    if bad: raise SystemExit('used a forbidden module: %s' % bad)
    def imp(name, *a, **k):
        if name.split('.')[0] in mods: raise ImportError('forbidden: ' + name)
        return _real_import(name, *a, **k)
    def no(*a, **k): raise RuntimeError('eval/exec forbidden')
    builtins.__import__, builtins.eval, builtins.exec = imp, no, no
def allow():
    builtins.__import__, builtins.eval, builtins.exec = _real_import, _real_eval, _real_exec
"""

TASKS = [
    {
        "name": "semver_sort",
        "prompt": "Write a Python function semver_sort(versions: list[str]) -> list[str] that sorts version strings "
                  "ascending by Semantic Versioning 2.0.0 precedence: MAJOR.MINOR.PATCH compared numerically, a "
                  "pre-release version (after '-') has lower precedence than the release, pre-release identifiers "
                  "compared dot by dot (numeric ones numerically, alphanumeric ones in ASCII order, numeric lower "
                  "than alphanumeric, a longer set wins if all preceding are equal), and build metadata (after '+') "
                  "ignored. Versions of equal precedence keep their input order.",
        "tests": """
spec = ['1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta', '1.0.0-beta.2', '1.0.0-beta.11',
        '1.0.0-rc.1', '1.0.0', '1.9.0', '1.10.0', '2.0.0-0', '2.0.0-0.a', '2.0.0-a', '2.0.0', '10.0.0']
for _ in range(20):
    x = spec[:]; random.shuffle(x)
    assert semver_sort(x) == spec, semver_sort(x)
assert semver_sort(['1.0.0+b', '1.0.0', '1.0.0+a']) == ['1.0.0+b', '1.0.0', '1.0.0+a']
assert semver_sort(['1.0.0-rc.1+x', '1.0.0-rc.1', '0.9.9']) == ['0.9.9', '1.0.0-rc.1+x', '1.0.0-rc.1']
assert semver_sort(['1.0.0-Beta', '1.0.0-alpha']) == ['1.0.0-Beta', '1.0.0-alpha']
""",
    },
    {
        "name": "cron_next",
        "prompt": "Write a Python function cron_next(expr: str, after: datetime.datetime) -> datetime.datetime for "
                  "standard 5-field cron expressions (minute hour day-of-month month day-of-week). Each field supports "
                  "'*', numbers, ranges 'a-b', lists 'a,b,c', and steps '*/n' and 'a-b/n'. Day-of-week is 0-7 with "
                  "both 0 and 7 meaning Sunday. As in Vixie cron, if both day-of-month and day-of-week are restricted "
                  "(neither is '*'), a day matches if EITHER matches. Return the earliest matching time strictly after "
                  "`after` (seconds and microseconds zero). Use only the standard library.",
        "tests": """
import datetime as dt
def field(s, lo, hi):
    out = set()
    for part in s.split(','):
        rng, _, step = part.partition('/'); step = int(step or 1)
        if rng == '*': a, b = lo, hi
        elif '-' in rng: a, b = map(int, rng.split('-'))
        else: a = b = int(rng)
        out.update(range(a, b + 1, step))
    return out
def ref(expr, after):
    mi, ho, dm, mo, dw = expr.split()
    M, H, D, MO, W = field(mi, 0, 59), field(ho, 0, 23), field(dm, 1, 31), field(mo, 1, 12), field(dw, 0, 7)
    if 7 in W: W.add(0)
    t = after.replace(second=0, microsecond=0) + dt.timedelta(minutes=1)
    while True:
        if t.month in MO:
            dom, dow = t.day in D, (t.weekday() + 1) % 7 in W
            day = (dom or dow) if (dm != '*' and dw != '*') else (dom and dow)
            if day and t.hour in H and t.minute in M: return t
            if not day: t = (t + dt.timedelta(days=1)).replace(hour=0, minute=0); continue
            t += dt.timedelta(minutes=1)
        else:
            t = (t.replace(day=1) + dt.timedelta(days=32)).replace(day=1, hour=0, minute=0)
cases = ['*/15 9-17 * * 1-5', '0 0 29 2 *', '30 4 1,15 * 5', '0 12 * * 7', '5-59/20 */6 * 1-3,10 *',
         '0 0 31 * *', '59 23 * 12 0', '0 0 1 1 *', '*/7 * 13 * 5', '0 9 * * 1,3,5']
starts = [dt.datetime(2026, 10, 20, 19, 47, 31), dt.datetime(2027, 12, 31, 23, 59), dt.datetime(2028, 2, 28, 23, 0),
          dt.datetime(2026, 1, 1, 0, 0)]
for c in cases:
    for s in starts:
        got, want = cron_next(c, s), ref(c, s)
        assert got == want, (c, s, got, want)
""",
    },
    {
        "name": "json_parse",
        "prompt": "Write a Python function json_parse(s: str) that parses a JSON document (RFC 8259) without using the "
                  "json or ast modules, eval or exec. Support objects, arrays, strings with all escapes including "
                  "\\uXXXX and surrogate pairs, numbers (return int when there is no fraction or exponent, else "
                  "float), true, false, null and whitespace. Raise ValueError for invalid input, including trailing "
                  "commas, leading zeros like 01, single quotes, unescaped control characters in strings, and "
                  "trailing garbage.",
        "tests": """
import json
def gen(d=0):
    r = random.random()
    if d > 3 or r < 0.3:
        return random.choice([None, True, False, random.randint(-10**12, 10**12), random.uniform(-1e6, 1e6),
                              random.choice(['', 'a"b', 'tab\\there', 'é ✓ 😀', '\\\\/', 'line\\nbreak', '\\u0001'])])
    if r < 0.65: return [gen(d + 1) for _ in range(random.randint(0, 4))]
    return {random.choice(['k', 'é', 'a b', '😀', '']) + str(i): gen(d + 1) for i in range(random.randint(0, 4))}
docs = [json.dumps(gen(), ensure_ascii=random.random() < 0.5, indent=random.choice([None, 2])) for _ in range(150)]
docs += ['"\\\\ud83d\\\\ude00"', ' [1e3, -0, 0.5E-2, 1E+2, -12] ', '{"a":[{}, []]}', '"\\\\b\\\\f\\\\n\\\\r\\\\t\\\\/"']
want = [json.loads(d) for d in docs]
bad = ['[1,]', '{"a":1,}', '01', "{'a':1}", '"a\\nb"', '[1] x', '', '[', '{"a" 1}', '1.', '.5', '-', '"\\\\x"',
       'tru', 'nul', '[1 2]', '"\\\\ud83d"x']
forbid('json', 'ast')
got = [json_parse(d) for d in docs]
errs = []
for b in bad:
    try: json_parse(b); errs.append(b)
    except ValueError: pass
    except RecursionError: errs.append(b)
allow()
for d, g, w in zip(docs, got, want):
    assert g == w and type(g) is type(w), (d[:60], g, w)
assert not errs, 'accepted invalid: %r' % errs
""",
    },
    {
        "name": "regex_match",
        "prompt": "Write a Python function regex_match(pattern: str, s: str) -> bool that returns True if the WHOLE "
                  "string matches the pattern, without using the re module. Support literal characters, '.', the "
                  "quantifiers '*', '+' and '?' (applied to the previous atom), character classes like [abc], [a-c] "
                  "and negated [^ab] ('.' inside a class is literal), groups '(...)' that can be quantified, alternation "
                  "'|' (inside groups and at the top level), and '\\' to escape a metacharacter. Empty alternatives like (a|) are allowed. It "
                  "must terminate on patterns like (a*)*.",
        "tests": """
import re
def atom(d):
    r = random.random()
    if r < 0.45: return random.choice('abc')
    if r < 0.55: return '.'
    if r < 0.62: return '\\\\.'
    if r < 0.78: return random.choice(['[ab]', '[a-b]', '[^b]', '[^a.]', '[b-c.]'])
    return '(' + alt(d + 1) + ')' if d < 2 else 'a'
def seq(d): return ''.join(atom(d) + random.choice(['', '', '*', '+', '?']) for _ in range(random.randint(0, 3)))
def alt(d): return '|'.join(seq(d) for _ in range(random.randint(1, 3)))
pairs = [('(a*)*', 'aaaa'), ('(a*)*b', 'aaaa'), ('(a|)+', 'aaa'), ('a|b|', ''), ('\\\\.+', '..'), ('(a|ab)(c|bcd)', 'abcd'),
         ('[^a.]*', 'bcb'), ('(.?)*c', 'abc')]
for _ in range(400):
    p = alt(0)
    for _ in range(6): pairs.append((p, ''.join(random.choice('abc.') for _ in range(random.randint(0, 7)))))
want = [re.fullmatch(p, s) is not None for p, s in pairs]
forbid('re')
got = [regex_match(p, s) for p, s in pairs]
allow()
wrong = [(p, s, w) for (p, s), g, w in zip(pairs, got, want) if g != w]
assert not wrong, '%d wrong, e.g. %r' % (len(wrong), wrong[:3])
""",
    },
    {
        "name": "osa_distance",
        "prompt": "Write a Python function osa_distance(a: str, b: str) -> int returning the optimal string alignment "
                  "distance: the minimum number of insertions, deletions, substitutions and transpositions of two "
                  "ADJACENT characters to turn a into b, where no substring is edited more than once (so it is not "
                  "the unrestricted Damerau-Levenshtein distance; osa_distance('ca', 'abc') is 3).",
        "tests": """
def ref(a, b):
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1): d[i][0] = i
    for j in range(len(b) + 1): d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            c = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]
assert osa_distance('ca', 'abc') == 3 and osa_distance('abcd', 'acbd') == 1 and osa_distance('', 'abc') == 3
for _ in range(2000):
    a = ''.join(random.choice('abc') for _ in range(random.randint(0, 7)))
    b = ''.join(random.choice('abc') for _ in range(random.randint(0, 7)))
    assert osa_distance(a, b) == ref(a, b), (a, b, osa_distance(a, b), ref(a, b))
""",
    },
    {
        "name": "parse_csv",
        "prompt": "Write a Python function parse_csv(text: str) -> list[list[str]] for RFC 4180 CSV without using the "
                  "csv module. Fields are separated by commas and records by '\\n' or '\\r\\n'. A field may be "
                  "enclosed in double quotes, and then may contain commas, CR, LF, and doubled quotes \"\" meaning one "
                  "quote. A final line ending does not start an extra record. Raise ValueError for an unterminated "
                  "quoted field or text after a closing quote (like \"a\"b).",
        "tests": """
import csv, io
rows_all, texts = [], []
for _ in range(300):
    rows = [[''.join(random.choice('ab ,"\\n\\r') for _ in range(random.randint(0, 5))) for _ in range(random.randint(1, 4))]
            for _ in range(random.randint(1, 4))]
    rows = [r for r in rows if r != ['']] or [['x']]
    buf = io.StringIO()
    csv.writer(buf, lineterminator=random.choice(['\\n', '\\r\\n'])).writerows(rows)
    t = buf.getvalue()
    if random.random() < 0.3: t = t.rstrip('\\r\\n') if not t.endswith('"\\r\\n') and not t.endswith('"\\n') else t
    rows_all.append(rows); texts.append(t)
bad = ['"abc', 'a,"b', '"a"b,c', 'x\\n"y""']
forbid('csv')
got = [parse_csv(t) for t in texts]
errs = []
for b in bad:
    try: parse_csv(b); errs.append(b)
    except ValueError: pass
allow()
for t, g, w in zip(texts, got, rows_all):
    assert g == w, (t, g, w)
assert not errs, 'accepted invalid: %r' % errs
""",
    },
    {
        "name": "run_limited",
        "prompt": "Write an async Python function run_limited(factories, limit) where factories is a list of "
                  "zero-argument callables that each return an awaitable. Run them with at most `limit` running at "
                  "once, starting them in list order, and return their results in list order. If one raises, cancel "
                  "all the others that are still running, don't start any more, and re-raise that exception. Use only "
                  "asyncio.",
        "tests": """
import asyncio
state = {'now': 0, 'peak': 0, 'started': [], 'cancelled': 0}
def job(i, delay, fail=False):
    async def run():
        state['started'].append(i); state['now'] += 1; state['peak'] = max(state['peak'], state['now'])
        try:
            await asyncio.sleep(delay)
            if fail: raise KeyError(i)
            return i * 10
        except asyncio.CancelledError:
            state['cancelled'] += 1; raise
        finally:
            state['now'] -= 1
    return run
delays = [0.05, 0.01, 0.03, 0.02, 0.04, 0.01, 0.02, 0.05, 0.01, 0.03]
res = asyncio.run(run_limited([job(i, d) for i, d in enumerate(delays)], 3))
assert res == [i * 10 for i in range(10)], res
assert state['peak'] == 3, state
assert state['started'][:3] == [0, 1, 2], state
assert asyncio.run(run_limited([], 2)) == []
state.update(now=0, peak=0, started=[], cancelled=0)
fs = [job(0, 0.2), job(1, 0.01, fail=True), job(2, 0.2)] + [job(i, 0.01) for i in range(3, 8)]
try:
    asyncio.run(run_limited(fs, 3)); raise SystemExit('no exception')
except KeyError as e:
    assert e.args == (1,), e
assert state['cancelled'] >= 2, state
assert set(state['started']) <= {0, 1, 2, 3}, state
assert state['now'] == 0, state
""",
    },
    {
        "name": "lex_shortest_path",
        "prompt": "Write a Python function shortest_path(graph: dict[str, dict[str, int]], src: str, dst: str) "
                  "returning (cost, path) for the cheapest SIMPLE path (no repeated nodes) from src to dst in a "
                  "directed graph with non-negative (possibly zero) edge weights, where graph[u][v] is the weight of "
                  "u->v and nodes may appear only as edge targets. Among all cheapest simple paths return the "
                  "lexicographically smallest path (as a list of node names). Return None if dst is unreachable. "
                  "If src == dst return (0, [src]).",
        "tests": """
def ref(g, s, t):
    best = None
    def dfs(u, path, cost):
        nonlocal best
        if u == t:
            if best is None or (cost, path) < best: best = (cost, path[:])
            return
        for v, w in g.get(u, {}).items():
            if v not in path: path.append(v); dfs(v, path, cost + w); path.pop()
    dfs(s, [s], 0)
    return best
assert shortest_path({'a': {'b': 1}}, 'a', 'a') == (0, ['a'])
assert shortest_path({'a': {'b': 1}}, 'b', 'a') is None
assert shortest_path({'s': {'v': 0, 'b': 1}, 'v': {'a': 0, 'z': 1}, 'a': {'v': 0}, 'b': {'z': 0}}, 's', 'z') == (1, ['s', 'b', 'z'])
for _ in range(600):
    n = random.randint(2, 7); names = random.sample('abcdefgh', n)
    g = {u: {v: random.choice([0, 0, 1, 1, 2, 3]) for v in names if v != u and random.random() < 0.4} for u in names}
    s, t = random.sample(names, 2)
    got, want = shortest_path(g, s, t), ref(g, s, t)
    if got is not None: got = (got[0], list(got[1]))
    assert got == want, (g, s, t, got, want)
""",
    },
]
