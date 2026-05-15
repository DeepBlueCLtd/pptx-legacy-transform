---
description: Review a plan thoroughly before task generation. Challenges scope, reviews architecture/design/tests/performance against existing code and constitution, with opinionated recommendations.
handoffs:
  - label: Create Tasks
    agent: speckit.tasks
    prompt: Break the plan into tasks
    send: true
  - label: Revise Plan
    agent: speckit.plan
    prompt: Revise the plan based on review findings
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Review the implementation plan before committing to task generation. This is a strategic review gate that challenges scope, examines architectural decisions against existing code and the constitution, and surfaces issues while they're still cheap to fix.

**This command is read-only.** It does not modify any files. It produces a structured review with opinionated recommendations and asks the user for decisions at each stage.

## Allowed Tools

This review uses only: Read, Grep, Glob, Bash (read-only commands like `git log`, `git diff`, `find`), AskUserQuestion.

## Priority Hierarchy

If running low on context or the user asks to compress: Step 0 > Test coverage diagram > Opinionated recommendations > Everything else. Never skip Step 0 or the test coverage diagram.

## Engineering Preferences (guide your recommendations)

* **Constitution is law** — constitution principles override all other considerations. Flag violations as CRITICAL.
* **DRY is important** — flag repetition aggressively across both the plan and existing code it touches.
* **Well-tested code is non-negotiable** — our constitution mandates schema tests, unit tests, and integration tests.
* **Engineered enough** — not under-engineered (fragile, hacky) and not over-engineered (premature abstraction, unnecessary complexity). Pre-release freedom (Article XIV) means we can move fast, but not recklessly.
* **Bias toward explicit over clever** — strict type safety (Article XV) reinforces this.
* **Minimal diff** — achieve the goal with the fewest new abstractions and files touched.
* **Offline-first always** — every design decision must work without network (Article I).
* **Thick services, thin frontends** — services return data only; frontends never persist (Article IV).

## Execution Steps

### 1. Initialize Review Context

Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS.
For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

Derive absolute paths:

- SPEC = FEATURE_DIR/spec.md
- PLAN = FEATURE_DIR/plan.md
- RESEARCH = FEATURE_DIR/research.md (if available)
- DATA_MODEL = FEATURE_DIR/data-model.md (if available)
- CONTRACTS = FEATURE_DIR/contracts/ (if available)

Abort with an error message if plan.md is missing (instruct user to run `/speckit.plan` first).

### 2. Load Artifacts

Read all available design artifacts:

