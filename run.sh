#!/bin/bash

# jq Implementation Runner Script
# Usage: ./run.sh [json_input] [query]
# Default: json_input="{}", query="."

# Set default values
JSON_INPUT=${1:-"{}"}
QUERY=${2:-"."}

# Show help if -h or --help is passed
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: ./run.sh [json_input] [query]"
    echo "Default: json_input='{}', query='.'"
    echo ""
    echo "Arguments:"
    echo "  json_input   - JSON string to process"
    echo "  query        - jq query expression"
    echo ""
    echo "Example:"
    echo "  ./run.sh '{\"name\": \"John\", \"age\": 30}' '.name'"
    echo "  ./run.sh '[1,2,3,4,5]' 'length'"
    echo "  ./run.sh '{\"users\": [{\"name\": \"Alice\"}, {\"name\": \"Bob\"}]}' '.users[] | .name'"
    exit 0
fi

echo "Running jq implementation" >&2
echo "JSON Input: $JSON_INPUT" >&2
echo "Query: $QUERY" >&2
echo "" >&2

# Run the mq interpreter with the jq implementation
echo $JSON_INPUT | mq -I text "include \"jq\" | jq(\"$QUERY\") | format_json_output()"
