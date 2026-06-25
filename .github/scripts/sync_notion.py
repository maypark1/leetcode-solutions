import os
import re
import requests
from datetime import datetime

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
    """Fetch the canonical title/difficulty/topics for a problem from
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
            "difficulty": q["difficulty"],
            "topics": [t["name"] for t in q["topicTags"]],
        }
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return None


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
    meta = {"topic": [], "time": "", "space": "", "spent": None}
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("#"):
                    break
                if "topic:" in line:
                    meta["topic"] = [t.strip() for t in line.split("topic:")[1].split(",")]
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


def problem_exists(number):
    url = f"https://api.notion.com/v1/databases/{PROBLEMS_DB}/query"
    res = requests.post(url, headers=HEADERS, json={
        "filter": {"property": "Number", "number": {"equals": number}}
    })
    if res.status_code != 200:
        print(f"⚠️  Lookup failed for #{number}: {res.text}")
        return False
    return len(res.json().get("results", [])) > 0


def add_to_notion(number, title, difficulty, filepath, meta, topics=None):
    url = "https://api.notion.com/v1/pages"
    leetcode_url = f"https://leetcode.com/problems/{title.lower().replace(' ', '-')}/"
    language = get_language(filepath)
    all_topics = sorted(set((topics or []) + meta["topic"]))
    lists = get_lists(number)

    properties = {
        "Problem":          {"title": [{"text": {"content": f"{number:04d}. {title}"}}]},
        "Number":           {"number": number},
        "LeetCode URL":     {"url": leetcode_url},
        "Date Solved":      {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        "Difficulty Level": {"select": {"name": difficulty}},
        "Language":         {"select": {"name": language}},
        "Problem Progress": {"select": {"name": "Completed"}},
    }

    if all_topics:
        properties["Topic"] = {"multi_select": [{"name": t} for t in all_topics]}
    if lists:
        properties["Lists"] = {"multi_select": [{"name": l} for l in lists]}
    if meta["time"]:
        properties["Time Complexity"] = {"select": {"name": meta["time"]}}
    if meta["space"]:
        properties["Space Complexity"] = {"multi_select": [{"name": meta["space"]}]}
    if meta["spent"]:
        properties["Time Spent"] = {"number": meta["spent"]}

    res = requests.post(url, headers=HEADERS, json={
        "parent": {"database_id": PROBLEMS_DB},
        "properties": properties
    })

    if res.status_code == 200:
        print(f"✅ Added: {number:04d}. {title} ({difficulty})")
    else:
        print(f"❌ Failed: {res.text}")


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
        if problem_exists(number):
            print(f"⏭️  Already exists: {number:04d}. {title}")
            continue

        remote = get_leetcode_metadata(number)
        if remote:
            title, difficulty = remote["title"], remote["difficulty"]
        topics = remote["topics"] if remote else []

        meta = parse_comments(filepath)
        add_to_notion(number, title, difficulty, filepath, meta, topics)


if __name__ == "__main__":
    main()
