<h1 align="center">jq.mq</h1>

A [jq](https://jqlang.org/) interpreter written as an [mq](https://github.com/harehare/mq) module. It follows **jq 1.8.2** and passes 820 of the 822 cases of the official test files.

## Usage

Copy `jq.mq` to your mq module directory, or point to it with `-L`.

```sh
mq -L . -I null 'include "jq" | jq_run(".[].name", .)' data.json
```

Without a local copy (needs `--allow-http-import`; pin a release with `@vX.Y.Z`):

```sh
mq --allow-http-import -I null 'include "github.com/harehare/jq.mq" | jq_run(".[].name", .)' data.md
```

```mq
include "jq"
| let data = {"scores": [42, 87, 15, 93, 61]}
| jq_run_first("[.scores[] | select(. >= 60)] | sort | reverse", data)
# => [93, 87, 61]
```

## What is supported

The whole jq 1.8 language and builtins: paths and assignment, `reduce`/`foreach`/`label`/`limit`, destructuring, user functions, string formats, regular expressions (with `\R`, `\X`, lookaround, backreferences), dates, `input`/`inputs`, `$ARGS`, `debug`/`stderr`, modules (`import`, `include`, `modulemeta`) and jq's own `fromjson`. Ordering, number formatting, error messages and evaluation order match jq.

## API

| Function | Does |
|---|---|
| `jq_run(program, input)` | All outputs as an array. An uncaught error is raised as an mq error. |
| `jq_run_first(program, input)` | The first output, or `None`. |
| `jq_run_opts(program, input, opts)` | `jq_run` with options. |
| `jq_run_result(program, input, opts)` | `{outputs, error}`: keeps the outputs before an uncaught error. |
| `jq_compile(program)` / `jq_compile_opts(program, opts)` | Compile once; evaluate with `jq_eval`, `jq_eval_opts` or `jq_eval_result`. |
| `jq_ast(program)` | The syntax tree. |

Options (`opts` is a dict):

| Option | Meaning |
|---|---|
| `inputs` | Values read by `input` and `inputs`. When they run out, `input` raises `break` like jq. |
| `named` | `--arg`/`--argjson`: `{frame: 6}` defines `$frame` and `$ARGS.named`. |
| `positional` | `$ARGS.positional`. |
| `filename` | `input_filename`. |
| `library_paths` | Directories searched by `import`/`include` (jq's `-L`). |
| `module_sources` | Module text keyed by the path it would have, used before the file system. |

```mq
jq_run_opts("[input, input, $n]", None, {inputs: [10, 20, 30], named: {n: 7}})
# => [[10, 20, 7]]

jq_run_result("1, 2, error(\"boom\"), 3", None, dict())
# => {"outputs": [1, 2], "error": "boom"}
```

Reading module files needs `mq --allow-read`, and `$ENV` needs `--allow-env`.

## Compatibility

jq.mq needs an mq newer than v0.10.0: `error(value)` with `e["value"]`, in-place appends to captured variables, exact division and integer checks, exponent notation for numbers, `regex_match_info`, and a call depth limit of 100,000. On v0.10.0 only 603 of 822 official cases pass.

## Known limitations

- **Recursion depth** (mq allows 100,000 frames): functions with only `$value` parameters recurse about 19,800 levels and can make any number of calls (`fib` of 25 takes 0.6 s). Functions with filter parameters, or that call the filter form of a `$value` parameter, reach about 8,200 levels.
- **Number literals** are doubles; jq keeps the text of unchanged literals such as `12345678901234567890123456789`.
- **`==`** is not limited to 10000 nesting levels (jq: "Equality check too deep").
- **Time zones**: `%Z` prints `UTC` or the offset (`+09`), not an abbreviation like `JST`.
- **`stderr`/`halt_error`** end their output with a newline.
- **Regex**: `\X` is an approximation; POSIX collating elements are not implemented (neither in Oniguruma).
- `$__prog_args` is not available; `input_line_number` is always 0.

## Development

```sh
mq-test jq_tests.mq
```

## License

MIT
