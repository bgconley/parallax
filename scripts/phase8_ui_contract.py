from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS_PATH = ROOT / "parallax_v1_3_artifact_pack/contracts/design/design_tokens.json"
EXAMPLES_PATH = ROOT / "parallax_v1_3_artifact_pack/examples"
EXPANSION_PACK_PATH = ROOT / "figma_expansion_readiness_pack_v0_8_1"
HANDOFF_PATH = ROOT / "apps/ios/DesignHandoff/phase8_figma_handoff.json"
SWIFT_DOMAIN_PATH = ROOT / "apps/ios/Sources/ParallaxCore/ParallaxDomain.swift"
TIMING_LAUNCHER_PATH = ROOT / "apps/ios/Sources/ParallaxApp/TimingLauncherSheet.swift"
XCODE_PROJECT_PATH = ROOT / "apps/ios/ParallaxNative.xcodeproj/project.pbxproj"


REQUIRED_SURFACES = {
    "Temporal Home",
    "Timing Launcher",
    "Checkpoint Setup",
    "Timing Session",
    "Timing Review",
}

REQUIRED_STATES = {
    "Default",
    "Offline Cached",
    "Sync Pending",
    "AI Pending",
    "Needs Review",
    "High Contrast",
    "Dynamic Type Stress",
}

REQUIRED_TIMING_STATES = {
    "Running",
    "Paused",
    "Detour Active",
    "Side Quest Active",
    "Forgot To Stop Correction",
}

REQUIRED_COMPONENTS = {
    "ActivityRow",
    "ActivityProfileHero",
    "PersonalRangeChip",
    "TimingLauncherCard",
    "TimingInstrument",
    "CurrentCheckpointCard",
    "SayWhatHappenedButton",
    "ContextCaptureSheet",
    "ContextInterpretationCard",
    "RunTimeline",
    "RunTimelineItem",
    "ReviewSummaryCard",
    "CountTreatmentCard",
    "InclusionDecisionControl",
    "EvidenceBackedAnswerCard",
    "QueryEvidenceCard",
    "PreflightCheckCard",
    "StartLatencyCard",
    "WorkModeSelector",
    "PrivacySettingCard",
    "SyncStatusPill",
    "CorrectionActionSheet",
}

REQUIRED_PAYLOAD_EXAMPLES = {
    "payloads/sample_activity_profile_response.json",
    "payloads/sample_capture_context_snapshot.json",
    "payloads/sample_context_capture_policy.json",
    "payloads/sample_place_change_forgotten_timer_scenario.json",
    "payloads/sample_sponge_detour_run.json",
    "payloads/sample_sync_push.json",
    "payloads/sample_temporal_query_answer.json",
    "payloads/sample_timing_review_flag.json",
}

REQUIRED_REFERENCE_MOCKUPS = {
    "reference_mockups/01_today_reference.png",
    "reference_mockups/02_timing_launcher_reference.png",
    "reference_mockups/03_timing_review_reference.png",
    "reference_mockups/04_timing_session_reference.png",
    "reference_mockups/05_break_it_down_reference.png",
}

REQUIRED_EXPANSION_INPUTS = {
    "START_HERE_FIGMA_AGENT.md",
    "01_design_authority_hierarchy.md",
    "08_figma_usage_playbook.md",
    "source_docs/02_canonical_design_language.md",
    "source_docs/05_component_system.md",
    "source_docs/08_accessibility_cognitive_load.md",
    "source_docs/11_design_acceptance_gates.md",
    "contracts/timing_session_ui.schema.json",
    "contracts/ui_state_model.schema.json",
    "system_boards/01_ui_component_library.png",
    "system_boards/02_state_matrix.png",
    "system_boards/03_navigation_layout_grammar.png",
    "anchors/05_timing_session.png",
    "anchors/06_timing_review.png",
    "anchors/07_calibrate_timing_sheet.png",
}


