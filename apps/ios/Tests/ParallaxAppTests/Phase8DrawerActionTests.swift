import Foundation
import ParallaxApp
import ParallaxCore
import Testing

@Test func phase8NestedDrawerActionInventoryIsComplete() {
    let expected: Set<String> = [
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
    ]

    #expect(Set(Phase8DrawerAction.allCases.map(\.rawValue)) == expected)
}

@MainActor
@Test func temporalHomeDrawerPerformerQueuesNestedDrawerActions() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_110_000),
        Date(timeIntervalSince1970: 1_775_110_010),
        Date(timeIntervalSince1970: 1_775_110_020),
    ]
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic test activity",
        sessionId: UUID(uuidString: "33333333-3333-4333-8333-333333333333")!,
        deviceId: "phase10-drawer-test",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await timing.startRun()
    await temporal.performDrawerAction(.pauseStep)
    await temporal.performDrawerAction(.addStepNote)

    let events = try await store.load()
    #expect(events.map(\.eventType) == [.sessionStarted, .sessionPaused, .annotationCaptured])
    #expect(events[1].payload["pause_reason"] == "user_paused_step")
    #expect(events[2].payload["source"] == "temporal_home")
}
