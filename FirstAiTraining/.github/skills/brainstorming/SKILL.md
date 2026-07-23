---
name: brainstorming
description: Phase 1 — Explore an idea through clarifying questions, propose approaches, present design, write a design spec. All questions via MCP ask_user.
---

# Brainstorming

Take an idea from exploration through a validated design spec. This is Phase 1 of the spec-driven-development workflow.

**Announce at start:** "Using brainstorming to explore this idea and create a design spec."

**Next phase:** After spec approval, load `../writing-plans/SKILL.md` to create the implementation plan.

## CRITICAL: How to Ask Questions

## Steps

You MUST create a task for each of these items and complete them in order:

1. **Explore project context** — check files, docs, recent changes
2. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
3. **Propose 2-3 approaches** — with trade-offs and your recommendation
4. **Present design** — in sections scaled to complexity, get user approval after each section 
5. **Write design doc** — save to `documentation/spec-driven/specs/YYYY-MM-DD-<topic>-design.md`
6. **Spec self-review** — check for placeholders, contradictions, ambiguity, scope
7. **User reviews written spec** — ask user to review before proceeding
8. **Transition to implementation** — load `../writing-plans/SKILL.md` and create the implementation plan

### Understanding the Idea

- Check out the current project state first (files, docs, recent changes)
- Before asking detailed questions, assess scope: if the request describes multiple independent subsystems, flag this immediately. Don't spend questions refining details of a project that needs to be decomposed first.
- If the project is too large for a single spec, help the user decompose into sub-projects: what are the independent pieces, how do they relate, what order should they be built? Then brainstorm the first sub-project through the normal design flow. Each sub-project gets its own spec → plan → implementation cycle.
- For appropriately-scoped projects, ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Only one question per message — if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

### Exploring Approaches

- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

### Presenting the Design

- Once you believe you understand what you're building, present the design
- Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced
- Ask after each section whether it looks right so far 
- Cover: architecture, components, data flow, error handling, testing
- Be ready to go back and clarify if something doesn't make sense

### Design for Isolation and Clarity

- Break the system into smaller units that each have one clear purpose, communicate through well-defined interfaces, and can be understood and tested independently
- For each unit, you should be able to answer: what does it do, how do you use it, and what does it depend on?
- Can someone understand what a unit does without reading its internals? Can you change the internals without breaking consumers? If not, the boundaries need work.
- Smaller, well-bounded units are easier to work with — you reason better about code you can hold in context at once, and your edits are more reliable when files are focused.

### Working in Existing Codebases

- Explore the current structure before proposing changes. Follow existing patterns.
- Where existing code has problems that affect the work, include targeted improvements as part of the design.
- Don't propose unrelated refactoring. Stay focused on what serves the current goal.

### After the Design

**Write the spec:**
Save the validated design to `documentation/spec-driven/specs/YYYY-MM-DD-<topic>-design.md`

**Spec Self-Review** — after writing the spec, look at it with fresh eyes:

- **Placeholder scan:** Any "TBD", "TODO", incomplete sections, or vague requirements? Fix them.
- **Internal consistency:** Do any sections contradict each other? Does the architecture match the feature descriptions?
- **Scope check:** Is this focused enough for a single implementation plan, or does it need decomposition?
- **Ambiguity check:** Could any requirement be interpreted two different ways? If so, pick one and make it explicit.

Fix any issues inline. No need to re-review — just fix and move on.

**User Review Gate:**

After the spec review passes, ask the user:

> "Spec written to `<path>`. Please review it and let me know if you want changes before we create the implementation plan."

Wait for the user's response. If they request changes, make them and re-run the spec review. Only proceed once the user approves.

**Transition:**

Once approved, load `../writing-plans/SKILL.md` and create the implementation plan.

## Key Principles

- **One question at a time** — don't overwhelm with multiple questions
- **Multiple choice preferred** — easier to answer than open-ended when possible
- **YAGNI ruthlessly** — remove unnecessary features from all designs
- **Explore alternatives** — always propose 2-3 approaches before settling
- **Incremental validation** — present design, get approval before moving on
- **Be flexible** — go back and clarify when something doesn't make sense
