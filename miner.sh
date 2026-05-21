#!/bin/bash

# Ensure a corpus path was provided
if [ -z "$1" ]; then
    echo "Usage: ./miner.sh /path/to/corpus"
    exit 1
fi

CORPUS="$1"

# Read from stdin line-by-line
while read -r target anchor; do
    # Skip empty lines or lines with only one word
    if [ -z "$target" ] || [ -z "$anchor" ]; then
        continue
    fi
    
    echo "✅ Match for [$target]:"
    
    # Run ripgrep. 
    # The regex looks for: (target followed by anchor) OR (anchor followed by target)
    # -N removes line numbers to keep the output clean
    # -m 1 stops searching after the first match is found to save even more time
    rg -N -m 1 "$target.*$anchor|$anchor.*$target" "$CORPUS"
    
    echo ""
done