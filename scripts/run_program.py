#!/usr/bin/env python3
"""Run a jq program file with jq and with jq.mq, and compare what they print.

    python3 scripts/run_program.py PROGRAM.jq [--stdin FILE] [--argjson NAME=JSON]...
                                   [--arg NAME=TEXT]... [--args A B ...] [--raw]

The program is run like `jq -n [-r] -f PROGRAM.jq` with the values of --stdin available to
`input` and `inputs`. Set MQ to choose the mq binary (default `mq`); the filesystem and
environment flags of mq are passed through MQ_FLAGS (for example "--allow-read").
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MQ = os.environ.get("MQ", "mq")
MQ_FLAGS = os.environ.get("MQ_FLAGS", "").split()

RUNNER = """include "jq"
| jq_run_result(self["program"], None, {inputs: self["inputs"], named: self["named"], positional: self["positional"]})
"""


def read_values(path):
    """The JSON values of a file, as jq reads its input stream."""
    if path is None:
        return []
    text = open(path, encoding="utf-8").read()
    decoder = json.JSONDecoder()
    values, pos = [], 0
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            return values
        value, pos = decoder.raw_decode(text, pos)
        values.append(value)


def render(outputs, raw):
    """What the jq command line prints for a list of outputs."""
    lines = []
    for value in outputs:
        if raw and isinstance(value, str):
            lines.append(value)
        else:
            lines.append(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return "".join(line + "\n" for line in lines)


def run_jq(args, program, stdin_text):
    cmd = ["jq", "-n"] + (["-r"] if args.raw else []) + jq_vars(args) + ["-f", program]
    if args.positional:
        cmd += ["--args"] + args.positional
    r = subprocess.run(cmd, input=stdin_text, capture_output=True, text=True)
    return r.stdout, r.stderr.strip(), r.returncode


def jq_vars(args):
    out = []
    for item in args.argjson:
        out += ["--argjson"] + item.split("=", 1)
    for item in args.arg:
        out += ["--arg"] + item.split("=", 1)
    return out


def run_mq(args, program):
    named = {}
    for item in args.argjson:
        name, text = item.split("=", 1)
        named[name] = json.loads(text)
    for item in args.arg:
        name, text = item.split("=", 1)
        named[name] = text
    data = {
        "program": open(program, encoding="utf-8").read(),
        "inputs": read_values(args.stdin),
        "named": named,
        "positional": args.positional,
    }
    with tempfile.TemporaryDirectory() as tmp:
        data_path = os.path.join(tmp, "data.json")
        runner_path = os.path.join(tmp, "runner.mq")
        json.dump(data, open(data_path, "w", encoding="utf-8"), ensure_ascii=False)
        open(runner_path, "w").write(RUNNER)
        r = subprocess.run(
            [MQ, *MQ_FLAGS, "-L", ROOT, "-I", "json", "-F", "json", "-f", runner_path, data_path],
            capture_output=True, text=True,
        )
    if r.returncode != 0:
        return "", "mq failed: " + (r.stderr.strip() or r.stdout.strip())[:400], 2
    result = json.loads(r.stdout)
    return render(result["outputs"], args.raw), result["error"] or "", 5 if result["error"] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("program")
    parser.add_argument("--stdin", help="file whose JSON values feed input/inputs")
    parser.add_argument("--argjson", action="append", default=[], metavar="NAME=JSON")
    parser.add_argument("--arg", action="append", default=[], metavar="NAME=TEXT")
    parser.add_argument("--args", dest="positional", nargs="*", default=[])
    parser.add_argument("--raw", "-r", action="store_true", help="print strings without quotes")
    parser.add_argument("--show", action="store_true", help="also print the jq.mq output")
    args = parser.parse_args()

    stdin_text = open(args.stdin, encoding="utf-8").read() if args.stdin else ""
    expected, expected_err, _ = run_jq(args, args.program, stdin_text)
    actual, actual_err, _ = run_mq(args, args.program)

    if args.show:
        sys.stdout.write(actual)
    same_out = expected == actual
    # jq prefixes its error text with "jq: error (at <unknown>) : "; compare the core message.
    same_err = (not expected_err) == (not actual_err)
    print(f"output: {'identical' if same_out else 'DIFFERENT'} "
          f"({len(expected)} chars from jq, {len(actual)} from jq.mq, "
          f"{expected.count(chr(10))} / {actual.count(chr(10))} lines)")
    print(f"error:  {'both ok' if not expected_err and not actual_err else 'both failed' if same_err else 'DIFFERENT'}"
          + (f"  jq: {expected_err[:120]!r}  jq.mq: {actual_err[:120]!r}" if expected_err or actual_err else ""))
    if not same_out:
        for number, (a, b) in enumerate(zip(expected.split("\n"), actual.split("\n")), 1):
            if a != b:
                print(f"first difference at line {number}:\n  jq   : {a[:200]!r}\n  jq.mq: {b[:200]!r}")
                break
    return 0 if same_out and same_err else 1


if __name__ == "__main__":
    sys.exit(main())
