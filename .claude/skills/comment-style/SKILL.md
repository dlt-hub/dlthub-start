---
name: comment-style
description: How to write comments and docstrings in the dlthub-start CLI (src/create_dlthub_workspace/**). Use when adding/editing a comment or docstring, or reviewing a diff for comment quality.
---

# Comment & docstring style

Keep comments terse and factual. Avoid generated-sounding prose that narrates
reasoning, tradeoffs, or history.

## Rules

1. **Delete first.** If the name, params, or the line already say it, drop the comment.
2. **≤2 lines.** Longer means the prose is the problem — cut, don't reformat.
3. **State what, not the story.** What it does, plus the *one* non-obvious why. No alternatives-considered, no history.
4. **Match siblings.** Private helpers here usually have no docstring; don't add one just because it's new.
5. **Don't restate** the function name or self-describing params (`stream=False`).

## Test

Keep a comment only if removing it makes a maintainer guess wrong about
something not visible in the code. Good keeper (one line):

```python
# --follow blocks until the remote run completes; without it the overview below would be empty.
```

Drop restatements:

```python
# BAD: name already says it
# Streamed subprocess output is recolored uniformly so it reads as nested output.
STREAM_LOG_STYLE = "dim cyan"
```
