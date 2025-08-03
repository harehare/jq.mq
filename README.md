# jq.mq

> **Note:** This project is currently under active development.

An implementation of jq JSON processor written in the [mq](https://github.com/harehare/mq).

## Overview

This project provides a implementation of the jq command-line JSON processor using the [mq](https://github.com/harehare/mq). It supports JSON parsing, querying, and transformation with a familiar jq-like syntax.

## Usage

### Using the Runner Script

```bash
# Make the script executable
chmod +x run.sh

# Basic usage
./run.sh '{"name": "John", "age": 30}' '.name'

# Array operations
./run.sh '[1,2,3,4,5]' 'length'

# Complex queries with pipes
./run.sh '{"users": [{"name": "Alice"}, {"name": "Bob"}]}' '.users[] | .name'

# Show help
./run.sh --help
```

## Implementation Details

The implementation is structured into several key components:

1. **JSON Parser** - Converts JSON strings into mq data structures
2. **Query Tokenizer** - Breaks down jq queries into executable tokens
3. **Execution Engine** - Processes queries against JSON data
4. **Built-in Functions** - Implements standard jq functions
5. **Output Formatter** - Converts results back to JSON format

## License

This project is provided as-is for educational and demonstration purposes.
