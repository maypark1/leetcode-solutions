import os
import re
import requests
from datetime import datetime, timedelta

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PROBLEMS_DB = os.environ["NOTION_PROBLEMS_DB"]

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
    """Fetch problem metadata from LeetCode GraphQL API"""
    url = "https://leetcode.com/graphql"
    slug_query = """
    query problemsetQuestionList($skip: Int!) {
        problemsetQuestionList: questionList(
            categorySlug: ""
            limit: 1
            skip: $skip
            filters: {}
        ) {
            questions: data {
                questionFrontendId