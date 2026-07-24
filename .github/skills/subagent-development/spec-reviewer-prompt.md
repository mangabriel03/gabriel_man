# Spec Compliance Reviewer Prompt Template

Use this template when dispatching a spec compliance reviewer subagent.

**Purpose:** Verify the implementer built what was requested — nothing more, nothing less.

```
Agent tool (general-purpose):
  description: "Review spec compliance for Task N"
  prompt: |
    You are reviewing whether an implementation matches its specification.

    ## What Was Requested

    [FULL TEXT of task requirements]

    ## What Implementer Claims They Built

    [From implementer's report]

    ## Changes Made

    [High-level summary of files created/modified]

    ## CRITICAL: Do Not Trust the Report

    The implementer's report may be incomplete, inaccurate, or optimistic.
    You MUST verify everything independently.

    **DO NOT:**
    - Take their word for what they implemented
    - Trust claims about completeness
    - Accept their interpretation of requirements

    **DO:**
    - Read the actual code they wrote
    - Compare implementation to requirements line by line
    - Check for missing pieces they claimed to implement
    - Look for extra features they didn't mention

    ## Your Job

    Read the code and verify:

    **Missing requirements:**
    - Did they implement everything requested?
    - Are there requirements they skipped?
    - Did they claim something works but didn't implement it?

    **Extra/unneeded work:**
    - Did they build things not requested?
    - Over-engineering or unnecessary features?

    **Misunderstandings:**
    - Did they interpret requirements differently than intended?
    - Did they solve the wrong problem?

    **Verify by reading code, not by trusting the report.**

    ## Report

    **Assessment:** Approved | Needs changes

    If approved, confirm what you verified.
    If needs changes, list what's missing or extra with file:line references.
```
