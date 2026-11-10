#!/usr/bin/env python3
# Repeated quality benchmark for an OpenAI-compatible server: 21 coding tasks (coding_tasks_hard.py + coding_tasks_v2.py,
# graded by unit tests in a throwaway container with no network) and 40 arithmetic word problems (arith.py, exact
# answers), each asked RUNS times. One run of the old 8-task set could not tell two builds apart (the same server
# scored 4/8 and 6/8 an hour apart); this gives 63 + 120 samples per arm and a pass rate per task.
#   quality.py <base_url> <api_key> <label>
#   RUNS=3        rounds (default 3)
#   ONLY=code|arith
#   THINK=1       thinking on for the arithmetic problems (coding stays off: 16K-token thinking per task takes hours)
#   THINK_CODE=1  thinking on for the coding tasks too, with 16,000 extra tokens per answer
#   COOL=76       before each request wait until every GPU is below this (default 76; 0 = don't wait)
# Writes <out>/quality-<label>.jsonl (one line per answer) and prints a summary; OUT_DIR defaults to ~/bench.
import json, os, re, subprocess, sys, tempfile, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coding_tasks_hard import TASKS as HARD, PRELUDE
from coding_tasks_v2 import TASKS as V2
import arith

URL, KEY, LABEL = sys.argv[1], sys.argv[2], sys.argv[3]
RUNS, ONLY = int(os.environ.get("RUNS") or 3), os.environ.get("ONLY", "")
THINK, COOL = os.environ.get("THINK") == "1", int(os.environ.get("COOL", "76"))
THINK_CODE = os.environ.get("THINK_CODE") == "1"
SANDBOX = os.environ.get("SANDBOX_IMAGE", "python:3.12-slim")
OUT = os.path.join(os.path.expanduser(os.environ.get("OUT_DIR", "~/bench")), "quality-%s.jsonl" % LABEL)
CODE_SYSTEM = "You are a careful Python programmer. Reply with one ```python code block containing the complete code, no tests."


def ask(system, prompt, max_tokens, think):
    body = {"model": "x", "max_tokens": max_tokens, "temperature": 0, "cache_prompt": False,
            "chat_template_kwargs": {"enable_thinking": think},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    req = urllib.request.Request(URL + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    t0 = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=1200))
    m = d["choices"][0]["message"]
    return m.get("content") or "", d.get("timings", {}), time.time() - t0, len(m.get("reasoning_content") or "")


def wait_cool():
    while COOL:
        temps = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True).stdout.split()
        if not temps or max(int(x) for x in temps) < COOL:
            return
        time.sleep(10)


def grade_code(answer, tests):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", answer, re.S)
    if not blocks:
        return False, "no code block"
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "t.py"), "w") as f:
            f.write(max(blocks, key=len) + "\n\n" + PRELUDE + "\n" + tests)
        os.chmod(d, 0o755)
        r = subprocess.run(["docker", "run", "--rm", "--network", "none", "--memory", "1g", "--pids-limit", "64",
                            "-v", d + ":/w:ro", "--entrypoint", "timeout", SANDBOX, "40", "python3", "-I", "/w/t.py"],
                           capture_output=True, text=True)
    if r.returncode == 0:
        return True, ""
    err = (r.stderr or r.stdout).strip().splitlines()
    return False, err[-1][:100] if err else "exit %d" % r.returncode


items = []
if ONLY != "arith":
    items += [("code", t) for t in HARD + V2]
if ONLY != "code":
    items += [("arith", p) for p in arith.problems()]
tally = {}
with open(OUT, "a") as log:
    for run in range(1, RUNS + 1):
        for kind, t in items:
            wait_cool()
            try:
                if kind == "code":
                    answer, tm, secs, think = ask(CODE_SYSTEM, t["prompt"], 6000 + (16000 if THINK_CODE else 0), THINK_CODE)
                    ok, why = grade_code(answer, t["tests"])
                else:
                    answer, tm, secs, think = ask(arith.SYSTEM, t["prompt"], 1500 + (8000 if THINK else 0), THINK)
                    ok, why = arith.grade(answer, t["answer"])
            except Exception as e:  # a failed request is recorded, not counted as a wrong answer
                print("%-10s run %d %-5s %-20s ERROR %s" % (LABEL, run, kind, t["name"], str(e)[:80]), flush=True)
                log.write(json.dumps({"label": LABEL, "run": run, "kind": kind, "task": t["name"], "error": str(e)[:200]}) + "\n")
                continue
            tally.setdefault((kind, t["name"]), []).append(ok)
            log.write(json.dumps({"label": LABEL, "run": run, "kind": kind, "task": t["name"], "ok": ok, "why": why,
                                  "tokens": tm.get("predicted_n", 0), "tok_s": round(tm.get("predicted_per_second", 0), 1),
                                  "secs": round(secs, 1), "think_chars": think, "answer": answer}) + "\n")
            log.flush()
            print("%-10s run %d %-5s %-20s %s %5d tok @ %5.1f tok/s %6.1f s  %s" % (
                LABEL, run, kind, t["name"], "PASS" if ok else "FAIL", tm.get("predicted_n", 0),
                tm.get("predicted_per_second", 0), secs, why), flush=True)

for kind in ("code", "arith"):
    rows = [(n, v) for (k, n), v in tally.items() if k == kind]
    if not rows:
        continue
    total, n = sum(sum(v) for _, v in rows), sum(len(v) for _, v in rows)
    print("%-10s %s total %d/%d (%.0f%%); per run: %s; always %d, never %d, mixed %d of %d tasks" % (
        LABEL, kind, total, n, 100 * total / n,
        " ".join(str(sum(v[i] for _, v in rows if len(v) > i)) for i in range(RUNS)),
        sum(all(v) for _, v in rows), sum(not any(v) for _, v in rows),
        sum(any(v) and not all(v) for _, v in rows), len(rows)))
    if kind == "code":
        print("%-10s code by task: %s" % (LABEL, "  ".join("%s %d/%d" % (n, sum(v), len(v)) for n, v in rows)))
print("QUALITY-DONE")
