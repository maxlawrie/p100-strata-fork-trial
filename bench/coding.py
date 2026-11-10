#!/usr/bin/env python3
# Runs coding_tasks.py against an OpenAI-compatible server and grades each answer with its unit tests.
# The model's code runs in a throwaway container with no network. Usage: coding.py <base_url> <api_key> <label>
# CODING_SET=hard uses coding_tasks_hard.py instead (bigger tasks, checked against the stdlib on random inputs).
# THINK=1 turns thinking on (default off), BUDGET=N adds Strata's reasoning_budget_tokens, COOL=T waits before each
# task until every GPU is below T C (for long thinking runs that would otherwise trip the 80 C guard).
import json, os, re, subprocess, sys, tempfile, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HARD = os.environ.get("CODING_SET") == "hard"
if HARD:
    from coding_tasks_hard import TASKS, PRELUDE
else:
    from coding_tasks import TASKS
    PRELUDE = ""

URL, KEY, LABEL = sys.argv[1], sys.argv[2], sys.argv[3]
SANDBOX = os.environ.get("SANDBOX_IMAGE", "python:3.12-slim")
THINK, BUDGET, COOL = os.environ.get("THINK") == "1", int(os.environ.get("BUDGET") or 0), int(os.environ.get("COOL") or 0)
SYSTEM = "You are a careful Python programmer. Reply with one ```python code block containing the complete code, no tests."


def ask(prompt):
    body = {"model": "x", "max_tokens": (6000 if HARD else 2500) + (16000 if THINK else 0), "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": THINK},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    if BUDGET:
        body["reasoning_budget_tokens"] = BUDGET
    req = urllib.request.Request(URL + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    t0 = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=600))
    m = d["choices"][0]["message"]
    return m.get("content") or "", d.get("timings", {}), time.time() - t0, len(m.get("reasoning_content") or "")


def wait_cool():
    while COOL:
        temps = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True).stdout.split()
        if max(int(x) for x in temps) < COOL:
            return
        time.sleep(10)


def grade(answer, tests):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", answer, re.S)
    if not blocks:
        return False, "no code block"
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "t.py"), "w") as f:
            f.write(max(blocks, key=len) + "\n\n" + PRELUDE + "\n" + tests)
        os.chmod(d, 0o755)
        r = subprocess.run(["docker", "run", "--rm", "--network", "none", "--memory", "1g", "--pids-limit", "64",
                            "-v", d + ":/w:ro", "--entrypoint", "timeout", SANDBOX, "30" if HARD else "20", "python3", "-I", "/w/t.py"],
                           capture_output=True, text=True)
    if r.returncode == 0:
        return True, ""
    err = (r.stderr or r.stdout).strip().splitlines()
    return False, err[-1][:80] if err else "exit %d" % r.returncode


passed, wall, toks = 0, 0.0, 0
for t in TASKS:
    if os.path.exists(os.path.expanduser(os.environ.get("ABORT_FILE", "ABORT"))):
        print("%-8s ABORT seen, stopping" % LABEL); break
    wait_cool()
    answer, tm, secs, think = ask(t["prompt"])
    ok, why = grade(answer, t["tests"])
    passed += ok; wall += secs; toks += tm.get("predicted_n", 0)
    print("%-8s code %-16s %s  %4d tok @ %5.1f tok/s  %5.1f s  think %5d ch  %s" % (
        LABEL, t["name"], "PASS" if ok else "FAIL", tm.get("predicted_n", 0), tm.get("predicted_per_second", 0), secs, think,
        why), flush=True)
print("%-8s code%s total %d/%d passed, %d tokens, %.0f s" % (LABEL, "-hard" if HARD else "", passed, len(TASKS), toks, wall))
