# Arithmetic word problems with exact answers, for bench/quality.py. Generated from a seed, so every run and every
# engine gets the same questions. All amounts are built so the exact answer has at most two decimals (no rounding
# rule to argue about). Modelled on the failure Junk GPU Lab reported for Strata (a payment reminder total).
import random
from decimal import Decimal as D

SYSTEM = "Answer the question. End your reply with a line of the form 'ANSWER: <number>' giving only the final number, without a currency sign or thousands separators."


def money(x):
    return f"{x:.2f}"


def problems(seed=20261110, n=40):
    r = random.Random(seed)
    out = []
    for i in range(n):
        kind = i % 5
        if kind == 0:   # payment reminder: unpaid months plus a flat late fee each
            months = r.randint(2, 5); rent = D(r.randint(300, 2400)) + D(r.choice([0, 25, 50, 75])) / 100
            fee = D(r.randint(5, 45)) + D(r.choice([0, 50])) / 100; paid = D(r.randint(0, 3)) * 50
            q = (f"A tenant owes {months} months of rent at ${money(rent)} per month. Each unpaid month also carries a "
                 f"late fee of ${money(fee)}. They have already paid ${money(paid)} towards the debt. What is the total "
                 f"amount still owed?")
            a = months * (rent + fee) - paid
        elif kind == 1:  # invoice lines with a percentage discount on whole-dollar subtotal
            lines = [(r.randint(1, 12), D(r.randint(3, 180))) for _ in range(r.randint(3, 5))]
            disc = r.choice([5, 10, 15, 20, 25]); ship = D(r.randint(5, 40)) + D(r.choice([0, 95, 50])) / 100
            q = ("An invoice has these lines: " + "; ".join(f"{n} x ${money(p)}" for n, p in lines) +
                 f". A {disc}% discount applies to the goods (not to shipping), then shipping of ${money(ship)} is added. "
                 "What is the invoice total?")
            sub = sum(n * p for n, p in lines); a = sub * (100 - disc) / 100 + ship
        elif kind == 2:  # a column of amounts, some negative
            xs = [D(r.randint(-90000, 250000)) / 100 for _ in range(r.randint(6, 9))]
            q = "Add up these ledger entries: " + ", ".join(money(x) for x in xs) + ". What is the sum?"
            a = sum(xs)
        elif kind == 3:  # hours at different rates
            h1 = D(r.randint(10, 160)) / 4; h2 = D(r.randint(1, 20)) / 2; rate = D(r.randint(22, 95))
            q = (f"A contractor worked {h1} ordinary hours at ${money(rate)} per hour and {h2} overtime hours at one and "
                 f"a half times that rate. What is the total pay?")
            a = h1 * rate + h2 * rate * D("1.5")
        else:            # instalments with a percentage late fee on a whole-dollar amount
            n = r.randint(3, 6); inst = D(r.randint(40, 900)); late = r.randint(1, n); pct = r.choice([2, 4, 5, 8, 10])
            dep = D(r.randint(50, 500))
            q = (f"A purchase is paid with a ${money(dep)} deposit and {n} instalments of ${money(inst)}. {late} of the "
                 f"instalments were late, and each late instalment incurs a fee of {pct}% of that instalment. What is "
                 f"the total paid, including the deposit and the fees?")
            a = dep + n * inst + late * inst * pct / 100
        a = D(a)
        assert a == a.quantize(D("0.01")), (q, a)
        out.append({"name": "arith%02d" % i, "prompt": q, "answer": a})
    return out


def grade(reply, answer):
    import re
    m = re.findall(r"ANSWER:\s*\**\s*\$?\s*(-?[\d,]*\.?\d+)", reply)
    if not m:
        m = re.findall(r"-?\$?\d[\d,]*\.?\d*", reply)
        if not m:
            return False, "no number"
    try:
        got = D(m[-1].replace(",", "").replace("$", ""))
    except Exception:
        return False, "unparsable %r" % m[-1]
    return got == answer, "" if got == answer else "got %s, want %s" % (got, answer)


if __name__ == "__main__":
    for p in problems()[:10]:
        print(p["answer"], "|", p["prompt"])
