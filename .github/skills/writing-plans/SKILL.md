---
name: writing-plans
description: Phase 2 — Create a detailed implementation plan from a design spec, with file structure, task breakdown, and code snippets
---

# Writing Plans

Create a comprehensive implementation plan from a design spec. The plan assumes the implementing agent has zero context for the codebase. Document everything: which files to touch, code snippets, how to test. Break it into bite-sized tasks.

**Announce at start:** "Creating the implementation plan from the design spec."

**Save plans to:** `documentation/spec-driven/plans/YYYY-MM-DD-<feature-name>.md`

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

## Task Granularity

Each task should be a focused unit of work that a subagent can complete independently:

- Implement a single component or module
- Add a specific feature to an existing file
- Write tests for a specific component
- Wire up integration between components

Tasks should be completable in one subagent dispatch. If a task feels too large, break it down further.

## Plan Document Header

Every plan MUST start with this header:

```markdown
# [Feature Name] Implementation Plan

> **Execution:** Use subagent-driven development to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Design Spec:** [Path to the design spec this plan implements]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.ext`
- Modify: `exact/path/to/existing.ext` (lines ~X-Y)
- Test: `tests/exact/path/to/test.ext`

**Requirements:**
- [Specific requirement 1]
- [Specific requirement 2]

**Implementation:**

```language
// Key code snippets showing what to build
function example() {
    return result;
}
```

**Testing:**

```language
// Test code or description of what to verify
test('specific behavior', () => {
    expect(result).toBe(expected);
});
```

**Verification:**
- How to verify this task works (run command, check output, etc.)
````

## No Placeholders

Every task must contain the actual content an engineer needs. These are plan failures — never write them:

- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the content — the agent reads tasks independently)
- Steps that describe what to do without showing how
- References to types, functions, or methods not defined in any task

## Remember

- Exact file paths always
- Complete code in every task — if a task changes code, show the code
- Verification steps with expected output
- DRY, YAGNI

## Self-Review

After writing the complete plan, review it:

1. **Spec coverage:** Skim each requirement in the spec. Can you point to a task that implements it? List any gaps.
2. **Placeholder scan:** Search for red flags from the "No Placeholders" section. Fix them.
3. **Type consistency:** Do types, method signatures, and property names match across tasks?

Fix issues inline. If a spec requirement has no task, add the task.

## Handoff

After saving the plan:

> "Plan saved to `documentation/spec-driven/plans/<filename>.md`. Ready to begin subagent-driven implementation."

Then load `../subagent-development/SKILL.md` and begin execution.
