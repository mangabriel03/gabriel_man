# Receiving Code Review

How to handle code review feedback with technical rigor — verify before implementing, push back when wrong.

## The Response Pattern

```
1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate the requirement (or ask for clarification)
3. VERIFY: Check against the actual codebase
4. EVALUATE: Is it technically sound for THIS codebase?
5. RESPOND: Technical acknowledgment or reasoned pushback
6. IMPLEMENT: One item at a time, verify each
```

## Handling Unclear Feedback

If any item is unclear, STOP — do not implement anything yet. Ask for clarification on unclear items first. Items may be related; partial understanding leads to wrong implementations.

## Implementation Order

For multi-item feedback:

1. Clarify anything unclear FIRST
2. Then implement in order:
   - Blocking issues (bugs, security)
   - Simple fixes (typos, imports)
   - Complex fixes (refactoring, logic)
3. Verify each fix individually
4. Check for regressions

## When to Push Back

Push back when:
- Suggestion breaks existing functionality
- Reviewer lacks full context
- Violates YAGNI (unused feature)
- Technically incorrect for this stack
- Conflicts with the design spec

**How:** Use technical reasoning. Reference working code. Ask specific questions.

## Acknowledging Correct Feedback

When feedback IS correct — just fix it. The code shows you heard the feedback.

- "Fixed. [Brief description of what changed]"
- "Good catch — [specific issue]. Fixed in [location]."

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Blind implementation | Verify against codebase first |
| Batch without testing | One at a time, verify each |
| Assuming reviewer is right | Check if it breaks things |
| Avoiding pushback | Technical correctness matters |
| Partial implementation | Clarify all items first |