def main() -> int:
    tokens = json.loads(TOKENS_PATH.read_text())
    handoff = json.loads(HANDOFF_PATH.read_text())
    swift_domain = SWIFT_DOMAIN_PATH.read_text()
    timing_launcher = TIMING_LAUNCHER_PATH.read_text()
    xcode_project = XCODE_PROJECT_PATH.read_text()

    _expect(
        tokens["meta"]["app_name"] == "Parallax",
        "design token app name must be Parallax",
    )
    _expect(tokens["meta"]["version"] == handoff["token_version"], "handoff token version drift")
    _expect(handoff["figma_file_name"].startswith("Parallax"), "Figma file name must use Parallax")
    _expect(handoff["figma_status"] == "created", "Figma file must be created for Phase 8")
    _expect(
        isinstance(handoff["figma_file_key"], str) and len(handoff["figma_file_key"]) > 8,
        "Figma file key must be recorded",
    )
    _expect(
        handoff["figma_file_url"].endswith(handoff["figma_file_key"]),
        "Figma file URL/key drift",
    )
    _expect(
        "parallax_v1_3_artifact_pack/examples/reference_mockups"
        in handoff["figma_source_inputs"],
        "Figma handoff must record canonical reference mockups",
    )
    _expect(
        "parallax_v1_3_artifact_pack/examples/payloads" in handoff["figma_source_inputs"],
        "Figma handoff must record canonical UI payload examples",
    )
    _expect(
        "figma_expansion_readiness_pack_v0_8_1" in handoff["figma_source_inputs"],
        "Figma handoff must record design-language expansion input",
    )

    _expect_files(EXAMPLES_PATH, REQUIRED_PAYLOAD_EXAMPLES)
    _expect_files(EXAMPLES_PATH, REQUIRED_REFERENCE_MOCKUPS)
    _expect_files(EXPANSION_PACK_PATH, REQUIRED_EXPANSION_INPUTS)

    frames = handoff["frames"]
    frame_names = [frame["name"] for frame in frames]
    _expect(all(name.startswith("Parallax / ") for name in frame_names), "frame naming drift")
    _expect(
        not any("Temporal" in name and "Parallax" not in name for name in frame_names),
        "retired frame naming",
    )

    surfaces = {frame["surface"] for frame in frames}
    _expect(
        REQUIRED_SURFACES <= surfaces,
        f"missing surfaces: {sorted(REQUIRED_SURFACES - surfaces)}",
    )

    states = set(handoff["required_states"])
    states.update(*(set(frame["states"]) for frame in frames))
    _expect(
        REQUIRED_STATES <= states,
        f"missing required states: {sorted(REQUIRED_STATES - states)}",
    )
    _expect(
        REQUIRED_TIMING_STATES <= states,
        f"missing timing states: {sorted(REQUIRED_TIMING_STATES - states)}",
    )

    components = set(handoff["components"])
    _expect(
        REQUIRED_COMPONENTS <= components,
        f"missing components: {sorted(REQUIRED_COMPONENTS - components)}",
    )

    build_summary = handoff["figma_build_summary"]
    _expect(
        build_summary["core_flow_frames"] >= 5,
        "missing canonical core-flow Figma prototype frames",
    )
    _expect(
        build_summary.get("canonical_reference_backed_frames", 0)
        >= len(REQUIRED_REFERENCE_MOCKUPS),
        "missing source-backed canonical Figma frames",
    )
    _expect(
        build_summary["p0_state_frames"] + build_summary["accessibility_stress_frames"]
        >= len(frames),
        "missing canonical-derived Figma state frames",
    )
    _expect(
        build_summary["accessibility_stress_frames"] >= 4,
        "missing accessibility stress frames",
    )
    state_derivations = build_summary.get("canonical_state_derivation_nodes", {})
    _expect(
        state_derivations.get("p0", {}).get("count") == build_summary["p0_state_frames"],
        "P0 canonical state derivation count drift",
    )
    _expect(
        state_derivations.get("accessibility_offline_stress", {}).get("count")
        == build_summary["accessibility_stress_frames"],
        "accessibility/offline canonical state derivation count drift",
    )
    _expect(build_summary["component_cards"] >= len(components), "missing Figma component cards")
    _expect(build_summary["imported_reference_images"] >= 20, "missing imported Figma references")
    _expect(
        len(build_summary.get("screenshot_verified_nodes", [])) >= 8,
        "missing Figma screenshot verification coverage",
    )
    source_backed = build_summary.get("canonical_reference_backed_nodes", {})
    source_paths = {
        entry["source"].replace("parallax_v1_3_artifact_pack/examples/", "")
        for entry in source_backed.values()
    }
    _expect(
        REQUIRED_REFERENCE_MOCKUPS <= source_paths,
        "missing source-backed canonical references: "
        f"{sorted(REQUIRED_REFERENCE_MOCKUPS - source_paths)}",
    )
    visual_refinement = build_summary.get("visual_refinement", {})
    _expect(
        visual_refinement.get("status") == "completed",
        "Figma visual refinement status must be completed",
    )
    _expect(
        any("zero issues" in check for check in visual_refinement.get("checks", [])),
        "Figma visual refinement must record overlap audit results",
    )
    _expect(
        any(
            "source-backed canonical reference images" in check
            for check in visual_refinement.get("checks", [])
        ),
        "Figma visual refinement must record canonical source-backed rebuild",
    )
    drawer_workflows = build_summary.get("drawer_expansion_workflows", {})
    _expect(
        drawer_workflows.get("board_id") == "85:3",
        "Phase 8 drawer expansion workflow board must be recorded",
    )
    _expect(
        drawer_workflows.get("count") == 6,
        "Phase 8 drawer expansion workflow count must remain six",
    )
    _expect(
        set(drawer_workflows.get("workflows", []))
        == {
            "step_detail",
            "friction_evidence",
            "forgotten_timer",
            "review_decision",
            "preflight_evidence",
            "checkpoint_setup",
        },
        "Phase 8 drawer expansion workflow names drifted from Figma handoff",
    )
    _expect(
        any(
            "zero out-of-bounds and zero chip label issues" in check
            for check in visual_refinement.get("checks", [])
        ),
        "Figma drawer expansion QA must record zero-issue geometry/chip audit",
    )
    ios_implementation = handoff.get("ios_implementation", {})
    _expect(
        ios_implementation.get("xcode_project") == "apps/ios/ParallaxNative.xcodeproj",
        "Phase 8 iOS Xcode project path must be recorded",
    )
    _expect(
        ios_implementation.get("xcode_scheme") == "ParallaxNative",
        "Phase 8 iOS Xcode scheme must be recorded",
    )
    _expect(
        ios_implementation.get("module_boundaries") == [
            "ParallaxDesignSystem",
            "ParallaxCore",
            "ParallaxApp",
        ],
        "Phase 8 iOS module boundaries drifted",
    )
    _expect(
        "custom SwiftUI bottom overlays" in ios_implementation.get("drawer_implementation", ""),
        "Phase 8 drawer implementation must preserve custom Figma-scaled overlays",
    )
    simulator_evidence = ios_implementation.get("simulator", {})
    _expect(
        simulator_evidence.get("app_bundle_id") == "com.bgc.parallax.native",
        "Phase 8 simulator bundle id drift",
    )
    _expect(
        set(simulator_evidence.get("screenshot_evidence", {}))
        == set(drawer_workflows.get("workflows", [])),
        "Phase 8 simulator screenshot evidence must cover all drawer workflows",
    )
    _expect(
        set(simulator_evidence.get("figma_reference_evidence", {}))
        == set(drawer_workflows.get("workflows", [])),
        "Phase 8 Figma reference evidence must cover all drawer workflows",
    )
    for evidence_group in ("screenshot_evidence", "figma_reference_evidence"):
        for evidence_path in simulator_evidence.get(evidence_group, {}).values():
            _expect(
                (ROOT / evidence_path).exists(),
                f"missing Phase 8 visual evidence: {evidence_path}",
            )
    for xcode_file in (
        "CheckpointSetupScreen.swift",
        "PendingPreflightDecisionStore.swift",
        "Phase8DrawerModels.swift",
        "Phase8DrawerViews.swift",
    ):
        _expect(xcode_file in xcode_project, f"Xcode project target missing {xcode_file}")

    _expect(
        'case manualButton = "manual_timer_button"' in swift_domain,
        "manual timer capture method must use canonical manual_timer_button",
    )
    _expect(
        "let dismiss: () -> Void" in timing_launcher
        and ".onTapGesture(perform: dismiss)" in timing_launcher
        and "Button(action: dismiss)" in timing_launcher,
        "Timing launcher must support cancel/backdrop dismissal",
    )

    for required_case in (
        "offlineCached",
        "syncPending",
        "aiPending",
        "needsReview",
        "highContrast",
        "dynamicTypeStress",
        "waitingActive",
        "detourActive",
        "interruptionActive",
        "sideQuestActive",
        "forgotToStopCorrection",
        "unresolvedInterpretation",
    ):
        _expect(required_case in swift_domain, f"UI projection missing {required_case}")

    print(
        json.dumps(
            {
                "status": "passed",
                "phase": "phase8",
                "summary": {
                    "frames": len(frames),
                    "components": len(components),
                    "figma_status": handoff["figma_status"],
                    "figma_file_key": handoff["figma_file_key"],
                    "token_version": handoff["token_version"],
                },
            },
            indent=2,
        )
    )
    return 0


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _expect_files(base_path: Path, relative_paths: set[str]) -> None:
    missing = sorted(path for path in relative_paths if not (base_path / path).exists())
    _expect(not missing, f"missing Phase 8 source inputs under {base_path}: {missing}")


if __name__ == "__main__":
    raise SystemExit(main())
