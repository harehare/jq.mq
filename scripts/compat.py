#!/usr/bin/env python3
"""Run jq's official test file (tests/jq.test) against jq.mq.

Usage:
  scripts/compat.py [--file jq.test] [--filter SUBSTR] [--verbose] [--chunk N]

The jq.test file is downloaded on first use into scripts/.cache/. Each case is
three lines (program / input / expected outputs, blank-line separated).
`%%FAIL` blocks (compile-error expectations) are skipped.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

# The mq binary to test; set MQ to try a build that is not first on PATH.
MQ = os.environ.get("MQ", "mq")
# The tests read the environment (PAGER=less, as jq's own test runner sets) and, later, module files.
MQ_FLAGS = os.environ.get("MQ_FLAGS", "--allow-env --allow-read").split()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "scripts", ".cache")
URL = "https://raw.githubusercontent.com/jqlang/jq/jq-1.8.2/tests/{name}"
SUITES = ["jq.test", "onig.test", "man.test", "manonig.test", "optional.test"]

# Like jq's own test runner, an error after all the expected outputs have been produced is fine.
RUNNER = r'''
include "jq"
| map(fn(c):
    let r = try: jq_run_result(c["p"], c["i"], dict()) catch(e): {outputs: [], error: e["message"], compile: true}
    | if (r["outputs"] == c["e"] && is_none(r["compile"])): "PASS"
      elif (!is_none(r["error"])): "ERR " + r["error"]
      else: "FAIL " + to_string(r["outputs"])
  ;)
'''


def load_cases(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    cases = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#") or line.strip() == "":
            i += 1
            continue
        if line.startswith("%%FAIL"):
            while i < len(lines) and lines[i].strip() != "":
                i += 1
            continue
        prog = line
        i += 1
        inp = lines[i]
        i += 1
        outs = []
        while i < len(lines) and lines[i].strip() != "":
            outs.append(lines[i])
            i += 1
        try:
            cases.append({
                "p": prog,
                "i": json.loads(inp),
                "e": [json.loads(o) for o in outs],
                "src": f"{prog}  <<  {inp}",
            })
        except Exception:
            pass  # nan / invalid literals, skip
    return cases


def run_chunk(cases, timeout):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([{"p": c["p"], "i": c["i"], "e": c["e"]} for c in cases], f)
        path = f.name
    try:
        r = subprocess.run(
            [MQ, *MQ_FLAGS, "-L", ROOT, "-I", "json", "-F", "json", RUNNER, path],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PAGER": "less"},
        )
    except subprocess.TimeoutExpired:
        return None
    finally:
        os.unlink(path)
    try:
        return json.loads(r.stdout)
    except Exception:
        if len(cases) == 1:
            err = [l for l in r.stderr.splitlines() if "×" in l]
            return ["CRASH " + (err[0].strip() if err else (r.stderr.strip().splitlines() or ["?"])[-1])[:160]]
        return None


def run(cases, chunk, timeout):
    results = []
    for k in range(0, len(cases), chunk):
        part = cases[k:k + chunk]
        out = run_chunk(part, timeout)
        if out is None or len(out) != len(part):
            if len(part) == 1:
                results.append("TIMEOUT")
            else:
                results.extend(run(part, max(1, len(part) // 4), timeout))
        else:
            results.extend(out)
    return results


def suite_path(name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "jq-1.8.2-" + name)
    if not os.path.exists(path):
        urllib.request.urlretrieve(URL.format(name=name), path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", action="append", help="jq.test | onig.test | man.test | manonig.test | optional.test (default: all)")
    ap.add_argument("--file", help="run an arbitrary test file")
    ap.add_argument("--filter")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--chunk", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=4)
    ap.add_argument("--min-pass", type=int, help="exit non-zero if fewer than N cases pass in total (for CI)")
    a = ap.parse_args()
    paths = [(a.file, a.file)] if a.file else [(n, suite_path(n)) for n in (a.suite or SUITES)]
    total = passed = 0
    for name, path in paths:
        cases = load_cases(path)
        if a.filter:
            cases = [c for c in cases if a.filter in c["src"]]
        results = run(cases, a.chunk, a.timeout)
        npass = sum(1 for r in results if r == "PASS")
        for c, r in zip(cases, results):
            if r != "PASS" and a.verbose:
                print(f"[{r[:120]}]\n    {c['src']}\n    expected {json.dumps(c['e'])[:150]}")
        print(f"{name}: {npass}/{len(cases)} passed ({100*npass/max(1,len(cases)):.1f}%)")
        total += len(cases)
        passed += npass
    if len(paths) > 1:
        print(f"TOTAL: {passed}/{total} passed ({100*passed/max(1,total):.1f}%)")
    if a.min_pass is not None:
        return 0 if passed >= a.min_pass else 1
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
