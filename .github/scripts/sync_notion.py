import os
import re
import requests
from datetime import datetime, timedelta
from html import unescape

NOTION_TOKEN = os.environ["NOTION_TOKEN"]


def normalize_uuid(raw):
    """Notion's API requires hyphenated UUIDs (8-4-4-4-12) in JSON request
    bodies, even though it accepts bare 32-char hex ids in URL paths."""
    value = raw.strip().replace("-", "")
    if len(value) != 32:
        return raw.strip()
    return f"{value[0:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:32]}"


PROBLEMS_DB = normalize_uuid(os.environ["NOTION_PROBLEMS_DB"])
if len(PROBLEMS_DB.replace("-", "")) != 32:
    raise SystemExit(
        f"NOTION_PROBLEMS_DB is missing or malformed: {PROBLEMS_DB!r}. "
        "Check that it's set as a repository secret under Settings > Secrets "
        "and variables > Actions (an empty value means the secret name doesn't "
        "match or it's an Environment secret the job can't see)."
    )

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

NOTION_CODE_LANGUAGE = {
    "Python": "python",
    "C++": "c++",
    "Java": "java",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "C": "c",
}

NEETCODE_150 = [
    1, 2, 3, 11, 15, 17, 19, 20, 21, 22, 23, 25, 33, 36, 39, 40, 42, 43, 45,
    46, 48, 49, 51, 53, 54, 55, 56, 57, 62, 67, 70, 72, 73, 74, 75, 76, 78,
    79, 84, 85, 88, 90, 91, 97, 98, 100, 101, 102, 104, 105, 110, 121, 124,
    125, 128, 130, 131, 133, 136, 138, 139, 141, 143, 146, 150, 152, 153, 155,
    167, 191, 198, 199, 200, 202, 206, 207, 208, 210, 211, 212, 213, 215, 217,
    226, 230, 235, 238, 239, 242, 252, 253, 261, 269, 271, 286, 295, 297, 300,
    309, 312, 322, 323, 329, 338, 347, 355, 371, 378, 380, 381, 384, 394, 416,
    417, 424, 435, 437, 438, 448, 450, 460, 473, 480, 494, 496, 502, 518, 543,
    547, 567, 572, 588, 621, 647, 648, 684, 685, 703, 704, 739, 743, 745, 746,
    778, 787, 792, 853, 875, 876, 895, 901, 904, 907, 912, 953, 973, 981, 994
]

BLIND_75 = [
    1, 3, 11, 15, 19, 20, 21, 23, 33, 39, 42, 49, 53, 55, 56, 62, 70, 72, 76,
    78, 79, 84, 88, 91, 97, 98, 100, 101, 102, 104, 105, 121, 124, 125, 128,
    133, 139, 141, 143, 146, 152, 153, 155, 191, 198, 199, 200, 206, 207, 208,
    210, 212, 213, 217, 226, 230, 235, 238, 239, 242, 295, 300, 322, 323, 338,
    347, 371, 378, 416, 435, 438, 543, 547, 572, 647, 684, 704, 739, 743
]


