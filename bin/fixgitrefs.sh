#!/bin/bash

echo "Attempting to fix 'does not point to a valid object' errors."
echo "This might take a while..."

git for-each-ref --format="%(refname)" | while read ref; do
    git show-ref --quiet --verify $ref 2>/dev/null || git update-ref -d $ref
done

echo "Complete. Please try a 'git pull --rebase' now."
