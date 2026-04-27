# Test and QA Plan

Use this alongside `docs/12_testing_qa_release_rollback.md`.

Required test suites:

1. Contract parse and schema validation.
2. Migration application and rollback smoke tests.
3. API route integration tests.
4. Offline/idempotency replay tests.
5. Temporal semantics tests.
6. Privacy and raw-log tests.
7. Workflow idempotency tests.
8. Context extraction evals.
9. Query grounding evals.
10. Accessibility and design QA.
11. Context capture policy gate tests.
12. Timing review flag lifecycle tests.
13. Optional profile migration smoke tests only when the matching profile is enabled.

A phase is not complete until its acceptance criteria are covered by automated tests or an explicit manual QA checklist.