1. **spec.md** — user stories, requirements, success criteria
2. **plan.md** — technical context, architecture, project structure, constitution check
3. **research.md** — design decisions and alternatives (if exists)
4. **data-model.md** — entities, relationships, validation rules (if exists)
5. **contracts/** — API definitions (if exists)
6. **`.specify/memory/constitution.md`** — immutable development principles

### 3. Survey Existing Code

**This step is critical.** The plan does not exist in a vacuum — it integrates with or modifies existing code.

1. **Identify files the plan touches**: Read plan.md's Project Structure section and extract all source file paths, directories, and modules mentioned.

2. **Search for existing implementations**: For each entity, service, or module proposed in the plan:
   - Glob for files with matching names in the repository
   - Grep for key type names, function names, and class names
   - Note what already exists vs what the plan proposes to create

3. **Check git history** for the feature branch:
   ```
   git log --oneline -20
   git log --oneline main..HEAD (if not on main)
   ```
   If prior commits suggest a previous review cycle (review-driven refactors, reverted changes), note what changed and be more aggressive reviewing those areas.

4. **Record findings** for use in Step 0 and the "What Already Exists" output.

### 4. Step 0 — Scope Challenge

**BEFORE reviewing anything else**, answer these questions:

1. **What existing code already partially or fully solves each sub-problem?** Reference specific files and functions found in Step 3. Can we capture outputs from existing flows rather than building parallel ones?

2. **What is the minimum set of changes that achieves the stated goal?** Flag any work in the plan that could be deferred without blocking the core objective. Be ruthless about scope creep.

3. **Complexity check**: Count the files the plan creates or modifies, and the new types/services/classes it introduces. If the plan touches more than 8 files or introduces more than 2 new services/classes, treat that as a smell and challenge whether the same goal can be achieved with fewer moving parts.

4. **Constitution compliance pre-check**: Does the plan's Constitution Check section in plan.md correctly identify all relevant articles? Are there violations it missed?

Then use AskUserQuestion to present your findings and ask the user to choose one of three review modes:

**Option A — SCOPE REDUCTION**: The plan is overbuilt. You will propose a minimal version that achieves the core goal, then review that reduced plan.

**Option B — FULL REVIEW**: Work through interactively, one section at a time (Architecture → Design Quality → Tests → Performance) with at most 4 top issues per section.

**Option C — COMPRESSED REVIEW**: Step 0 + one combined pass covering all 4 sections. For each section, pick the single most important issue. Present as a single numbered list + mandatory test coverage diagram + completion summary. One AskUserQuestion round at the end.

**Critical: If the user does NOT select SCOPE REDUCTION, respect that decision fully.** Your job becomes making the plan they chose succeed, not continuing to lobby for a smaller plan. Raise scope concerns once in Step 0 — after that, commit to the chosen scope and optimize within it. Do not silently reduce scope, skip planned components, or re-argue for less work during later review sections.

### 5. Review Sections (after scope is agreed)

#### 5A. Architecture Review

Evaluate the plan against the codebase and constitution:

* **Constitution alignment**: Check every architectural decision against relevant articles. Pay special attention to:
  - Article I (offline-first): Does the design work without network?
  - Article II (schema integrity): Are new data structures derived from LinkML schemas?
  - Article IV (thick services, thin frontends): Do services return data only?
  - Article V (extensibility): Could a broken extension crash core functionality?
  - Article XV (strict type safety): Any `Any`/`any` in proposed types?

* **Component boundaries and coupling**: Review the dependency graph between proposed and existing modules. Flag circular dependencies or tight coupling.

* **Data flow patterns**: Trace data from input to storage to output. Identify potential bottlenecks.

* **Integration with existing code**: For each touchpoint with existing code (found in Step 3), assess whether the integration approach is clean or introduces coupling.

* **Failure scenarios**: For each new codepath or integration point, describe one realistic production failure scenario and whether the plan accounts for it.

* **Diagrams**: Note whether key flows deserve ASCII diagrams in the plan or in code comments.

**STOP.** You MUST call AskUserQuestion NOW with your findings from this section. Do NOT proceed to the next section until the user responds.

#### 5B. Design Quality Review

Evaluate the proposed design in data-model.md, contracts/, and plan.md:

* **DRY violations**: Check proposed types and interfaces against existing ones. Flag duplication aggressively — especially types that overlap with schema-generated types.

* **Error handling patterns**: Are failure modes explicit? Does the design honour "no silent failures" (Article I)?

* **Over/under-engineering**: Is the design proportional to the problem? Flag premature abstractions (unnecessary base classes, overly generic interfaces) and missing structure (god objects, mixed concerns).

* **Schema compliance**: Do proposed data models conform to or extend the LinkML master schemas? Would they pass schema adherence tests (Article II)?

* **Existing code impact**: For files the plan modifies (found in Step 3), review whether the proposed changes conflict with existing patterns, break existing tests, or introduce inconsistencies.

* **Stale documentation**: If the plan modifies code that has inline comments or diagrams, note that these will need updating.

**STOP.** You MUST call AskUserQuestion NOW with your findings from this section. Do NOT proceed to the next section until the user responds.

#### 5C. Test Review

Build a diagram (ASCII art) of all new:
- User journeys (from spec.md user stories)
- Data flows (from data-model.md and contracts/)
- Codepaths and branching (from plan.md architecture)

For each item in the diagram, verify:

1. **Schema tests**: Does the plan account for golden fixtures, round-trip tests, and schema comparison (Article II)?
2. **Unit tests**: Are proposed services covered (Article VI)?
3. **Integration tests**: Are end-to-end paths (load → transform → store) tested (Article VI)?
4. **Acceptance criteria**: Can every acceptance scenario from spec.md be mapped to a testable assertion?
5. **Existing test impact**: Will the proposed changes break any existing tests? Grep for test files that reference modified modules.

Flag any new codepath that has no planned test coverage.

**STOP.** You MUST call AskUserQuestion NOW with your findings from this section. Do NOT proceed to the next section until the user responds.

#### 5D. Performance Review

Evaluate with our domain constraints in mind:

* **Offline data volumes**: Maritime track data can be large. How does the design handle datasets with 100k+ position reports?
* **File I/O patterns**: Does the design read files efficiently? Watch for full-file reads when streaming would suffice.
* **Memory usage**: Are large collections held in memory unnecessarily?
* **STAC catalog operations**: Are catalog reads/writes efficient? Watch for N+1 patterns when traversing STAC items.
* **Startup impact**: Does the feature add measurable delay to application startup (relevant for VS Code extension and Electron app)?

**STOP.** You MUST call AskUserQuestion NOW with your findings from this section. Do NOT proceed to the next section until the user responds.

## For Each Issue Found

For every specific issue (bug, smell, design concern, or risk):

1. **Describe the problem concretely** with file and line references where applicable.
2. **Present 2–3 options**, including "do nothing" where reasonable.
3. For each option, state in one line: effort, risk, and maintenance burden.
4. **Lead with your recommendation.** State it as a directive: "Do B. Here's why:" — not "Option B might be worth considering." Be opinionated.
5. **Map the reasoning to a specific engineering preference or constitution article.** One sentence connecting your recommendation to a principle.
6. **AskUserQuestion format**: Start with "We recommend [LETTER]: [one-line reason]" then list all options. Label with issue NUMBER + option LETTER (e.g., "3A", "3B").

## Required Outputs

### "NOT in scope" Section

Every review MUST produce a "NOT in scope" section listing work that was considered and explicitly deferred, with a one-line rationale for each item.

### "What Already Exists" Section

List existing code, modules, and flows (found in Step 3) that already partially solve sub-problems in this plan. State whether the plan reuses them or unnecessarily rebuilds them.

### Deferred Items for BACKLOG.md

Any deferred work that is genuinely valuable MUST be written up as potential BACKLOG.md entries. Each entry needs:

* **What**: One-line description of the work
* **Why**: The concrete problem it solves or value it unlocks
* **Context**: Enough detail that someone picking this up in 3 months understands the motivation
* **Depends on / blocked by**: Any prerequisites

Do NOT write vague bullet points. Ask the user which deferred items they want captured before proposing backlog entries.

### Diagrams

The review should use ASCII diagrams for any non-trivial data flow, state machine, or processing pipeline being discussed. Additionally, identify which files in the implementation should get inline ASCII diagram comments — particularly:
- Models with complex state transitions
- Services with multi-step pipelines
- Integration points with non-obvious data flow

### Failure Modes

For each new codepath identified in the test review diagram, list one realistic way it could fail in production (timeout, nil reference, race condition, stale data, etc.) and whether:

1. A test would cover that failure
2. Error handling exists for it
3. The user would see a clear error or a silent failure

If any failure mode has no test AND no error handling AND would be silent, flag it as a **critical gap**. Our constitution (Article I.3) forbids silent failures.

### Completion Summary

At the end of the review, display this summary:

```
## Review Summary

- Step 0: Scope Challenge (user chose: ___)
- Architecture Review: ___ issues found
- Design Quality Review: ___ issues found
- Test Review: diagram produced, ___ gaps identified
- Performance Review: ___ issues found
- NOT in scope: written
- What already exists: written
- Deferred items: ___ items proposed to user
- Failure modes: ___ critical gaps flagged
- Constitution violations: ___ found

### Unresolved Decisions

[List any AskUserQuestion decisions the user did not respond to or skipped]
These may cause problems during implementation if not addressed.
```

## Formatting Rules

* NUMBER issues (1, 2, 3...) and give LETTERS for options (A, B, C...).
* When using AskUserQuestion, label each option with issue NUMBER and option LETTER.
* Recommended option is always listed first.
* Keep each option to one sentence max.
* After each review section, pause and ask for feedback before moving on.

## Unresolved Decisions

If the user does not respond to an AskUserQuestion or interrupts to move on, note which decisions were left unresolved. At the end of the review, list these as "Unresolved decisions that may bite you later" — never silently default to an option.

## Context

$ARGUMENTS
