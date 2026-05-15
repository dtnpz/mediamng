#!/bin/bash

for file in *; do
    if [[ $file =~ _shift[^.]*\. ]]; then
        new_name=$(echo "$file" | sed -E 's/_shift[^.]*//')
        mv "$file" "$new_name"
        echo "Renamed: $file -> $new_name"
    fi
done
