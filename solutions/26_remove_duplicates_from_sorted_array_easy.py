#
# @lc app=leetcode id=26 lang=python3
#
# [26] Remove Duplicates from Sorted Array
#
# time: O(n)
# space: O(1)
# spent: 15
# runtime: 88ms
# memory: 17.2MB

# @lc code=start
class Solution:
    def removeDuplicates(self, nums: list) -> int:
        k = 1
        for i in range(1, len(nums)):
            if nums[i] != nums[i-1]:
                nums[k] = nums[i]
                k += 1
        return k
# @lc code=end