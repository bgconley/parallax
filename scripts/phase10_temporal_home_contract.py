from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION_MAP_PATH = ROOT / "docs/phase10_temporal_home_interactions/action_map.json"
EXPECTED_FIGMA_PATH = ROOT / "docs/phase10_temporal_home_interactions/figma_reactions_expected.json"
ACTUAL_FIGMA_PATH = ROOT / "docs/phase10_temporal_home_interactions/figma_reactions_actual.json"
HANDOFF_PATH = ROOT / "apps/ios/DesignHandoff/phase10_temporal_home_interactions.json"
TEMPORAL_MODELS_PATH = ROOT / "apps/ios/Sources/ParallaxApp/TemporalHomeModels.swift"
TEMPORAL_ACTION_MAP_PATH = ROOT / "apps/ios/Sources/ParallaxApp/TemporalHomeActionMap.swift"
TEMPORAL_SCREEN_PATH = ROOT / "apps/ios/Sources/ParallaxApp/TemporalHomeScreen.swift"
TEMPORAL_DRAWERS_PATH = ROOT / "apps/ios/Sources/ParallaxApp/TemporalHomeDrawers.swift"
PHASE8_DRAWER_MODELS_PATH = ROOT / "apps/ios/Sources/ParallaxApp/Phase8DrawerModels.swift"
PHASE8_DRAWER_VIEWS_PATH = ROOT / "apps/ios/Sources/ParallaxApp/Phase8DrawerViews.swift"
API_CLIENT_PATH = ROOT / "apps/ios/Sources/ParallaxCore/ParallaxAPIClient.swift"
MAKEFILE_PATH = ROOT / "Makefile"

REQUIRED_CLASSIFICATIONS = {"drawer", "navigation", "local_queue", "api_workflow", "display_only"}
REQUIRED_SCREEN_NODES = {"118:9", "118:104", "118:199", "118:294", "118:346"}
REQUIRED_PHASE8_ACTIONS = {
    "complete_step",
    "pause_step",
    "skip_step",
    "move_step",
    "add_step_note",
    "confirm_friction_evidence",
    "correct_friction_evidence",
    "ignore_friction_evidence",
    "keep_friction_note_only",
    "trim_forgotten_timer",
    "timer_kept_running",
    "forgotten_timer_not_sure",
    "save_useful_run",
    "mark_unusual",
    "active_time_only",
    "friction_evidence_only",
    "discard_timing_keep_note",
    "keep_preflight_active",
    "snooze_preflight",
    "hide_preflight",
    "retire_preflight",
    "view_preflight_runs",
    "update_checkpoint_plan",
    "make_checkpoint_optional",
    "start_from_checkpoint",
}
REQUIRED_API_CLIENT_METHODS = {
    "createTemporalQueryRequest",
    "listTimingReviewFlagsRequest",
    "updateTimingReviewFlagRequest",
    "confirmExtractedEventRequest",
    "correctExtractedEventRequest",
}


