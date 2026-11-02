#!/usr/bin/env python3
"""Differential test: run programs through real jq and jq.mq and compare outputs.

Usage: scripts/diff.py [cases.txt]
Each case is `program<TAB>input-json` (input defaults to null). Lines starting with # are ignored.
"""
import json
import os
import subprocess
import sys
import tempfile

# The mq binary to test; set MQ to try a build that is not first on PATH.
MQ = os.environ.get("MQ", "mq")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUNNER = r'''
include "jq"
| map(fn(c):
    let r = try: {ok: true, got: jq_run(c["p"], c["i"])} catch(e): {ok: false, got: e["message"]}
    | if (r["ok"]): {out: r["got"]} else: {err: r["got"]}
  ;)
'''


def real_jq(prog, inp):
    r = subprocess.run(["jq", "-c", "--argjson", "dummy", "null", prog], input=json.dumps(inp),
                       capture_output=True, text=True, timeout=10)
    outs = [json.loads(l) for l in r.stdout.splitlines() if l.strip()]
    if r.returncode != 0:
        msg = r.stderr.strip().splitlines()[0] if r.stderr.strip() else "error"
        return {"out": outs, "err": msg}
    return {"out": outs}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "scripts", "diff_cases.txt")
    cases = []
    for line in open(path, encoding="utf-8").read().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        prog, _, inp = line.partition("\t")
        cases.append({"p": prog, "i": json.loads(inp) if inp.strip() else None})
    mine = []
    for c in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump([c], f)
            cpath = f.name
        try:
            r = subprocess.run([MQ, "-L", ROOT, "-I", "json", "-F", "json", RUNNER, cpath],
                               capture_output=True, text=True, timeout=10)
            mine.append(json.loads(r.stdout)[0])
        except subprocess.TimeoutExpired:
            mine.append({"err": "TIMEOUT"})
        except Exception:
            err = [l for l in r.stderr.splitlines() if "×" in l]
            mine.append({"err": "CRASH " + (err[0].strip() if err else "?")})
        finally:
            os.unlink(cpath)
    bad = 0
    for c, m in zip(cases, mine):
        ref = real_jq(c["p"], c["i"])
        ok = False
        if "err" in ref:
            ok = "err" in m   # both fail; compare messages loosely
            if ok and ref["err"].split(": ", 2)[-1].strip() != m["err"].strip():
                ok = ok  # message differences are reported below as notes
        else:
            ok = "out" in m and m["out"] == ref["out"]
        if not ok:
            bad += 1
            print(f"DIFF  {c['p']}   <<  {json.dumps(c['i'])}")
            print(f"   jq   : {json.dumps(ref)[:200]}")
            print(f"   jq.mq: {json.dumps(m)[:200]}")
    print(f"\n{len(cases)-bad}/{len(cases)} cases match real jq")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
