---
name: spec-driven-development
description: Orchestrates the full spec-driven development workflow — from brainstorming an idea through design spec, implementation plan, and subagent-driven implementation with reviews.
---

# Spec-Driven Development

You orchestrate structured software development through three phases:

1. **Brainstorming** — explore the idea, clarify requirements, write a design spec
2. **Writing Plans** — turn the spec into a detailed implementation plan
3. **Subagent Development** — execute the plan task-by-task with reviews

## Starting a New Project

When the user describes what they want to build:

1. Load and follow `../brainstorming/SKILL.md`
2. After the design spec is approved, load and follow `../writing-plans/SKILL.md`
3. After the plan is saved, load and follow `../subagent-development/SKILL.md`

Each phase skill contains detailed instructions. Follow them exactly.

## Resuming In-Progress Work

If the user wants to continue existing work:

- **Has a design spec but no plan?** Start at phase 2 — load `../writing-plans/SKILL.md`
- **Has a plan but hasn't started implementation?** Start at phase 3 — load `../subagent-development/SKILL.md`
- **Partway through implementation?** Read the plan, check what's done (git log, file state), and resume phase 3 from the next incomplete task

Ask the user which phase to start from if it's not obvious.

## Rules

- Always follow the phase skills — don't improvise the workflow
- One phase at a time, in order
- Each phase must complete before moving to the next
- If the user wants to skip a phase, confirm before proceeding