def main() -> int:
    action_map = _load_json(ACTION_MAP_PATH)
    expected_figma = _load_json(EXPECTED_FIGMA_PATH)
    actual_figma = _load_json(ACTUAL_FIGMA_PATH)
    handoff = _load_json(HANDOFF_PATH)
    temporal_models = TEMPORAL_MODELS_PATH.read_text()
    temporal_action_map = TEMPORAL_ACTION_MAP_PATH.read_text()
    temporal_screen = TEMPORAL_SCREEN_PATH.read_text()
    temporal_drawers = TEMPORAL_DRAWERS_PATH.read_text()
    phase8_models = PHASE8_DRAWER_MODELS_PATH.read_text()
    phase8_views = PHASE8_DRAWER_VIEWS_PATH.read_text()
    api_client = API_CLIENT_PATH.read_text()
    makefile = MAKEFILE_PATH.read_text()

    actions = action_map["actions"]
    action_ids = [action["id"] for action in actions]
    _expect(len(action_ids) == len(set(action_ids)), "duplicate Phase 10 action ids")
    _expect(len(action_ids) == 55, "Phase 10 action map must cover 55 selectable/display rows")
    _expect(
        {action["screen_node"] for action in actions} == REQUIRED_SCREEN_NODES,
        "Phase 10 action map screen-node coverage drift",
    )
    _expect(
        {action["classification"] for action in actions} == REQUIRED_CLASSIFICATIONS,
        "Phase 10 action map classification coverage drift",
    )
    _expect(
        set(action_map["classification_values"]) == REQUIRED_CLASSIFICATIONS,
        "Phase 10 classification values drift",
    )

    temporal_action_enum = _extract_enum_body(temporal_models, "TemporalHomeAction")
    swift_action_cases = {
        raw_value: case_name
        for case_name, raw_value in re.findall(
            r'case\s+(\w+)\s+=\s+"([^"]+)"', temporal_action_enum
        )
    }
    swift_action_ids = set(swift_action_cases)
    _expect(
        set(action_ids) == swift_action_ids,
        "TemporalHomeAction raw values drift from action_map.json",
    )
    for action_id in action_ids:
        case_name = swift_action_cases[action_id]
        _expect(
            f".{case_name}" in temporal_action_map, f"TemporalHomeActionMap missing {action_id}"
        )

    for path in (
        "TemporalHomeScreen.swift",
        "TemporalHomeModels.swift",
        "TemporalHomeActionMap.swift",
        "TemporalHomeViewModel.swift",
        "TemporalHomeDrawers.swift",
    ):
        _expect(
            path in (ROOT / "apps/ios/ParallaxNative.xcodeproj/project.pbxproj").read_text(),
            f"Xcode project missing {path}",
        )

    phase8_actions = set(re.findall(r'case\s+\w+\s+=\s+"([^"]+)"', phase8_models))
    _expect(
        REQUIRED_PHASE8_ACTIONS <= phase8_actions,
        "Phase 8 nested drawer action inventory incomplete",
    )
    _expect(
        "action: @escaping () -> Void = {}" not in phase8_views,
        "Phase 8 drawer helper still has empty action default",
    )
    _expect(
        "Button {}" not in temporal_screen + temporal_drawers + phase8_views,
        "empty SwiftUI Button action detected",
    )

    for method in REQUIRED_API_CLIENT_METHODS:
        _expect(method in api_client, f"ParallaxAPIClient missing {method}")
    for endpoint in (
        "/v1/temporal/query",
        "/v1/timing/sessions/\\(sessionId.uuidString)/review-flags",
        "/v1/timing/review-flags/\\(flagId.uuidString)",
        "/v1/timing/extracted-events/\\(eventId.uuidString)/confirm",
        "/v1/timing/extracted-events/\\(eventId.uuidString)/correct",
    ):
        _expect(endpoint in api_client, f"ParallaxAPIClient missing canonical endpoint {endpoint}")

    _expect(
        handoff["canonical_action_map"]
        == "docs/phase10_temporal_home_interactions/action_map.json",
        "Phase 10 handoff action map drift",
    )
    _expect("phase10-smoke:" in makefile, "Makefile missing phase10-smoke target")

    for node_id, minimum in expected_figma["minimum_reactions"].items():
        actual = actual_figma.get("reaction_counts", {}).get(node_id, 0)
        _expect(
            actual >= minimum,
            f"Figma reaction count for {node_id} below expected minimum: {actual} < {minimum}",
        )
    _expect(
        actual_figma.get("status") == "wired",
        "Figma reaction export must be refreshed after wiring",
    )

    print(
        json.dumps(
            {
                "status": "passed",
                "phase": "phase10",
                "summary": {
                    "actions": len(actions),
                    "screen_nodes": sorted(REQUIRED_SCREEN_NODES),
                    "figma_reactions": actual_figma.get("reaction_counts", {}),
                },
            },
            indent=2,
        )
    )
    return 0


def _load_json(path: Path) -> dict:
    _expect(path.exists(), f"missing required Phase 10 artifact: {path.relative_to(ROOT)}")
    return json.loads(path.read_text())


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"VALIDATION FAILED: {message}")


def _extract_enum_body(source: str, enum_name: str) -> str:
    match = re.search(rf"enum\s+{re.escape(enum_name)}\b[^\{{]*\{{", source)
    if match is None:
        raise SystemExit(f"VALIDATION FAILED: missing Swift enum {enum_name}")
    depth = 0
    body_start = match.end()
    for index in range(match.end() - 1, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[body_start:index]
    raise SystemExit(f"VALIDATION FAILED: unterminated Swift enum {enum_name}")


if __name__ == "__main__":
    raise SystemExit(main())