def get_leetcode_metadata(number):
    """Fetch the canonical title/difficulty/topics/slug for a problem from
    LeetCode's GraphQL API. Returns None on any failure so callers fall
    back to filename-derived metadata."""
    url = "https://leetcode.com/graphql"
    query = """
    query problemsetQuestionList($skip: Int!) {
        problemsetQuestionList: questionList(
            categorySlug: ""
            limit: 1
            skip: $skip
            filters: {}
        ) {
            questions: data {
                questionFrontendId
                title
                titleSlug
                difficulty
                topicTags { name }
            }
        }
    }
    """
    try:
        res = requests.post(
            url,
            json={"query": query, "variables": {"skip": number - 1}},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        res.raise_for_status()
        questions = res.json()["data"]["problemsetQuestionList"]["questions"]
        if not questions or int(questions[0]["questionFrontendId"]) != number:
            return None
        q = questions[0]
        return {
            "title": q["title"],
            "slug": q["titleSlug"],
            "difficulty": q["difficulty"],
            "topics": [t["name"] for t in q["topicTags"]],
        }
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return None


def html_to_description_blocks(html):
    """Best-effort conversion of LeetCode's problem HTML into a mix of
    heading3/code/bulleted_list_item/paragraph blocks."""
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"</li>", "", text)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<pre>", "\n\n", text)
    text = re.sub(r"</pre>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)

    blocks = []
    for chunk in (c.strip() for c in text.split("\n\n")):
        if not chunk:
            continue
        lines = [l.strip() for l in chunk.split("\n") if l.strip()]
        if len(lines) == 1 and re.match(r"^Example\s+\d+:?$", lines[0], re.IGNORECASE):
            blocks.append(heading3_block(lines[0]))
        elif chunk.rstrip(":") == "Constraints":
            blocks.append(heading3_block("Constraints:"))
        elif re.match(r"^(Input|Output)\s*:", lines[0], re.IGNORECASE):
            blocks.append(code_block(chunk, "Plain Text"))
        elif all(l.startswith("- ") for l in lines):
            blocks.extend(bulleted_list_item_block(l[2:].strip()) for l in lines)
        else:
            blocks.append(paragraph_block(chunk))
    return blocks


def get_leetcode_description(slug):
    """Fetch the problem statement for a slug and convert it to paragraph
    blocks. Returns [] on any failure."""
    url = "https://leetcode.com/graphql"
    query = """
    query questionContent($titleSlug: String!) {
        question(titleSlug: $titleSlug) {
            content
        }
    }
    """
    try:
        res = requests.post(
            url,
            json={"query": query, "variables": {"titleSlug": slug}},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        res.raise_for_status()
        html = res.json()["data"]["question"]["content"]
        return html_to_description_blocks(html) if html else []
    except (requests.RequestException, KeyError, TypeError):
        return []


def parse_filename(filepath):
    """0042_trapping-rain-water_hard.py → (42, 'Trapping Rain Water', 'Hard')"""
    filename = os.path.basename(filepath)
    match = re.match(r'(\d+)_(.+)_(easy|medium|hard)\.\w+', filename, re.IGNORECASE)
    if not match:
        return None
    number = int(match.group(1))
    title = match.group(2).replace('-', ' ').title()
    difficulty = match.group(3).capitalize()
    return number, title, difficulty


def parse_comments(filepath):
    """파일 상단 주석에서 메타데이터 파싱"""
    meta = {"topic": [], "time": "", "space": "", "spent": None, "runtime": "", "memory": ""}
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("#"):
                    break
                if "topic:" in line:
                    meta["topic"] = [t.strip() for t in line.split("topic:")[1].split(",")]
                elif "runtime:" in line:
                    meta["runtime"] = line.split("runtime:")[1].strip()
                elif "memory:" in line:
                    meta["memory"] = line.split("memory:")[1].strip()
                elif "time:" in line:
                    meta["time"] = line.split("time:")[1].strip()
                elif "space:" in line:
                    meta["space"] = line.split("space:")[1].strip()
                elif "spent:" in line:
                    meta["spent"] = int(line.split("spent:")[1].strip())
    except OSError:
        pass
    return meta


def get_language(filepath):
    ext_map = {
        "py": "Python", "cpp": "C++", "java": "Java",
        "js": "JavaScript", "ts": "TypeScript", "c": "C"
    }
    ext = filepath.rsplit(".", 1)[-1]
    return ext_map.get(ext, ext.upper())


def get_lists(number):
    lists = []
    if number in NEETCODE_150:
        lists.append("NeetCode 150")
    if number in BLIND_75:
        lists.append("Blind 75")
    return lists


def find_existing_page(number, language):
    """Look up a page with the same problem Number AND Language. Returns
    the full page object if found (so callers can read its current
    property values), else None."""
    url = f"https://api.notion.com/v1/databases/{PROBLEMS_DB}/query"
    res = requests.post(url, headers=HEADERS, json={
        "filter": {
            "and": [
                {"property": "Number", "number": {"equals": number}},
                {"property": "Language", "select": {"equals": language}},
            ]
        }
    })
    if res.status_code != 200:
        print(f"⚠️  Lookup failed for #{number} ({language}): {res.text}")
        return None
    results = res.json().get("results", [])
    return results[0] if results else None


def get_number_property(page, name):
    prop = page.get("properties", {}).get(name) or {}
    return prop.get("number") or 0


def build_update_properties(meta, existing_page):
    """Runtime/Memory/Time Complexity/Space Complexity always overwrite with
    the latest push; Time Spent accumulates onto the page's current total."""
    properties = {}
    if meta["time"]:
        properties["Time Complexity"] = {"select": {"name": meta["time"]}}
    if meta["space"]:
        properties["Space Complexity"] = {"select": {"name": meta["space"]}}
    if meta["runtime"]:
        properties["Runtime"] = {"rich_text": [{"text": {"content": meta["runtime"]}}]}
    if meta["memory"]:
        properties["Memory"] = {"rich_text": [{"text": {"content": meta["memory"]}}]}
    if meta["spent"]:
        properties["Time Spent"] = {"number": get_number_property(existing_page, "Time Spent") + meta["spent"]}
    return properties


def update_page_properties(page_id, properties):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    res = requests.patch(url, headers=HEADERS, json={"properties": properties})
    if res.status_code != 200:
        print(f"❌ Failed to update properties: {res.text}")
    return res.status_code == 200


def add_to_notion(number, title, difficulty, language, meta, topics=None):
    url = "https://api.notion.com/v1/pages"
    leetcode_url = f"https://leetcode.com/problems/{title.lower().replace(' ', '-')}/"
    all_topics = sorted(set((topics or []) + meta["topic"]))
    lists = get_lists(number)

    properties = {
        "Name":         {"title": [{"text": {"content": f"{number:04d}. {title}"}}]},
        "Number":       {"number": number},
        "LeetCode URL": {"url": leetcode_url},
        "Date Solved":  {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        "Difficulty":   {"select": {"name": difficulty}},
        "Language":     {"select": {"name": language}},
        "Status":       {"select": {"name": "Solved"}},
        "Review Date":  {"date": {"start": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")}},
    }

    if lists:
        properties["Lists"] = {"multi_select": [{"name": l} for l in lists]}
    if all_topics:
        properties["Tags"] = {"multi_select": [{"name": t} for t in all_topics]}
    if meta["time"]:
        properties["Time Complexity"] = {"select": {"name": meta["time"]}}
    if meta["space"]:
        properties["Space Complexity"] = {"select": {"name": meta["space"]}}
    if meta["spent"]:
        properties["Time Spent"] = {"number": meta["spent"]}
    if meta["runtime"]:
        properties["Runtime"] = {"rich_text": [{"text": {"content": meta["runtime"]}}]}
    if meta["memory"]:
        properties["Memory"] = {"rich_text": [{"text": {"content": meta["memory"]}}]}

    res = requests.post(url, headers=HEADERS, json={
        "parent": {"database_id": PROBLEMS_DB},
        "properties": properties
    })

    if res.status_code == 200:
        print(f"✅ Added: {number:04d}. {title} ({difficulty})")
        return res.json()["id"]
    print(f"❌ Failed: {res.text}")
    return None


def chunk_text(text, size=2000):
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def paragraph_block(text=""):
    rich_text = [{"type": "text", "text": {"content": c}} for c in chunk_text(text)] if text else []
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text}}


def heading2_block(text):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def heading3_block(text):
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def bulleted_list_item_block(text):
    rich_text = [{"type": "text", "text": {"content": c}} for c in chunk_text(text)] if text else []
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rich_text}}


def divider_block():
    return {"object": "block", "type": "divider", "divider": {}}


def code_block(text, language):
    notion_language = NOTION_CODE_LANGUAGE.get(language, "plain text")
    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [{"type": "text", "text": {"content": c}} for c in chunk_text(text)],
            "language": notion_language,
        },
    }


