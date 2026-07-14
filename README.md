<h1 align="center">jq.mq</h1>

A [jq](https://jqlang.org/) interpreter implemented as an [mq](https://github.com/harehare/mq) module.

## Features

- Identity (`.`) and field access (`.foo`, `.foo.bar`)
- Array/object indexing (`.[0]`, `.["key"]`) and slicing (`.[1:3]`)
- Iterator (`.[]`) and recursive descent (`..`)
- Pipe (`|`), comma (`,`), and alternative operator (`//`)
- Arithmetic (`+`, `-`, `*`, `/`, `%`) and comparison operators
- Boolean logic (`and`, `or`, `not`)
- String interpolation (`"Hello, \(.name)!"`)
- `if-then-else-end` and `if-elif-else-end`
- `try-catch` error handling
- `reduce`, `foreach`, `as` bindings, `label-break`
- User-defined functions (`def name(args): body;`)
- Format strings (`@base64`, `@uri`, `@csv`, `@tsv`, `@html`, `@json`, `@text`)
- Comprehensive builtin library (see [API](#api))

## Installation

Copy `jq.mq` to your mq module directory, or place it anywhere and reference it with `-L`.

```sh
cp jq.mq ~/.local/mq/config/
```

## Usage

```sh
mq -L /path/to/modules -I null \
  'include "jq" | jq_run(".[].name", .)' data.md
```

## API

### `jq_run(program, input)`

Evaluates a jq program against the given input. Returns an array of all outputs (jq produces streams).

| Parameter | Type | Description |
|---|---|---|
| `program` | String | jq expression to evaluate |
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

Parses a jq program and returns the compiled AST. Useful for evaluating the same program repeatedly.

```mq
let ast = jq_compile(".[] | . * 2")
| jq_eval(ast, [1, 2, 3])
# => [2, 4, 6]
```

### `jq_eval(ast, input)`

Evaluates a pre-compiled AST against the given input.

## Supported Builtins

| Category | Builtins |
|---|---|
| Types | `type`, `arrays`, `objects`, `strings`, `numbers`, `booleans`, `nulls`, `iterables`, `scalars` |
| Length | `length`, `utf8bytelength` |
| Keys/Values | `keys`, `values`, `has`, `in`, `to_entries`, `from_entries`, `with_entries` |
| Collections | `map`, `map_values`, `select`, `empty`, `add`, `flatten`, `transpose`, `walk`, `del`, `range`, `sort`, `sort_by`, `group_by`, `unique`, `unique_by`, `min`, `max`, `min_by`, `max_by`, `reverse`, `contains`, `inside`, `indices`, `index`, `rindex` |
| Math | `floor`, `ceil`, `round`, `sqrt`, `fabs`, `abs`, `nan`, `infinite`, `isinfinite`, `isnan`, `isnormal`, `isfinite`, `finites`, `normals` |
| Strings | `split`, `join`, `ltrimstr`, `rtrimstr`, `ltrim`, `rtrim`, `trim`, `trimstr`, `startswith`, `endswith`, `ascii_downcase`, `ascii_upcase`, `explode`, `implode`, `tostring`, `tonumber`, `tojson`, `fromjson`, `test`, `match`, `capture`, `scan`, `sub`, `gsub` |
| Paths | `paths`, `leaf_paths`, `getpath`, `setpath`, `delpaths` |
| Iteration | `any`, `all`, `recurse`, `first`, `last`, `nth`, `limit`, `until`, `while` |
| Misc | `error`, `debug`, `env`, `builtins` |

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

## Compatibility

Requires [mq](https://github.com/harehare/mq) v0.6 or later.

## License

MIT
