# Phase 10 Temporal Home Action Map

Every selectable-looking element on the active 118 screens is listed here and in `action_map.json`. Swift enum raw values must match the `id` values exactly.

| Screen | Element | ID | Classification | Target |
| --- | --- | --- | --- | --- |
| `118:9` | Menu | `118_9_menu` | drawer | Temporal navigation drawer |
| `118:9` | Temporal action | `118_9_temporal_action` | drawer | Quick capture drawer |
| `118:9` | Current timing focus card | `118_9_current_focus` | navigation | `118:294` expanded run |
| `118:9` | Temporal insight card | `118_9_preflight_insight` | drawer | `preflight_evidence` |
| `118:9` | Current run | `118_9_running_row` | navigation | `118:294` expanded run |
| `118:9` | Preflight evidence | `118_9_preflight_row` | drawer | `preflight_evidence` |
| `118:9` | Waiting time | `118_9_waiting_row` | drawer | `step_detail` |
| `118:9` | Personal range baseline | `118_9_baseline_row` | drawer | Ask Time drawer |
| `118:9` | Grounded answer | `118_9_grounded_row` | navigation | `118:346` grounded answer |
| `118:9` | All evidence current | `118_9_evidence_current_row` | drawer | temporal answer evidence |
| `118:9` | Capture timing evidence | `118_9_quick_capture` | local_queue | annotation capture |
| `118:9` | Review run / approve learning | `118_9_review_run` | drawer | `review_decision` |
| `118:9` | Start timer | `118_9_start_timer` | navigation | Timing launcher |
| `118:9` | Ask time / grounded answer | `118_9_ask_time` | drawer | Ask Time drawer |
| `118:104` | Menu | `118_104_menu` | drawer | Temporal navigation drawer |
| `118:104` | Temporal action | `118_104_temporal_action` | drawer | Quick capture drawer |
| `118:104` | Review focus card | `118_104_review_focus` | drawer | `review_decision` |
| `118:104` | Learning impact pending | `118_104_learning_impact` | drawer | Ask Time drawer |
| `118:104` | Run review | `118_104_run_review_row` | drawer | `review_decision` |
| `118:104` | Evening reset correct | `118_104_evening_correct_row` | drawer | `forgotten_timer` |
| `118:104` | Baseline sample | `118_104_baseline_sample_row` | drawer | `review_decision` |
| `118:104` | Preflight check | `118_104_preflight_check_row` | drawer | `preflight_evidence` |
| `118:104` | Sample support | `118_104_sample_support_row` | drawer | Ask Time drawer |
| `118:104` | Queue ready | `118_104_queue_ready_row` | drawer | Sync queue drawer |
| `118:104` | Add review context | `118_104_quick_capture` | local_queue | annotation capture |
| `118:104` | Review all / choose scopes | `118_104_review_all` | drawer | `review_decision` |
| `118:104` | Ask impact / what changes | `118_104_ask_impact` | drawer | Ask Time drawer |
| `118:199` | Menu | `118_199_menu` | drawer | Temporal navigation drawer |
| `118:199` | Temporal action | `118_199_temporal_action` | drawer | Quick capture drawer |
| `118:199` | Sync focus card | `118_199_sync_focus` | drawer | Sync queue drawer |
| `118:199` | Local-first sync behavior | `118_199_sync_behavior` | drawer | Sync queue drawer |
| `118:199` | session_started queued | `118_199_session_started_row` | drawer | Sync queue drawer |
| `118:199` | resource_detour queued | `118_199_resource_detour_row` | drawer | Sync queue drawer |
| `118:199` | review_saved queued | `118_199_review_saved_row` | drawer | Sync queue drawer |
| `118:199` | preflight decision queued | `118_199_preflight_decision_row` | drawer | Sync queue drawer |
| `118:199` | Bearer retry | `118_199_bearer_retry_row` | local_queue | sync retry |
| `118:199` | Mutation sequence safe | `118_199_sequence_safe_row` | display_only | queue integrity status |
| `118:199` | Capture while offline | `118_199_quick_capture` | local_queue | annotation capture |
| `118:199` | Retry sync | `118_199_retry_sync` | local_queue | sync retry |
| `118:199` | View queue | `118_199_view_queue` | drawer | Sync queue drawer |
| `118:294` | Open review | `118_294_open_review` | drawer | `review_decision` |
| `118:294` | Ask similar time | `118_294_ask_similar_time` | drawer | Ask Time drawer |
| `118:294` | Start this again | `118_294_start_again` | navigation | Timing launcher |
| `118:346` | Menu | `118_346_menu` | drawer | Temporal navigation drawer |
| `118:346` | Temporal action | `118_346_temporal_action` | drawer | Quick capture drawer |
| `118:346` | Question focus card | `118_346_question_focus` | drawer | Temporal answer evidence |
| `118:346` | 36-44 min wall time | `118_346_answer_summary` | drawer | Temporal answer evidence |
| `118:346` | Reviewed runs | `118_346_reviewed_runs_row` | drawer | Temporal answer evidence |
| `118:346` | Resource detours | `118_346_resource_detours_row` | drawer | `friction_evidence` |
| `118:346` | Raw notes shown | `118_346_raw_notes_row` | drawer | Temporal answer evidence |
| `118:346` | Median wall time | `118_346_median_row` | drawer | Temporal answer evidence |
| `118:346` | Slow-case envelope | `118_346_slow_case_row` | drawer | Temporal answer evidence |
| `118:346` | Before starting | `118_346_before_starting_row` | drawer | `preflight_evidence` |
| `118:346` | Ask another time question | `118_346_ask_another` | drawer | Ask Time drawer |
| `118:346` | Start timer | `118_346_start_timer` | navigation | Timing launcher |
| `118:346` | Use check | `118_346_use_check` | drawer | `preflight_evidence` |
