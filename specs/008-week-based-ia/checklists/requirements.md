# Spec Quality Checklist — Week-Based IA

- [x] Every functional requirement is testable and observable.
- [x] User stories are independently testable and prioritised.
- [x] Success criteria are measurable (SC-001…SC-006).
- [x] Edge cases enumerated (no week token, Final Assessment, no-collision week,
      re-run idempotency, number > running max, bare-int outside 1–4).
- [x] Backwards compatibility stated: `target_gram_id` optional/inert (FR-011).
- [x] Determinism stated: fixed renumber order (FR-006), idempotent re-run
      (FR-012).
- [x] Out-of-scope boundaries drawn (week selection is an analyst decision;
      non-main layout unchanged; no global renumbering; `gram_id` immutable).
- [x] Contracts authoritative: `csv-target-gram-id.md`, `week-chapter-mapping.md`.
- [x] No new runtime/test dependencies; Python 3.9 floor respected.
