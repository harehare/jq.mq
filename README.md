<h1 align="center">jq.mq</h1>

A [jq](https://jqlang.org/) interpreter implemented as an [mq](https://github.com/harehare/mq) module, aiming at compatibility with the real `jq` (currently checked against **jq 1.8.2**).

## Features

- The full jq expression language: paths (`.foo`, `."foo"`, `.[0]`, `.[1:3]`, `.[]`, `..`, `?`), pipes, comma, `//`, arithmetic, comparison, `and`/`or`
- Assignment: `=`, `|=`, `+=`, `-=`, `*=`, `/=`, `%=`, `//=` (paths are tracked exactly like jq: `path(f)`, `del(f)`, `paths`, `pick(f)`, …)
- `if`/`elif`/`else`, `try`/`catch` (errors can carry any JSON value), `error`, `?`
- `reduce`, `foreach`, `label`/`break`, `limit`/`first`/`until`/`while`/`repeat` (lazy, so infinite generators work)
- Variables and destructuring: `. as [$a, {b: $c}] | …`, `?//` alternatives
- User-defined functions with closure and `$value` parameters, recursion, nested `def`
- String interpolation and formats: `@text @json @csv @tsv @html @uri @urid @sh @base64 @base64d @base32 @base32d`
- Regular expressions with real match offsets and captures: `test match capture scan split/2 splits sub gsub` (own backtracking engine: named groups, lookaround, backreferences, flags `g i x n p`)
- Dates: `now mktime gmtime localtime strftime strptime strflocaltime todate fromdate dateadd datesub date`
- jq's ordering rules (`null < false < true < numbers < strings < arrays < objects`), number formatting (`1e+17`, `3e-05`, …) and error messages
- Streams, evaluation order and `empty`/error semantics follow jq (for example `[(1,2) + (10,20)]` is `[11,12,21,22]`)

## Installation

Copy `jq.mq` to your mq module directory, or place it anywhere and reference it with `-L`.

```sh
cp jq.mq ~/.local/mq/config/
```

### HTTP Import (no local installation needed)

If `mq` was built with the `http-import` feature, you can import directly from GitHub without any local setup. This requires the `--allow-http-import` flag, which is disabled by default:

```sh
mq --allow-http-import -I null 'include "github.com/harehare/jq.mq" | jq_run(".[].name", .)' data.md
```

Pin to a specific release with `@vX.Y.Z`:

```sh
mq --allow-http-import -I null 'include "github.com/harehare/jq.mq@v1.0.0" | jq_run(".[].name", .)' data.md
```

## Usage

```sh
mq -L /path/to/modules -I null \
  'include "jq" | jq_run(".[].name", .)' data.md
```

## API

### `jq_run(program, input)`

Evaluates a jq program against the given input. Returns an array of all outputs (jq produces streams).
If the program raises an error that is not caught, the error is raised as an mq error.

| Parameter | Type | Description |
|---|---|---|
| `program` | String | jq program to evaluate |
| `input` | Any | Input value |

```mq
jq_run(".[] | . * 2", [1, 2, 3])
# => [2, 4, 6]
```

### `jq_run_first(program, input)`

Evaluates a jq program and returns only the first output value, or `None` if empty.

```mq
jq_run_first(".name", {"name": "Alice", "age": 30})
# => "Alice"
```

### `jq_compile(program)`

Parses and compiles a program once so it can be evaluated repeatedly. The result is an opaque value.

```mq
let program = jq_compile(".[] | . * 2")
| jq_eval(program, [1, 2, 3])
# => [2, 4, 6]
```

### `jq_eval(compiled, input)`

Evaluates a program returned by `jq_compile` against the given input.

### `jq_ast(program)`

Returns the parsed syntax tree (useful for debugging).

## Supported builtins

Everything in the jq 1.8 manual is supported except the items listed under [Known limitations](#known-limitations). That includes, among others:

| Category | Builtins |
|---|---|
| Types / selection | `type`, `arrays`, `objects`, `iterables`, `booleans`, `numbers`, `normals`, `finites`, `strings`, `nulls`, `values`, `scalars`, `empty`, `error`, `select`, `not` |
| Length / keys | `length`, `utf8bytelength`, `keys`, `keys_unsorted`, `has`, `in`, `inside`, `contains`, `to_entries`, `from_entries`, `with_entries`, `map`, `map_values`, `add`, `any`, `all` |
| Paths | `path`, `paths`, `leaf_paths`, `getpath`, `setpath`, `delpaths`, `del`, `pick`, `tostream`, `fromstream`, `truncate_stream` |
| Collections | `range`, `flatten`, `transpose`, `reverse`, `sort`, `sort_by`, `group_by`, `unique`, `unique_by`, `min`, `max`, `min_by`, `max_by`, `index`, `rindex`, `indices`, `bsearch`, `combinations`, `walk`, `recurse`, `first`, `last`, `nth`, `limit`, `skip`, `until`, `while`, `repeat`, `isempty`, `IN`, `INDEX`, `JOIN`, `toarray` |
| Strings | `split`, `join`, `ltrimstr`, `rtrimstr`, `trimstr`, `trim`, `ltrim`, `rtrim`, `startswith`, `endswith`, `ascii_downcase`, `ascii_upcase`, `explode`, `implode`, `tostring`, `tonumber`, `toboolean`, `tojson`, `fromjson`, `ascii`, `@format` |
| Regex | `test`, `match`, `capture`, `scan`, `split/2`, `splits`, `sub`, `gsub` |
| Math | `floor ceil round trunc nearbyint sqrt cbrt pow log log2 log10 exp exp2 exp10 sin cos tan asin acos atan sinh cosh tanh atan2 fabs abs significand logb frexp modf ldexp scalb drem fmod fma copysign fmin fmax infinite nan isinfinite isnan isnormal` |
| Dates | `now`, `mktime`, `gmtime`, `localtime`, `strftime`, `strflocaltime`, `strptime`, `todate`, `fromdate` |
| Misc | `env`, `$ENV`, `$__loc__`, `builtins`, `input`, `inputs`, `debug`, `stderr`, `have_literal_numbers`, `have_decnum`, `getpath` |

## Example

```sh
# Parse and filter JSON data embedded in Markdown
echo '{"users":[{"name":"Alice","age":30},{"name":"Bob","age":25}]}' | \
  mq -L . -I json 'include "jq" | jq_run("[.users[] | select(.age > 26) | .name]", .)'
# => ["Alice"]
```

```mq
# Use in an mq script
include "jq"
|
let data = {"scores": [42, 87, 15, 93, 61]}
| jq_run_first("[.scores[] | select(. >= 60)] | sort | reverse", data)
# => [93, 87, 61]
```

## How it works

A jq program is lexed and parsed into an AST, which is compiled to mq closures in continuation-passing style:
every compiled expression is a function `fn(input, env, emit)` that calls `emit` for each output. This is what makes
generators, `limit`/`first`/`label`, errors in the middle of a stream and path expressions behave like jq, and it is
considerably faster than building an array for every intermediate result. Path expressions (`path(f)`, assignments,
`del`) use a second compiled form that tracks paths alongside values. Builtins that jq defines in jq itself are
parsed from a small prelude, and only when a program references them. Large arrays are built in chunks, so
collecting 100k values stays linear.

## Known limitations

- **Modules**: `import` / `include` / `modulemeta` inside jq programs are not supported.
- **Recursion depth**: mq limits the call stack to 10 000 frames, so user-defined recursion that is not tail-recursive in jq is limited to roughly 600 levels (e.g. `fib` up to ~13). Builtins such as `range`, `recurse`, `until`, `while`, `repeat`, `limit`, `walk` and `paths` are not affected beyond the depth of the data. Very deeply nested data (≥ ~10 000 levels) also hits this limit.
- **Numbers**: numbers are IEEE doubles. jq 1.8's canonicalization of number literals (`100000000000000000000` stays as written, `1E+1000` is preserved) is not reproduced; computed values are formatted exactly like jq.
- **Errors**: `jq_run` returns the array of outputs only if the program finishes; outputs produced before an uncaught error are not returned.
- **`input` / `inputs` / `$__prog_args`**: there is no input stream, `inputs` is empty and `input` raises "No more inputs".
- **`env` / `$ENV`**: the environment is only visible when mq is run with `--allow-env`; otherwise `$ENV` is an empty object.
- **`localtime` / `strflocaltime` / `mktime`** treat all times as UTC.
- **`debug` / `stderr`** pass their input through without printing.
- Regular expressions use the engine in this module (Oniguruma-like semantics); exotic Oniguruma features such as `\X`, `\R`, absent operators and POSIX collating elements are not available.

## Development

```sh
# unit tests
mq-test jq_tests.mq

# official jq test suites (jq.test, onig.test, man.test, manonig.test, optional.test of jq 1.8.2)
python3 scripts/compat.py            # add -v to list failures, --suite jq.test to pick one

# differential test against the installed jq (compares outputs program by program)
python3 scripts/diff.py
```

`scripts/compat.py` downloads the upstream test files on first use into `scripts/.cache/`.

## Compatibility

Developed and tested with [mq](https://github.com/harehare/mq) v0.10.0 (it relies on `catch(e)` binders and the standard `json` module).

## License

MIT
