#!/usr/bin/env python3
"""Check how much work jq.mq can do: deep recursion, many calls and large results.

These run on the real mq binary (set MQ to choose it), because mq-test is built with the
debugger, which makes deep recursion take minutes. Each check has a time limit.

    python3 scripts/limits.py
"""
import os
import subprocess
import sys
import time

MQ = os.environ.get("MQ", "mq")
# JQ_ROOT chooses the directory holding jq.mq, for example a checkout of another commit.
ROOT = os.environ.get("JQ_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (description, jq program, expected output as printed by mq, time limit in seconds)
CHECKS = [
    ("fib(22): 28,000 calls, depth 22",
     "def fib: if . < 2 then . else (.-1|fib) + (.-2|fib) end; 22 | fib", "17711", 20),
    ("linear recursion 12000 levels deep",
     "def f: if . == 0 then 0 else (. - 1 | f) + 1 end; 12000 | f", "12000", 20),
    ("value parameter recursion 10000 levels deep",
     "def f($n): if $n == 0 then 0 else 1 + f($n - 1) end; f(10000)", "10000", 20),
    ("100000 calls in a reduce",
     "def inc: . + 1; reduce range(100000) as $i (0; inc)", "100000", 20),
    ("collecting 1,000,000 outputs",
     "[range(1000000)] | length", "1000000", 20),
    ("assigning 65540 elements past the end",
     "[] | .[65540] = 1 | length", "65541", 20),
    ("global match over 540000 characters",
     "(\"lorem ipsum dolor sit amet \" * 20000) | [match(\"\\\\b\\\\w+\\\\b\"; \"g\")] | length", "100000", 20),
    ("a text nested 9999 levels in fromjson",
     "(\"[\" * 9999) + (\"]\" * 9999) | fromjson | flatten | length", "0", 30),
]


def run(program):
    code = 'include "jq" | jq_run(%s, None)' % ('"' + program.replace("\\", "\\\\").replace('"', '\\"') + '"')
    return subprocess.run([MQ, "-L", ROOT, "-I", "null", code], capture_output=True, text=True,
                          timeout=120, input="")


def main():
    failed = 0
    for description, program, expected, limit in CHECKS:
        start = time.time()
        try:
            result = run(program)
        except subprocess.TimeoutExpired:
            print(f"FAIL {description}: no result after 120 s")
            failed += 1
            continue
        elapsed = time.time() - start
        out = result.stdout.strip()
        ok = out == f"[{expected}]" and elapsed <= limit
        print(f"{'ok  ' if ok else 'FAIL'} {description}: {elapsed:.2f} s (limit {limit} s)"
              + ("" if ok else f"  got {out[:80]!r} {result.stderr.strip()[:120]!r}"))
        failed += not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
