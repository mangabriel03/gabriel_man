---
name: subagent-development
description: Phase 3 — Execute an implementation plan by dispatching fresh subagents per task, with two-stage review (spec compliance + code quality) after each
---

# Subagent-Driven Development

Execute an implementation plan by dispatching a fresh subagent per task, with two-stage review after each: spec compliance first, then code quality.

**Why subagents:** Fresh context per task prevents confusion. You construct exactly what each subagent needs. This preserves your own context for coordination.

**Announce at start:** "Executing the implementation plan with subagent-driven development."

## The Process

```
For each task in the plan:
  1. Dispatch implementer subagent        → ./implementer-prompt.md
  2. Handle questions if any
  3. Dispatch spec reviewer subagent      → ./spec-reviewer-prompt.md
  4. Fix issues if any (re-dispatch implementer)
  5. Dispatch code quality reviewer       → ./code-quality-reviewer-prompt.md
  6. Fix issues if any (re-dispatch implementer)
  7. Mark task complete

After all tasks:
  Dispatch final review (./requesting-code-review.md) for entire implementation
  Report completion to user
```

## Setup

1. Read the plan file once and extract all tasks with their full text
2. Create a TodoWrite entry for each task
3. Note any cross-task dependencies or shared context

## Per-Task Execution

### 1. Dispatch Implementer

Use the Agent tool with the template from `./implementer-prompt.md`. Include:

- **Full task text** — paste it, don't make the subagent read the plan file
- **Context** — where this task fits, what previous tasks built, any relevant file content
- **Changes so far** — high-level summary of what previous tasks implemented (files created/modified and why)

### 2. Handle Implementer Response

| Status | Action |
|--------|--------|
| **DONE** | Proceed to spec review |
| **DONE_WITH_CONCERNS** | Read concerns. If correctness/scope issue, address first. If observations, note and proceed. |
| **NEEDS_CONTEXT** | Provide missing info, re-dispatch |
| **BLOCKED** | Provide more context, use more capable model, break task smaller, or escalate to user |

### 3. Spec Compliance Review

Dispatch a spec reviewer subagent (general-purpose) using `./spec-reviewer-prompt.md`. Provide:

- Full task requirements
- What the implementer claims they built
- High-level summary of changes made

If issues found → re-dispatch implementer to fix → re-review until clean.

### 4. Code Quality Review

Dispatch a code quality reviewer subagent (`spec-driven:code-reviewer` or general-purpose) using `./code-quality-reviewer-prompt.md`. Provide:

- What was implemented
- The task requirements
- High-level summary of changes made

If issues found → re-dispatch implementer to fix → re-review until clean.

### Handling Review Feedback

When acting on reviewer feedback (spec or code quality), follow the guidance in `./receiving-code-review.md`:

- Verify feedback against the actual codebase before implementing
- Clarify unclear items before making changes
- Push back with technical reasoning when feedback is incorrect
- Implement fixes one at a time, verifying each

### 5. Mark Complete

Update TodoWrite. Move to next task.

## After All Tasks

Dispatch a final code review (using `./requesting-code-review.md`) covering the entire implementation. This catches cross-task integration issues.

Then report to user:

> "Implementation complete. All tasks implemented and reviewed. Summary: [what was built]"

## After Completion

Once the implementation is complete and the final review passes, decide on next steps with the user:

- **Commit** the changes if working on the main branch
- **Create a PR** if working on a feature branch
- **Run the full test suite** if not already covered by per-task verification

## Model Selection

- **Simple tasks** (1-2 files, clear spec): `haiku`
- **Multi-file integration**: `sonnet`
- **Architecture/design/review**: `opus`

## Rules

- Never skip reviews (spec compliance OR code quality)
- Never proceed with unfixed issues
- Dispatch implementers sequentially by default. Parallel dispatch is allowed ONLY when tasks touch completely independent files with no shared state.
- Never make the subagent read the plan file — provide full text
- Never ignore subagent questions — answer before they proceed
- Always spec review before code quality review
- Always re-review after fixes
