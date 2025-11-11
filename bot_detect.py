#!/usr/bin/env python3
"""
Add `is_bot_close` field to each issue in a JSONL dataset.

Logic:
- is_bot_close = True  if closed_by.username is 'stale[bot]' or 'vue-bot' (case-insensitive)
- is_bot_close = False otherwise

Usage:
    python add_is_bot_close.py issues.jsonl issues_with_bot_flag.jsonl
"""

import json
import sys

def detect_bot_close(issue):
    """
    Return True if the issue was closed by 'stale[bot]' or 'vue-bot' (case-insensitive).
    """
    if not isinstance(issue, dict):
        return False
    closed_by = issue.get("closed_by")
    if not isinstance(closed_by, dict):
        return False

    uname = closed_by.get("username") or closed_by.get("login")
    if not isinstance(uname, str):
        return False

    uname = uname.strip().lower()
    return uname in {"stale[bot]", "vue-bot"}

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "issues.jsonl"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "issues_with_bot_flag.jsonl"

    count = 0
    true_count = 0

    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:

        for line_num, line in enumerate(infile, 1):
            try:
                issue = json.loads(line)
            except json.JSONDecodeError:
                print(f" Skipping invalid JSON on line {line_num}")
                continue

            issue["is_bot_close"] = detect_bot_close(issue)

            if issue["is_bot_close"]:
                true_count += 1
            count += 1

            outfile.write(json.dumps(issue, ensure_ascii=False) + "\n")

    print(f"\nProcessed {count:,} issues.")
    print(f"Marked {true_count:,} as is_bot_close = True.")
    print(f"Output written to: {output_file}\n")

if __name__ == "__main__":
    main()
