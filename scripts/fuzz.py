#!/usr/bin/env python3
"""Randomised differential test: random JSON values x generic programs, jq vs jq.mq.

Usage: scripts/fuzz.py [seed] [count]
"""
import json
import os
import random
import subprocess
import sys
import tempfile

# The mq binary to test; set MQ to try a build that is not first on PATH.
MQ = os.environ.get("MQ", "mq")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROGRAMS = [
    "sort", "unique", "tojson", "tostring", "length", "keys", "type", "add", "min", "max", "reverse",
    "[.[]?]", "[..]", "[paths]", "to_entries", "flatten", "map(type)", "group_by(type)",
    "sort_by(type)", "[.[]? | tojson]", "walk(if type==\"number\" then .+1 else . end)", "tostream",
    "[tostream] | fromstream(.[])", "map(select(. != null))", "[.[]? | numbers]", "[.[]? | strings | length]",
    "first, last", "[limit(2; .[]?)]", ". == .", ". < .", "[., .] | sort", "[.] | unique", "contains(.)",
    "inside(.)", "tojson | fromjson", "[.[]? | arrays | length]", "del(.[]?)", "[getpath([0], [\"a\"])]",
    "paths(type == \"number\")", "with_entries(.)", "map_values(.)", "[splits(\"a\")]?", "ascii_downcase?",
    "[.[]? | tostring]", "any, all", "min_by(tojson)", "max_by(tojson)", "unique_by(type)", "[.[]?|numbers] | add",
    "indices(1)", "index(1), rindex(1)", "implode?", "explode?", "@json", "@text", "@csv?", "@html", "@uri",
    "@base64?", "tojson|length", "[recurse] | length", "[.. | scalars]", "env | type", "ltrimstr(\"a\")",
    "splits(\"\")?", "test(\"a\")?", "[match(\".\"; \"g\")?] | length", "tonumber?",
    "[.[]?] | sort | .[0:2]", "{a: .}", "[.[]?] | length", "to_entries? | from_entries?",
]


def rnd_str(r):
    pool = ["", "a", "b", "abc", "ABC", "x y", "é", "日本", "😀", "a\nb", "1", "-2.5", "true", "null", "tab\t", "q\"uote"]
    return r.choice(pool) if r.random() < 0.7 else "".join(r.choice("abcxyz 0123é") for _ in range(r.randint(0, 6)))


def rnd_num(r):
    c = r.random()
    if c < 0.4:
        return r.randint(-5, 20)
    if c < 0.6:
        return r.choice([0.5, -1.5, 3.14159, 123456789.125, 0.1, 2.5, -0.001, 100000, 0.00001234])
    if c < 0.8:
        return r.randint(-10**12, 10**12)
    return round(r.uniform(-1000, 1000), r.randint(0, 6))


def rnd_val(r, depth=0):
    c = r.random()
    if depth > 3 or c < 0.5:
        k = r.random()
        if k < 0.1:
            return None
        if k < 0.2:
            return r.choice([True, False])
        if k < 0.55:
            return rnd_num(r)
        return rnd_str(r)
    if c < 0.78:
        return [rnd_val(r, depth + 1) for _ in range(r.randint(0, 5))]
    return {rnd_str(r): rnd_val(r, depth + 1) for _ in range(r.randint(0, 4))}


RUNNER = r'''
include "jq"
| map(fn(c):
    let r = try: {ok: true, got: jq_run(c["p"], c["i"])} catch(e): {ok: false, got: e["message"]}
    | if (r["ok"]): {out: r["got"]} else: {err: r["got"]}
  ;)
'''


def real_jq(prog, inp):
    r = subprocess.run(["jq", "-c", prog], input=json.dumps(inp), capture_output=True, text=True, timeout=10)
    outs = [l for l in r.stdout.splitlines() if l.strip()]
    return {"out": [json.loads(l) for l in outs], "failed": r.returncode != 0}


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    r = random.Random(seed)
    cases = [{"p": r.choice(PROGRAMS), "i": rnd_val(r)} for _ in range(count)]
    mine = []
    for i in range(0, len(cases), 15):
        chunk = cases[i:i + 15]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(chunk, f)
            path = f.name
        try:
            p = subprocess.run([MQ, "-L", ROOT, "-I", "json", "-F", "json", RUNNER, path],
                               capture_output=True, text=True, timeout=60)
            mine.extend(json.loads(p.stdout))
        except Exception:
            # fall back to one by one
            for c in chunk:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([c], f)
                try:
                    p = subprocess.run([MQ, "-L", ROOT, "-I", "json", "-F", "json", RUNNER, path],
                                       capture_output=True, text=True, timeout=10)
                    mine.append(json.loads(p.stdout)[0])
                except Exception:
                    mine.append({"err": "CRASH/TIMEOUT"})
        finally:
            os.unlink(path)
    bad = 0
    for c, m in zip(cases, mine):
        ref = real_jq(c["p"], c["i"])
        if ref["failed"]:
            ok = "err" in m or True  # jq errors; accept any behaviour that does not crash
            ok = "err" in m
        else:
            ok = m.get("out") == ref["out"]
        if not ok:
            bad += 1
            print(f"DIFF  {c['p']}   <<  {json.dumps(c['i'], ensure_ascii=False)[:160]}")
            print(f"   jq   : {json.dumps(ref, ensure_ascii=False)[:200]}")
            print(f"   jq.mq: {json.dumps(m, ensure_ascii=False)[:200]}")
    print(f"\nseed {seed}: {len(cases)-bad}/{len(cases)} match")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
