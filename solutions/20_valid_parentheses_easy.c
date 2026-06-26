//
// @lc app=leetcode id=20 lang=c
//
// [20] Valid Parentheses
//
// time: O(n)
// space: O(n)
// spent: 20
// runtime: 0ms
// memory: 8.1MB

// @lc code=start
bool isValid(char* s) {
    int len = strlen(s);
    char stack[len];
    int top = -1;
    
    for (int i = 0; i < len; i++) {
        if (s[i] == '(' || s[i] == '{' || s[i] == '[') {
            stack[++top] = s[i];
        } else {
            if (top == -1) return false;
            if (s[i] == ')' && stack[top] != '(') return false;
            if (s[i] == '}' && stack[top] != '{') return false;
            if (s[i] == ']' && stack[top] != '[') return false;
            top--;
        }
    }
    return top == -1;
    sdfsdf
    sadasdfa
    asdfasd
}
// @lc code=end