def append_blocks(page_id, blocks):
    """Append children to a page, chunked to Notion's 100-block-per-request limit."""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    for i in range(0, len(blocks), 100):
        res = requests.patch(url, headers=HEADERS, json={"children": blocks[i:i + 100]})
        if res.status_code != 200:
            print(f"❌ Failed to append blocks: {res.text}")
            return False
    return True


def read_solution(filepath):
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        return f.read()


def strip_lc_comments(code):
    """Remove vscode-leetcode '@lc ...' marker comment lines."""
    return "\n".join(line for line in code.splitlines() if "@lc" not in line)


def solution_and_notes_blocks(filepath, language):
    code = strip_lc_comments(read_solution(filepath))
    return [
        heading2_block("💻 My Solution"),
        code_block(code, language),
        heading3_block("📝 Approach"),
        paragraph_block(),
        heading3_block("💡 Key Insight"),
        paragraph_block(),
        heading3_block("🚧 Stuck Point"),
        paragraph_block(),
    ]


def append_solution_block(page_id, filepath, language):
    """Existing page, same Number + Language: append a divider then a fresh solution+notes section."""
    blocks = [divider_block()] + solution_and_notes_blocks(filepath, language)
    append_blocks(page_id, blocks)


def append_new_page_blocks(page_id, filepath, language, slug):
    """New page: problem description, solution, and empty notes sections."""
    blocks = get_leetcode_description(slug) if slug else []
    blocks += solution_and_notes_blocks(filepath, language)
    append_blocks(page_id, blocks)


def main():
    print(f"🔑 PROBLEMS_DB: len={len(PROBLEMS_DB)} {PROBLEMS_DB[:4]}...{PROBLEMS_DB[-4:]}")

    with open("changed_files.txt") as f:
        files = [line.strip() for line in f if line.strip()]

    for filepath in files:
        parsed = parse_filename(filepath)
        if not parsed:
            print(f"⚠️  Skipped: {filepath}")
            continue

        number, title, difficulty = parsed
        language = get_language(filepath)

        existing_page = find_existing_page(number, language)
        if existing_page:
            meta = parse_comments(filepath)
            update_properties = build_update_properties(meta, existing_page)
            if update_properties:
                update_page_properties(existing_page["id"], update_properties)
            append_solution_block(existing_page["id"], filepath, language)
            print(f"🔄 Updated: {number:04d}. {title} ({language})")
            continue

        remote = get_leetcode_metadata(number)
        if remote:
            title, difficulty = remote["title"], remote["difficulty"]
        topics = remote["topics"] if remote else []
        slug = remote["slug"] if remote else None

        meta = parse_comments(filepath)
        page_id = add_to_notion(number, title, difficulty, language, meta, topics)
        if page_id:
            append_new_page_blocks(page_id, filepath, language, slug)


if __name__ == "__main__":
    main()
