# Release Gate Checklist

## Developer prototype

- [ ] Migrations 0001–0006 and 0008 apply.
- [ ] Activity API works.
- [ ] Timing session API works.
- [ ] Event append idempotency works.
- [ ] Review API works.
- [ ] Activity Profile returns first stats.
- [ ] Raw context logging disabled.

## Private alpha

- [ ] Context annotations work offline.
- [ ] Context capture policy gates optional sensor capture.
- [ ] Timing review flags do not mutate source timing facts.
- [ ] Extraction workflow validates schemas.
- [ ] Correction workflow exists.
- [ ] Privacy settings exist.
- [ ] Export/delete workflow exists.
- [ ] Backup/restore tested.
- [ ] Accessibility checklist passes.
- [ ] Cross-user isolation tests pass.

## Expanded alpha

- [ ] Grounded Ask works with evidence bundles.
- [ ] Query grounding evals pass.
- [ ] Optional retrieval profile measured.
- [ ] Runbooks exercised.
