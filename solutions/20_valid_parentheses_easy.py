#
# @lc app=leetcode id=20 lang=python3
#
# [20] Valid Parentheses
#
# time: O(n)
# space: O(n)
# spent: 16

# @lc code=start
class Solution:
    def isValid(self, s: str) -> bool:
        stack = []
        mapping = {')': '(', '}': '{', ']': '['}
        for char in s:
            if char in mapping:
                top = stack.pop() if stack else '#'
                if mapping[char] != top:
                    return False
            else:
                stack.append(char)
        return not stack
# @lc code=end