# LeetCode Solutions

A collection of my LeetCode solutions.
Pushing a solution to `solutions/` triggers a GitHub Actions workflow that **automatically records it in a Notion database**.

## How it works

```
push a solution to solutions/
        │
        ▼
GitHub Actions (notion-sync.yml)
        │  collect changed files (HEAD~1 ↔ HEAD)
        ▼
sync_notion.py
        ├─ LeetCode GraphQL → canonical title, difficulty, topics, description, company tags
        ├─ Problems DB → create a new page, or append the solution to an existing one
        └─ Challenges DB → update points / problem count / list progress / streak
```

- **New problem** (no page with the same number + language): creates a page whose body contains the problem description, the solution code, and empty note sections (📝 Approach / 💡 Key Insight / 🚧 Stuck Point).
- **Existing problem** (same number + language): appends a divider and a new solution section, overwrites complexity / Runtime / Memory with the latest values, and adds to Time Spent.
- A different language for the same problem gets its own page.
- LeetCode boilerplate (the `@lc` header and `Definition for ...` comment blocks) is stripped from the code.

## File conventions

### File name

```
<number>_<title>_<difficulty>.<ext>
```

| Example | Result |
| --- | --- |
| `0001_two-sum_easy.py` | #1, Python, Easy |
| `0042_trapping-rain-water_hard.cpp` | #42, C++, Hard |

- Leading zeros in the number are optional.
- Difficulty must be `easy`, `medium`, or `hard`.
- The canonical title and difficulty come from the LeetCode API; the title in the file name is only used if that lookup fails.
- Files that don't match this pattern are skipped.

Supported languages: Python (`.py`), C++ (`.cpp`), C (`.c`), Java (`.java`), JavaScript (`.js`), TypeScript (`.ts`)

### Metadata comments

Write any of these keys as **single-line comments** in the file and they'll be saved as Notion properties. All are optional.

```python
# time: O(n)
# space: O(n)
# spent: 20
# runtime: 0ms
# memory: 17.8MB
# topic: Hash Table, Array
```

| Key | Notion property | Description |
| --- | --- | --- |
| `time` | Time Complexity | Time complexity |
| `space` | Space Complexity | Space complexity |
| `spent` | Time Spent | Time spent solving (integer, minutes recommended). Accumulates on re-solves |
| `runtime` | Runtime | Runtime from the submission |
| `memory` | Memory | Memory from the submission |
| `topic` | Tags | Comma-separated; merged with LeetCode's topic tags |

- Use the language's line-comment prefix: `#` for Python, `//` for C/C++/Java/JS/TS.
- Values inside `/* ... */` block comments are not recognized.
- Save files as **UTF-8**. Other encodings (e.g. UTF-16) prevent the comments from being read.

## Setup

### 1. Notion

Create a [Notion integration](https://www.notion.so/my-integrations) and connect it to both databases below (Connections → Add).

**Problems DB**

| Property | Type |
| --- | --- |
| Name | Title |
| Number | Number |
| LeetCode URL | URL |
| Date Solved | Date |
| Review Date | Date (auto-set to solve date + 7 days) |
| Difficulty | Select |
| Language | Select |
| Status | Select |
| Lists | Multi-select (`NeetCode 150`, `Blind 75`) |
| Tags | Multi-select |
| Company | Multi-select |
| Time Complexity | Select |
| Space Complexity | Select |
| Time Spent | Number |
| Runtime | Text |
| Memory | Text |

**Challenges DB**

| Property | Type |
| --- | --- |
| Name | Title |
| Type | Select (`Coin`, `Count`, `Completion`, `Streak`) |
| Current | Number |
| Goal | Number |

What each `Type` tracks:

| Type | Value written to Current |
| --- | --- |
| `Coin` | LeetCode points |
| `Count` | Total rows in the Problems DB |
| `Completion` | Problems solved from a list. The row's Name must be `NeetCode 150` or `Blind 75`; Goal is filled in automatically |
| `Streak` | Consecutive days solved, ending today (or yesterday if nothing has been solved yet today) |

### 2. GitHub Secrets

Add these under **Settings → Secrets and variables → Actions → Repository secrets**.

| Name | Value |
| --- | --- |
| `NOTION_TOKEN` | Notion integration token |
| `NOTION_PROBLEMS_DB` | Problems DB ID (32 chars, with or without hyphens) |
| `NOTION_CHALLENGES_DB` | Challenges DB ID |
| `LEETCODE_USERNAME` | LeetCode username (for fetching points) |

They must be Repository secrets; Environment secrets aren't visible to the workflow.

## Notes

- The sync only runs on pushes to `main` that change files under `solutions/`.
- Changed files are taken from **the last commit only** (`HEAD~1..HEAD`). If you push several commits at once, only the last commit's files are synced.
- Company tags are LeetCode Premium data, so they're usually empty without authentication.
- If the LeetCode API lookup fails, the title and difficulty from the file name are used (no description or topics).

## Structure

```
.
├── .github/
│   ├── workflows/notion-sync.yml   # runs the sync on push
│   └── scripts/sync_notion.py      # Notion / LeetCode sync script
└── solutions/                      # solution files
```
