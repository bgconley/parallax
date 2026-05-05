# Phase 9 App Workflow And Action Contract

This document defines the real app behavior each current iOS surface must
provide. Figma labels may guide layout, but runtime content comes from user data,
local state, and canonical APIs.

## App Launch

| State | Required behavior |
| --- | --- |
| No local activity, no backend activity | Show create/select activity. No demo data. |
| Backend configured with activities | Fetch and show activity list. Select last cached activity if still present. |
| Backend unavailable | Show local cached activities and sync status. Allow local-first timing. |
| UAT seed activity provided | Resolve/create through canonical API/local cache, then select it. |

## Activity Create/Select

| UI action | Workflow |
| --- | --- |
| Type activity name | Local draft only. |
| Create activity | `POST /v1/activities` with mutation in connected mode, local cached activity plus pending create in offline mode. |
| Select activity | Load profile, checkpoints, preflight checks, resource dependencies, and local pending state for that activity. |
| Search/resolve activity | `POST /v1/activities/resolve`, read-only. Must not create aliases or activities. |

## Temporal Home

Temporal Home is a projection of the selected activity, current session, pending
review session, profile, preflight checks, query answer, and sync queue.

| Element | Runtime source | Action |
| --- | --- | --- |
| Current focus | Selected activity plus current session | Open current run or launcher. |
| Intelligence card | Profile/preflight/resource dependency/query state | Open relevant drawer, or no-data explanation if absent. |
| Timeline/list rows | Current run events, pending review, preflight checks, profile evidence, sync queue | Open run evidence, review, preflight, profile evidence, or sync queue. |
| Quick capture | User-entered note | Create annotation or queue local annotation. |
| Review action | Pending unreviewed session | Open timing review. Disabled/empty when none exists. |
| Ask time | User question | Open Ask About Time input or submit query. |

Temporal Home must not fabricate multiple activities such as laundry or pack
lunch unless those activities exist in the user's data.

## Timing Launcher

| Action | Workflow |
| --- | --- |
| Choose measurement mode | Updates local launch draft using canonical `MeasurementMode`. |
| Start timing | Create/ensure timing session, append `session_started`, navigate to session. |
| Not now | Dismiss launcher without mutation. |

Profile range copy is displayed only when `ActivityProfile.latest_stats` exists.
Otherwise use "No reviewed runs yet" or "Still calibrating" with no fake sample
count.

## Timing Session

| Action | Workflow |
| --- | --- |
| Pause | Append `session_paused`; timer stops active-time accumulation. |
| Resume | Append `session_resumed`; active-time accumulation resumes. |
| Finish | Complete session through `/v1/timing/sessions/{id}/complete` or queue completion. |
| Done with checkpoint | Append `checkpoint_completed` for real current checkpoint. |
| Skip checkpoint | Append `checkpoint_skipped` for real checkpoint. |
| Move checkpoint | Update local/remote checkpoint plan via scope/change or checkpoint template update. |
| Log friction | Open friction capture drawer with text input and span type choice. |
| Add note | Create annotation or queue local annotation. |
| Insights | Show real extracted events/review flags/profile evidence, or an empty state. |

## Context Capture

| Action | Workflow |
| --- | --- |
| Save note | `POST /v1/timing/sessions/{id}/annotations` when remote session exists, otherwise queue `annotation_captured`. |
| Voice/quick chip/manual | Preserve canonical `CaptureMethod` and `AnnotationInputMode`. |
| Cancel | Dismiss without mutation. |

Raw note text is privacy-sensitive and must not be logged outside the local/API
payload path.

## Friction And Extracted Evidence

| Action | Workflow |
| --- | --- |
| Confirm evidence | `/v1/timing/extracted-events/{event_id}/confirm` if backend ID exists; otherwise queue user-confirmed evidence. |
| Correct | `/v1/timing/extracted-events/{event_id}/correct` or queue `user_correction_applied`. |
| Not relevant | Confirm ignored/correct to `do_not_count`, or queue ignored correction. |
| Keep note only | Annotation/review decision with `query_evidence_only` or `do_not_count` as appropriate. |

