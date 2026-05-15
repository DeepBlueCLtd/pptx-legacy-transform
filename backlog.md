# Backlog

Prioritized list of features, capabilities, and technical debt for the PPTX → DITA migration pipeline.

This document is the single source of truth for what's coming next. Items flow from idea → proposed → approved → specified → implementing → complete. Epics group related items into larger bodies of work.

## Scoring Criteria

| Dimension | Description | 1 | 3 | 5 |
|-----------|-------------|---|---|---|
| **Value** | Improvement to the migration pipeline or maintainer experience | Nice-to-have, cosmetic | Useful enhancement, improves workflow | Core capability, unblocks delivery |
| **Media** | Interest for write-up / demo | Internal, hard to visualize | Interesting technical story | Visual, demo-able, compelling narrative |
| **Autonomy** | Suitability for AI-assisted development | Needs significant human judgment / on-site testing | Some verification needed | Clear acceptance criteria, testable in CI |

**Total** = Value + Media + Autonomy (max 15)

### Complexity

| Level | Meaning | Model |
|-------|---------|-------|
| **Low** | Straightforward, limited scope | Haiku |
| **Medium** | Moderate scope, some design decisions | Sonnet |
| **High** | Significant scope, complex design | Opus |

## Workflow

| Status | Meaning | Trigger |
|--------|---------|---------|
| **needs-interview** | Quick capture, awaiting detailed requirements | `/idea --defer` |
| **proposed** | Item added, awaiting review | Human or agent adds |
| **approved** | Reviewed, ready for spec | Maintainer approves |
| **specified** | Spec created, linked below | `/speckit.specify` |
| **clarified** | Ambiguities resolved | `/speckit.clarify` |
| **planned** | Implementation plan ready | `/speckit.plan` |
| **tasked** | Tasks broken down | `/speckit.tasks` |
| **implementing** | Active development | `/speckit.implement` or `/bugfix` |
| **complete** | Done (row struck through) | Implementation merged |

### Bug Fast-Track

Bug items (`Category: Bug`) skip the full speckit pipeline — a bug fix restores existing specified behaviour and doesn't need a new spec.

```
approved → implementing → complete
```

Tests are still required; atomic commits and a PR with summary and test plan still apply.

## Epics

Large features broken down into multiple backlog items.

| ID | Title | Description | Status |
|----|-------|-------------|--------|
| E01 | Tooling & Developer Experience | Browser-based spec navigation, agent integration, and other improvements to the maintainer's workflow around this repo | proposed |

## Items

| ID | Title | Category | Epic | V | M | A | Total | Complexity | Status |
|----|-------|----------|------|---|---|---|-------|------------|--------|
| 001 | Introduce speckit-navigator SPA support — host a browser-based viewer ([DeepBlueCLtd/speckit-navigator](https://github.com/DeepBlueCLtd/speckit-navigator)) for the specs in this repo so reviewers can read spec.md, plan.md, tasks.md and related artifacts with markdown rendering and inline PR commenting, without cloning the repo | Tooling | E01 | 4 | 3 | 5 | 12 | Low | proposed |
