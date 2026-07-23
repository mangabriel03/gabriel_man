# Requesting Code Review

Dispatch a code review subagent to catch issues before they cascade. The reviewer gets precisely crafted context — never your session's history.

## When to Request Review

**Mandatory:**
- After all tasks complete (final integration review using the template below)

**Note:** Per-task reviews use `spec-reviewer-prompt.md` and `code-quality-reviewer-prompt.md` directly — they are handled automatically by the subagent-driven development process.

**Optional:**
- When stuck (fresh perspective)
- Before a major refactor (baseline check)

## How to Request

Dispatch a code reviewer subagent with:

- **What was implemented** — summary of the work
- **Requirements** — what it should do (task text or spec reference)
- **Changes made** — high-level list of files created/modified
- **Description** — brief context for the reviewer

## Acting on Feedback

| Severity | Action |
|----------|--------|
| Critical | Fix immediately |
| Important | Fix before proceeding |
| Minor | Note for later |

If the reviewer is wrong, push back with technical reasoning. Don't blindly implement.

## Final Review

After all tasks are complete, dispatch a final review covering the entire implementation. This reviewer should:

- Check cross-task integration (do the pieces work together?)
- Verify the overall architecture matches the spec
- Look for inconsistencies between components
- Confirm nothing was missed

Template:

```
Agent tool (general-purpose):
  description: "Final code review for [feature name]"
  prompt: |
    You are reviewing the complete implementation of [feature name].

    ## Design Spec
    [Path to spec file — reviewer should read it]

    ## Implementation Plan
    [Path to plan file — reviewer should read it]

    ## Changes Made
    [High-level summary of all files created/modified across all tasks]

    ## Your Job

    This is a final integration review. Individual tasks have already
    passed spec compliance and code quality review. Your focus is:

    1. Do all the pieces work together?
    2. Does the implementation match the design spec?
    3. Are there inconsistencies between components?
    4. Is anything missing from the spec?
    5. Are there integration issues the per-task reviews couldn't catch?

    ## Report

    **Overall Assessment:** Approved | Needs changes
    **Integration issues:** [any cross-component problems]
    **Spec gaps:** [anything missing]
    **Strengths:** [what's done well]
```
