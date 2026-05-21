#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: ./miner.sh /path/to/corpus"
    exit 1
fi

CORPUS="$1"

# Read from stdin line-by-line
while read -r raw_target raw_anchor; do
    # 1. Clean up hidden carriage returns (\r) and trailing whitespaces cleanly
    target=$(echo "$raw_target" | tr -d '\r[:space:]')
    anchor=$(echo "$raw_anchor" | tr -d '\r[:space:]')
    
    # Skip if either variable ends up empty
    if [ -z "$target" ] || [ -z "$anchor" ]; then
        continue
    fi
    
    echo "🔍 Searching for [$target] + [$anchor]..."
    
    # 2. Pipeline approach with unrestricted ripgrep (-uu)
    # -uu forces rg to search ALL files, ignoring .gitignore and hidden status
    # First rg finds lines containing the target, second filters for the anchor
    # -m 1 limits the final output to 1 match
    result=$(rg -uu -N "$target" "$CORPUS" | rg -m 1 "$anchor")
    
    if [ -n "$result" ]; then
        echo "✅ Match found:"
        echo "$result"
    else
        echo "❌ No match found."
    fi
    echo ""
done