The drawer must display the actual extracted/user-entered text and resource name.
If no extracted event exists, it becomes a friction capture form, not a sponge
confirmation screen.

## Checkpoint Setup

| Action | Workflow |
| --- | --- |
| Add/split/edit checkpoint | `PUT /v1/activities/{activity_id}/checkpoints` with full replacement list and mutation, or local pending equivalent. |
| Make optional | Update checkpoint template optional flag. |
| Start from checkpoint | Create/ensure timing session and append `checkpoint_started` for selected checkpoint. |

Checkpoint labels are optional helpers. Timing remains valid without them.

## Preflight

| Action | Workflow |
| --- | --- |
| Create preflight check | `POST /v1/activities/{activity_id}/preflight-checks`. |
| Keep active | `POST /v1/activities/{activity_id}/preflight-checks/{check_id}/decision` with `accept`. |
| Snooze | Same endpoint with `snooze` and `snoozed_until`. |
| Hide | Same endpoint with `hide`. |
| Retire | Same endpoint with `retire`. |
| View runs | Open Activity Profile/evidence scoped to the selected preflight/resource dependency. |

Preflight actions require a real activity ID and check ID. If no check exists,
show create/suggest empty state rather than using a demo UUID.

## Timing Review

| Action | Workflow |
| --- | --- |
| Save useful run | `/v1/timing/sessions/{id}/review` with `save_useful_run`, model inclusion, and scopes. |
| Mark unusual | Review with `mark_unusual`. |
| Active time only | Review with `active_only`. |
| Friction only | Review with `friction_only`. |
| Discard timing, keep note | `/v1/timing/sessions/{id}/discard` with `discard_timing_keep_note`. |
| Discard all | `/v1/timing/sessions/{id}/discard` with `discard_all`. |
| Trim forgotten timer | User correction based on real review flag evidence, then review/discard decision. |
| Timer kept running | Review/flag resolution without duration correction. |
| Not sure | Leave flag open/snoozed without corrupting timing facts. |

Review metrics and flags must derive from `TimingSession`, local run state,
`ActivityProfile`, and `TimingReviewFlag`. No fixed 42-minute/31-minute values.

## Activity Profile

| Element | Runtime source |
| --- | --- |
| Activity title | `Activity.display_name`. |
| Personal range | `ActivityProfile.latest_stats`. |
| Preflight checks | `ActivityProfile.preflight_checks` or list preflight endpoint. |
| Recent sessions | `ActivityProfile.recent_sessions` if present. |
| Limitations | `ActivityProfile.limitations`. |

No profile should claim sample size, confidence, or common friction without data.

## Ask About Time

| Action | Workflow |
| --- | --- |
| Submit question | `POST /v1/temporal/query` with mutation and `include_raw_quotes=false` by default. |
| Refresh pending answer | `GET /v1/temporal/query/{answer_id}`. |
| View evidence | Display `TemporalQueryAnswer.evidence` summaries and limitations. |
| Ask another | Reset input and preserve prior answer in local recent questions if desired. |

If offline, queue a clear "question saved, answer needs backend" intent. Do not
display a fabricated answer.

## Privacy

| Action | Workflow |
| --- | --- |
| View capture policy | `GET /v1/privacy/context-capture-policy` when available. |
| Update capture policy | `PATCH /v1/privacy/context-capture-policy` with mutation. |
| Raw quote setting for Ask | Defaults false unless the user explicitly opts in. |

## Offline And Sync

| Action | Workflow |
| --- | --- |
| View queue | Show actual pending timing events, preflight decisions, annotations, and queued creates. |
| Retry sync | Run pending sync with stable idempotency keys. |
| Conflict | Preserve local queue, show structured conflict, and avoid deleting unrelated queued mutations. |

Pending sync must map local IDs to remote IDs before uploading dependent
sessions, events, annotations, review decisions, and preflight decisions.
