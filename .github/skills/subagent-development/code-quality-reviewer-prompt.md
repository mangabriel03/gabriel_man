# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify the implementation is clean, tested, and maintainable.

**Only dispatch after spec compliance review passes.**

```
Agent tool (spec-driven:code-reviewer or general-purpose):
  description: "Review code quality for Task N"
  prompt: |
    You are reviewing code quality for a task implementation.

    ## What Was Implemented

    [From implementer's report]

    ## Task Requirements

    [Full task text for context]

    ## Changes Made

    [High-level summary of files created/modified]

    ## Your Job

    Read the actual code and evaluate:

    **Correctness:**
    - Does the code actually work as intended?
    - Are there logic errors or edge cases?

    **Clarity:**
    - Are names clear and accurate?
    - Can you understand each unit without reading its internals?
    - Is the code self-documenting?

    **Decomposition:**
    - Does each file have one clear responsibility?
    - Are units small enough to reason about independently?
    - Are interfaces well-defined?

    **Testing:**
    - Do tests verify real behavior (not just mock behavior)?
    - Are tests comprehensive?
    - Can tests break if the implementation breaks?

    **Simplicity:**
    - Is there unnecessary complexity?
    - Any over-engineering or premature abstractions?
    - Could anything be simpler?

    ## Report Format

    **Strengths:** [What's done well]

    **Issues:**
    - Critical: [Must fix — bugs, security, data loss]
    - Important: [Should fix — maintainability, clarity]
    - Minor: [Nice to fix — style, naming]

    **Assessment:** Approved | Needs changes
```
