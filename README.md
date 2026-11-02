<h1 align="center">jq.mq</h1>

A [jq](https://jqlang.org/) interpreter implemented as an [mq](https://github.com/harehare/mq) module, aiming at compatibility with the real `jq` (currently checked against **jq 1.8.2**).

## Features

- The full jq expression language: paths (`.foo`, `."foo"`, `.[0]`, `.[1:3]`, `.[]`, `..`, `?`), pipes, comma, `//`, arithmetic, comparison, `and`/`or`
- Assignment: `=`, `|=`, `+=`, `-=`, `*=`, `/=`, `%=`, `//=` (paths are tracked exactly like jq: `path(f)`, `del(f)`, `paths`, `pick(f)`, …)
- `if`/`elif`/`else`, `try`/`catch` (errors can carry any JSON value), `error`, `?`
- `reduce`, `foreach`, `label`/`break`, `limit`/`first`/`until`/`while`/`repeat` (lazy, so infinite generators work)
- Variables and destructuring: `. as [$a, {b: $c}] | …`, `?//` alternatives
- Modules: `import`, `include`, data imports (`import "x" as $x;`), `module` metadata and `modulemeta`
- `input` and `inputs`, named arguments (`$name`, `$ARGS`), `debug`, `stderr`, `halt_error`, `$__loc__`, `localtime` and `strflocaltime`
- User-defined functions with closure and `$value` parameters, recursion, nested `def`
- String interpolation and formats: `@text @json @csv @tsv @html @uri @urid @sh @base64 @base64d @base32 @base32d`
- Regular expressions with real match offsets and captures: `test match capture scan split/2 splits sub gsub` (own backtracking engine: named groups, lookaround, backreferences, absent operator, `\R`, `\X`, flags `g i x n p`; long inputs use mq's native engine when the pattern allows it)
- A JSON parser that follows jq's: `fromjson` reports jq's errors with the same line and column and accepts `nan`, `NaN` and `Infinity`
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
If the program raises an error that is not caught, the error is raised as an mq error. For options and for keeping the outputs that come before an error, see `jq_run_opts` and `jq_run_result` below.

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

### `jq_run_opts(program, input, opts)`

Like `jq_run`, with options in the dict `opts`:

| Option | Meaning |
|---|---|
| `inputs` | Array of the values `input` and `inputs` read, in order. Once they are used up `input` raises `break`, like jq. |
| `named` | Dict of named arguments: `{frame: 6}` defines `$frame` and `$ARGS.named` (jq's `--arg` and `--argjson`). |
| `positional` | Array for `$ARGS.positional`. |
| `filename` | The value of `input_filename`. |
| `library_paths` | Directories searched by `import` and `include` (jq's `-L`); see [Modules](#modules). |
| `module_sources` | Dict from the path a module would have to its text, used before the file system. |

```mq
jq_run_opts("[input, input, $n]", None, {inputs: [10, 20, 30], named: {n: 7}})
# => [[10, 20, 7]]
```

### `jq_run_result(program, input, opts)`

Like `jq_run_opts`, but returns `{outputs, error}` instead of raising, so the outputs produced before an uncaught error are kept. `error` is `None`, or the message jq would print.

```mq
jq_run_result("1, 2, error(\"boom\"), 3", None, dict())
# => {"outputs": [1, 2], "error": "boom"}
```

### `jq_compile(program)`, `jq_compile_opts(program, opts)`

Parse and compile a program once so it can be evaluated repeatedly. The result is an opaque value. `jq_compile_opts` takes `library_paths` and `module_sources`.

```mq
let program = jq_compile(".[] | . * 2")
| jq_eval(program, [1, 2, 3])
# => [2, 4, 6]
```

### `jq_eval(compiled, input)`, `jq_eval_opts(compiled, input, opts)`, `jq_eval_result(compiled, input, opts)`

Evaluate a compiled program, like `jq_run`, `jq_run_opts` and `jq_run_result`.

### `jq_ast(program)`

Returns the parsed syntax tree (useful for debugging).

### Modules

`import "path" as name;` makes the functions of `path.jq` (or `path/path.jq`) available as `name::function`, `include "path";` defines them as they are, and `import "path" as $name;` binds `$name` and `$name::name` to the array of the values in `path.json`. The search path is the `search` key of the directive's metadata (relative to the importing file) and then `library_paths`. A module's own definitions and imports are not visible to its importer. Reading module files needs mq's `--allow-read` option; the option `module_sources` provides module text without reading files.

```sh
mq --allow-read -L . -I null 'include "jq" | jq_run_opts("import \"util\" as u; u::shout(\"hi\")", None, {library_paths: ["modules"]})'
```

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
| Misc | `env`, `$ENV`, `$__loc__`, `$ARGS`, `builtins`, `input`, `inputs`, `input_filename`, `debug`, `stderr`, `halt`, `halt_error`, `modulemeta`, `get_search_list`, `have_literal_numbers`, `have_decnum`, `getpath` |

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
considerably faster than building an array for every intermediate result. Because nothing returns until the program
ends, the call depth would grow with every step, so an analysis pass finds the expressions that always yield exactly one
value and compiles them to functions that return it instead. Path expressions (`path(f)`, assignments,
`del`) use a second compiled form that tracks paths alongside values. Builtins that jq defines in jq itself are
parsed from a small prelude, and only when a program references them. Collecting a stream into an array appends
in place, so collecting 100k values stays linear. `import` and `include` are resolved when a program is compiled, and
a regular expression that mq's native engine runs the same way is translated and matched natively on long input.

## Known limitations

- **Recursion depth**: mq limits the call stack to 100,000 frames. Expressions that yield exactly one value are evaluated directly, so a recursive function whose parameters are all `$value` parameters (or none), and whose body does not call the filter form of one of them (`a` for `$a`), can recurse about 19,800 levels deep and make any number of calls (`fib` of 25 takes 0.6 s). A function with a filter parameter, one that generates several outputs, or one that calls the filter form of a value parameter recurses about 8,200 levels deep and its calls nest deeper as the program runs (about 8000 calls in one expression). Exceeding the limit raises "Maximum recursion depth exceeded". Very deeply nested data (≥ ~100,000 levels) also hits it.
- **Equality of deeply nested values**: `==` is not limited to 10000 levels of nesting, whereas jq reports "Equality check too deep". The other limits (comparison, merge, containment, paths, `tojson`, `fromjson`) are the same as jq's.
- **Numbers**: numbers are IEEE doubles. jq 1.8 keeps the text of a number literal that is not changed (`100000000000000000000`, `12345678901234567890123456789`), which jq.mq cannot because mq has no such number; computed values are formatted exactly like jq.
- **Time zones**: `localtime` and `strflocaltime` use the time zone mq runs in (the `TZ` variable), daylight saving time included. mq gives the offset but not the abbreviation of a zone, so `%Z` prints `UTC` or the offset (`+09`) where jq prints `JST`.
- **`debug` / `stderr` / `halt_error`** write through mq, which ends every line: `stderr` and `halt_error` add a newline that jq does not.
- **`env` / `$ENV`** are only visible when mq is run with `--allow-env`; otherwise `$ENV` is an empty object.
- **Modules** are read from disk only when mq is run with `--allow-read`; `~` and `$ORIGIN` are not expanded in search paths.
- **`$__prog_args`** is not available. `input_line_number` is always 0.
- **Regular expressions** use the engine in this module (Oniguruma-like semantics), and mq's native engine for long inputs when the pattern allows it. `\X` is an approximation of an extended grapheme cluster (it covers combining marks, flags, emoji sequences and the common scripts). POSIX collating elements and equivalence classes (`[[.x.]]`, `[[=x=]]`) are not implemented; Oniguruma does not implement them either.
- **NUL characters**: jq stops the "(while parsing ...)" text of a `fromjson` error at a NUL character; jq.mq prints it.

## Development

```sh
# unit tests
mq-test jq_tests.mq

# official jq test suites (jq.test, onig.test, man.test, manonig.test, optional.test of jq 1.8.2)
python3 scripts/compat.py            # add -v to list failures, --suite jq.test to pick one
MQ=/path/to/mq python3 scripts/compat.py   # test an mq build that is not first on PATH

# differential test against the installed jq (compares outputs program by program)
python3 scripts/diff.py

# recursion depth and large inputs, on the real mq (mq-test takes minutes on deep recursion)
python3 scripts/limits.py

# run a jq program file with jq and with jq.mq on the same input values and compare the output
python3 scripts/run_program.py program.jq --stdin values.txt --argjson frame=6 --raw
```

`scripts/compat.py` downloads the upstream test files on first use into `scripts/.cache/`.

## Compatibility

Developed and tested with [mq](https://github.com/harehare/mq) at a commit after v0.10.0. jq.mq relies on these mq features, which are not in v0.10.0:

- `error(value)` accepts any value and `catch(e)` returns it as `e["value"]`;
- appending to a variable captured by a closure (`a += [x]`) is done in place;
- dividing by a tiny non-zero number is not a zero division, and `Number::is_int` is exact;
- very large and small numbers print in exponent notation (`1e21`, `1e-7`);
- `regex_match_info`, which returns match positions and capture groups;
- a call depth limit of 100,000 (it was 10,000).

jq.mq does not work correctly on v0.10.0: errors that carry non-string values are lost, so 603 instead of 820 of the 822 official test cases pass, and collecting a large result takes quadratic time.

## License

MIT
