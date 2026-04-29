from __future__ import annotations

INSERT_SESSION_SQL = """
insert into timing_session (
  user_id, activity_id, client_session_id, source_device_id, mode,
  status, work_mode, actor_mode, intended_start_at,
  user_pre_estimate_seconds, offline_created
)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
returning id, user_id, activity_id, client_session_id, source_device_id, mode, status, work_mode,
  actor_mode, intended_start_at, started_at, completed_at, active_seconds, wall_seconds,
  setup_seconds, detour_seconds, interruption_seconds, waiting_seconds, side_quest_seconds,
  start_latency_seconds, transition_seconds, run_quality, model_inclusion,
  needs_timeline_recompute
"""

INSERT_EVENT_SQL = """
insert into timing_event (
  user_id, session_id, event_type, client_time, timer_elapsed_seconds,
  timer_active_seconds, client_sequence, client_mutation_id,
  client_device_id, idempotency_key, capture_context_snapshot_id,
  capture_context_snapshot_ref, payload
)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
returning id, user_id, session_id, event_type, client_time, server_time, timer_elapsed_seconds,
  timer_active_seconds, client_sequence, client_mutation_id, client_device_id,
  idempotency_key, capture_context_snapshot_id, capture_context_snapshot_ref, payload
"""

LOAD_SESSION_SQL = """
select id, user_id, activity_id, client_session_id, source_device_id, mode, status, work_mode,
  actor_mode, intended_start_at, started_at, completed_at, active_seconds, wall_seconds,
  setup_seconds, detour_seconds, interruption_seconds, waiting_seconds, side_quest_seconds,
  start_latency_seconds, transition_seconds, run_quality, model_inclusion,
  needs_timeline_recompute
from timing_session
where user_id = %s and id = %s
"""

LOAD_EVENTS_SQL = """
select id, user_id, session_id, event_type, client_time, server_time, timer_elapsed_seconds,
  timer_active_seconds, client_sequence, client_mutation_id, client_device_id,
  idempotency_key, capture_context_snapshot_id, capture_context_snapshot_ref, payload
from timing_event
where user_id = %s and session_id = %s
order by server_time, id
"""

LOAD_SPANS_SQL = """
select id, user_id, session_id, checkpoint_run_id, span_type, friction_category,
  started_at, ended_at, duration_seconds, count_policy, count_in_wall_time,
  count_in_active_time, model_update_scopes, linked_annotation_id,
  linked_extracted_event_id, user_corrected
from timing_event_span
where user_id = %s and session_id = %s
order by started_at, id
"""

INSERT_SPAN_SQL = """
insert into timing_event_span (
  user_id, session_id, checkpoint_run_id, start_event_id, end_event_id, span_type,
  friction_category, started_at, ended_at, duration_seconds, count_policy,
  count_in_wall_time, count_in_active_time, model_update_scopes,
  linked_annotation_id, linked_extracted_event_id, user_corrected
)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
returning id, user_id, session_id, checkpoint_run_id, span_type, friction_category,
  started_at, ended_at, duration_seconds, count_policy, count_in_wall_time,
  count_in_active_time, model_update_scopes, linked_annotation_id,
  linked_extracted_event_id, user_corrected
"""

INSERT_REVIEW_SQL = """
insert into model_update_decision (
  user_id, session_id, decision, model_inclusion, scopes, user_note, payload
)
values (%s, %s, %s, %s, %s, %s, %s)
returning id, user_id, session_id, decision, model_inclusion, scopes, reviewed_at,
  user_note, payload
"""
