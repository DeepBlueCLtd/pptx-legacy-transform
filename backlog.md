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
| 002 | WAV link href as a first-class CSV column — split URL and label across `display_text` (label) and `link_href` (URI) so the generator never has to guess from `display_text.endswith('.wav')`. Solves the silent-corruption failure mode where the WAV stub topic's `xref href` was being populated from the human-readable label. Touches `extract_to_csv.py`, `generate_dita.py`, fixtures, and contracts. **Resolved by this PR — leaving here for traceability.** | Bug | — | 5 | 1 | 5 | 11 | Low | complete |
| 003 | CSV round-trip regression test + README Excel-edit guidance — add a byte-level write→read→rewrite test asserting `csv-schema.md`'s round-trip invariant under the writer's exact `utf-8-sig` + CRLF + `QUOTE_MINIMAL` settings, and document Excel save-as risks (BOM stripped, line endings flipped, leading zeros coerced) in the README troubleshooting section. **Resolved by this PR — leaving here for traceability.** | Tech debt | — | 3 | 1 | 5 | 9 | Low | complete |
| 004 | WAV-row extractor test against the mock generator's `.wav` placeholders — extend `test_extract_to_csv.py` so that once `extract_grams_from_slide` is implemented post-handover, the WAV-row construction path (`gram_to_rows` for `.wav` hrefs) is exercised end-to-end against `mock_pptx.py`'s configured WAV grams, not just via a hand-built `GramPlaceholder` (the latter is what item 002 added). Depends on: implementing the shape-grouping stub (R1 / FR-015), which requires real-instructor PPTX introspection findings. | Test | — | 3 | 2 | 4 | 9 | Medium | proposed |
| 005 | `topic_filename` collision check at CSV-load time — `generate_dita.py:read_csv` currently trusts that the `(publication, chapter, gram_id, topic_type, sequence)` identity tuple yields unique `topic_filename`s. If a hand-edited CSV duplicates the tuple, the second write silently overwrites the first (`csv-schema.md` §"Row identity" says "should never happen"). Add a load-time check that emits ERROR + aborts on collision, so the failure surfaces in `generate.log` rather than as missing output. | Tech debt | — | 4 | 1 | 5 | 10 | Low | proposed |
| 006 | Refresh stale `Branch` headers in `spec.md` and `plan.md` — both files reference `claude/document-pptx-spec-xQZC8`, a branch that no longer exists. Cosmetic doc-rot fix; either update to the merged-state placeholder (e.g. `main`) or remove the field. | Tech debt | — | 1 | 1 | 5 | 7 | Low | proposed |
| 007 | Realign pipeline with the audited Lofar → `.glc` → `.png`/`.jpg`/`.wav` model — the source docs originally said "Lofar links point to `.glc` files, a small number may point to `.wav` instead", and the pipeline was built around that. The audited corpus (1,004/1,004 `Lofar` text-run hyperlinks) shows **every** Lofar link targets a `.glc`; the 18% `.wav` case is always one indirection deeper, inside the `.glc`'s `data_source/filename`. **Resolved** — the generator already dispatches on the inner asset's extension per the new §1.3 contract (`.png`/`.jpg` → inline GramFrame; `.wav` → `<xref>` to the `.glc` with both `.glc` + `.wav` copied alongside the topic; anything else → skipped); the `wav_treatment` author-decision branch, `emit_wav_stub_topic`, the `is_wav_link` dispatch, the broken `<image href="*.wav">` emission, and the mock's `_emit_wav_link_grams` direct-`.wav` Lofar runs are all gone. Final cleanup on the extraction side: `extract_to_csv.extract_grams_from_slide`'s Lofar filter is tightened to `.glc`-only and warns loudly on anything else (was warning only on `.wav`), and the matching mock-corpus test (`test_lofar_count_per_gram_in_1_to_4_range`) asserts the tighter `.glc`-only target. `wav_treatment` is retained in `CSV_COLUMNS` for round-trip compatibility but is otherwise dead. | Tech debt | — | 4 | 2 | 4 | 10 | Medium | complete |
