import os
import re
import requests
from datetime import datetime

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

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
        with open(filepath) as f:
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
    except:
        pass
    return meta

def get_language(filepath):
    ext_map = {
        "py": "Python", "cpp": "C++", "java": "Java",
        "js": "JavaScript", "ts": "TypeScript", "c": "C"
    }
    ext = filepath.rsplit(".", 1)[-1]
    return ext_map.get(ext, ext.upper())

def problem_exists(number):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(url, headers=HEADERS, json={
        "filter": {"property": "Number", "number": {"equals": number}}
    })
    return len(res.json().get("results", [])) > 0

def add_to_notion(number, title, difficulty, filepath, meta):
    url = "https://api.notion.com/v1/pages"
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    github_url = f"https://github.com/{repo}/blob/main/{filepath}"
    leetcode_url = f"https://leetcode.com/problems/{title.lower().replace(' ', '-')}/"
    language = get_language(filepath)

    properties = {
        "Problem":          {"title": [{"text": {"content": f"{number:04d}. {title}"}}]},
        "Number":           {"number": number},
        "LeetCode URL":     {"url": leetcode_url},
        "Date Solved":      {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        "Difficulty Level": {"select": {"name": difficulty}},
        "Language":         {"select": {"name": language}},
        "Problem Progress": {"select": {"name": "Completed"}},
    }

    if meta["topic"]:
        properties["Topic"] = {"multi_select": [{"name": t} for t in meta["topic"]]}
    if meta["time"]:
        properties["Time Complexity"] = {"select": {"name": meta["time"]}}
    if meta["space"]:
        properties["Space Complexity"] = {"multi_select": [{"name": meta["space"]}]}
    if meta["spent"]:
        properties["Time Spent"] = {"number": meta["spent"]}

    res = requests.post(url, headers=HEADERS, json={
        "parent": {"database_id": DATABASE_ID},
        "properties": properties
    })

    if res.status_code == 200:
        print(f"✅ Added: {number:04d}. {title} ({difficulty})")
    else:
        print(f"❌ Failed: {res.text}")

def main():
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

        meta = parse_comments(filepath)
        add_to_notion(number, title, difficulty, filepath, meta)

if __name__ == "__main__":
    main()