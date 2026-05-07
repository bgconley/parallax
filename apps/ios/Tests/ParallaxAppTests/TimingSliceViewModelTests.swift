import Foundation
import ParallaxApp
import ParallaxCore
import Testing

@MainActor
@Test func firstVerticalSliceQueuesCanonicalEventsThroughReview() async throws {
    let fileURL = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("pending-events.json")
    defer { try? FileManager.default.removeItem(at: fileURL.deletingLastPathComponent()) }

    var timestamps = [
        Date(timeIntervalSince1970: 1_775_000_000),
        Date(timeIntervalSince1970: 1_775_000_600),
        Date(timeIntervalSince1970: 1_775_001_800),
        Date(timeIntervalSince1970: 1_775_001_860),
    ]
    let store = FilePendingTimingEventStore(fileURL: fileURL)
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic test activity",
        sessionId: UUID(uuidString: "22222222-2222-4222-8222-222222222222")!,
        deviceId: "ios-test-device",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()
    await viewModel.recordResourceDetour(resourceName: "missing resource", note: "Had to find a missing resource.")
    await viewModel.finishRun()
    await viewModel.saveUsefulReview()

    let events = try await store.load()
    #expect(events.map(\.eventType) == [.sessionStarted, .resourceDetourStarted, .sessionCompleted, .reviewSaved])
    #expect(events[1].payload["count_policy"] == CountPolicy.wallOnly.rawValue)
    #expect(events[2].timerElapsedSeconds == 1_800)
    #expect(events[2].timerActiveSeconds == 600)
    #expect(viewModel.status == .reviewed)
    #expect(viewModel.reviewDecision == .saveUsefulRun)
    #expect(viewModel.pendingEventCount == 4)
}

@MainActor
@Test func repeatedSameReviewDecisionDoesNotQueueDuplicateReviewEvent() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_001_000),
        Date(timeIntervalSince1970: 1_775_001_120),
        Date(timeIntervalSince1970: 1_775_001_180),
        Date(timeIntervalSince1970: 1_775_001_240),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic duplicate review activity",
        sessionId: UUID(uuidString: "39393939-3939-4939-8939-393939393939")!,
        deviceId: "ios-duplicate-review-guard",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()
    await viewModel.finishRun()
    await viewModel.saveReviewDecision(.markUnusual)
    await viewModel.saveReviewDecision(.markUnusual)

    let events = try await store.load()
    #expect(events.map(\.eventType) == [.sessionStarted, .sessionCompleted, .reviewSaved])
    #expect(events.last?.payload["decision"] == ModelUpdateDecision.markUnusual.rawValue)
    #expect(viewModel.reviewDecision == .markUnusual)
}

@MainActor
@Test func drawerActionsQueueCanonicalEvidenceCorrectionAndReviewEvents() async throws {
    let fileURL = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("pending-events.json")
    defer { try? FileManager.default.removeItem(at: fileURL.deletingLastPathComponent()) }

    var timestamps = [
        Date(timeIntervalSince1970: 1_775_010_000),
        Date(timeIntervalSince1970: 1_775_010_120),
        Date(timeIntervalSince1970: 1_775_010_180),
        Date(timeIntervalSince1970: 1_775_012_520),
        Date(timeIntervalSince1970: 1_775_012_540),
        Date(timeIntervalSince1970: 1_775_012_560),
    ]
    let store = FilePendingTimingEventStore(fileURL: fileURL)
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic test activity",
        sessionId: UUID(uuidString: "33333333-3333-4333-8333-333333333333")!,
        deviceId: "ios-drawer-test-device",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun(mode: .checkpointed)
    await viewModel.completeCurrentCheckpoint()
    await viewModel.confirmFrictionEvidence(resourceName: "missing resource", note: "Had to fetch a missing resource.", suggestedPreflightText: "Check the dynamic resource before starting.")
    await viewModel.finishRun()
    await viewModel.trimForgottenTimerAtPlaceChange()
    await viewModel.saveReviewDecision(.frictionOnly)

    let events = try await store.load()
    #expect(events.map(\.eventType) == [
        .sessionStarted,
        .checkpointStarted,
        .checkpointCompleted,
        .checkpointStarted,
        .extractedEventCreated,
        .sessionCompleted,
        .userCorrectionApplied,
        .reviewSaved,
    ])
    #expect(events[4].payload["confirmation_state"] == "user_confirmed")
    #expect(events[4].payload["suggested_preflight_text"] == "Check the dynamic resource before starting.")
    #expect(events[6].payload["privacy_display"] == "human_explanation_only")
    #expect(events[7].payload["decision"] == ModelUpdateDecision.frictionOnly.rawValue)
    #expect(events[7].payload["model_inclusion"] == ModelInclusion.frictionPatternsOnly.rawValue)
    #expect(events[7].payload["scopes"] == "friction_patterns,preflight_suggestions")
}

@MainActor
@Test func wholeTaskRunsDoNotEmitCheckpointEventsFromCheckpointControls() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_010_000),
        Date(timeIntervalSince1970: 1_775_010_010),
        Date(timeIntervalSince1970: 1_775_010_020),
        Date(timeIntervalSince1970: 1_775_010_030),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic whole-task activity",
        sessionId: UUID(uuidString: "34343434-3434-4434-8434-343434343434")!,
        deviceId: "ios-whole-task-checkpoint-guard",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()
    await viewModel.completeCurrentCheckpoint()
    await viewModel.skipCurrentCheckpoint()
    await viewModel.moveCurrentCheckpoint()

    #expect(viewModel.measurementMode == .wholeTask)
    #expect(try await store.load().map(\.eventType) == [.sessionStarted])
}

@MainActor
@Test func checkpointedRunsKeepCheckpointControlsActive() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_010_000),
        Date(timeIntervalSince1970: 1_775_010_010),
        Date(timeIntervalSince1970: 1_775_010_020),
        Date(timeIntervalSince1970: 1_775_010_030),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic checkpointed activity",
        sessionId: UUID(uuidString: "35353535-3535-4535-8535-353535353535")!,
        deviceId: "ios-checkpointed-control-guard",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun(mode: .checkpointed)
    await viewModel.completeCurrentCheckpoint()
    await viewModel.skipCurrentCheckpoint()
    await viewModel.moveCurrentCheckpoint()

    let events = try await store.load()
    #expect(viewModel.measurementMode == .checkpointed)
    #expect(events.map(\.eventType) == [
        .sessionStarted,
        .checkpointStarted,
        .checkpointCompleted,
        .checkpointStarted,
        .checkpointSkipped,
        .checkpointStarted,
        .scopeChanged,
    ])
    #expect(events.last?.payload["sequence_order"] == "4")
    #expect(events.last?.payload["label"] == "Checkpoint 4")
    #expect(events.last?.payload["checkpoint_action"] == "move_current_step")
}

@MainActor
@Test func checkpointedRunStartEmitsCurrentCheckpointStartedWithCanonicalPayload() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_010_000),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic checkpoint start activity",
        sessionId: UUID(uuidString: "37373737-3737-4737-8737-373737373737")!,
        deviceId: "ios-checkpoint-start-guard",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun(mode: .checkpointed)

    let events = try await store.load()
    #expect(events.map(\.eventType) == [.sessionStarted, .checkpointStarted])
    if events.indices.contains(1) {
        #expect(events[1].payload["sequence_order"] == "2")
        #expect(events[1].payload["label"] == "Current checkpoint")
        #expect(events[1].payload["checkpoint_label"] == "Current checkpoint")
    }
}

@MainActor
@Test func checkpointSetupStartFromStepCreatesCheckpointedRunBoundary() async throws {
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_102_000),
        Date(timeIntervalSince1970: 1_775_102_001),
        Date(timeIntervalSince1970: 1_775_102_002),
    ]
    let store = InMemoryPendingTimingEventStore()
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "29292929-2929-4929-8929-292929292929")!,
        activityName: "Dynamic checkpoint setup activity",
        deviceId: "ios-uat-checkpoint-setup-start",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.updateCheckpointPlan()
    await viewModel.startFromCurrentCheckpoint()

    let events = try await store.load()
    #expect(events.map(\.eventType) == [.intentRecorded, .sessionStarted, .checkpointStarted])
    try #require(events.count == 3)
    #expect(viewModel.status == .running)
    #expect(viewModel.measurementMode == .checkpointed)
    #expect(events[0].payload["measurement_mode"] == MeasurementMode.checkpointed.rawValue)
    #expect(events[1].payload["measurement_mode"] == MeasurementMode.checkpointed.rawValue)
    #expect(events[2].payload["source"] == "checkpoint_setup_drawer")
    #expect(events[2].payload["sequence_order"] == "3")
    #expect(events[2].payload["label"] == "Next checkpoint")
}

@MainActor
@Test func completingCheckpointAdvancesProjectionAndUsesCanonicalSequencePayload() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_010_000),
        Date(timeIntervalSince1970: 1_775_010_010),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic checkpoint sequence activity",
        sessionId: UUID(uuidString: "36363636-3636-4636-8636-363636363636")!,
        deviceId: "ios-checkpoint-sequence-guard",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun(mode: .checkpointed)
    let completedLabel = viewModel.currentCheckpointLabel
    let expectedNextCurrent = viewModel.nextCheckpointLabel

    await viewModel.completeCurrentCheckpoint()

    let events = try await store.load()
    #expect(events.map(\.eventType) == [.sessionStarted, .checkpointStarted, .checkpointCompleted, .checkpointStarted])
    if events.indices.contains(3) {
        let completedPayload = events[2].payload
        let nextStartedPayload = events[3].payload
        #expect(completedPayload["sequence_order"] == "2")
        #expect(completedPayload["label"] == completedLabel)
        #expect(completedPayload["checkpoint_label"] == completedLabel)
        #expect(nextStartedPayload["sequence_order"] == "3")
        #expect(nextStartedPayload["label"] == expectedNextCurrent)
        #expect(nextStartedPayload["source"] == "checkpoint_auto_advance")
    }
    #expect(viewModel.currentCheckpointLabel == expectedNextCurrent)
    #expect(viewModel.nextCheckpointLabel == "Checkpoint 4")
}

@MainActor
@Test func checkpointStepNotesCarryCurrentCheckpointContextForSync() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_010_000),
        Date(timeIntervalSince1970: 1_775_010_090),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic checkpoint note activity",
        sessionId: UUID(uuidString: "38383838-3838-4838-8838-383838383838")!,
        deviceId: "ios-checkpoint-note-guard",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun(mode: .checkpointed)
    await viewModel.captureStepNote("Checkpoint note must stay tied to this step.")

    let events = try await store.load()
    #expect(events.map(\.eventType) == [.sessionStarted, .checkpointStarted, .annotationCaptured])
    if events.indices.contains(2) {
        #expect(events[2].payload["source"] == "timing_session_step_note")
        #expect(events[2].payload["sequence_order"] == "2")
        #expect(events[2].payload["label"] == "Current checkpoint")
        #expect(events[2].payload["checkpoint_label"] == "Current checkpoint")
    }
}

@MainActor
@Test func dynamicFrictionLoggingQueuesUserNoteAndDetour() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_011_000),
        Date(timeIntervalSince1970: 1_775_011_060),
        Date(timeIntervalSince1970: 1_775_011_120),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic friction activity",
        sessionId: UUID(uuidString: "66666666-6666-4666-8666-666666666666")!,
        deviceId: "ios-friction-test-device",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()
    await viewModel.logFriction(
        resourceName: "dynamic blocker",
        note: "UAT dynamic note should survive sync."
    )

    let events = try await store.load()
    #expect(events.map(\.eventType) == [.sessionStarted, .annotationCaptured, .resourceDetourStarted])
    #expect(events[1].notePreview == "UAT dynamic note should survive sync.")
    #expect(events[1].payload["source"] == "timing_session_friction")
    #expect(events[2].payload["resource_name"] == "dynamic blocker")
    #expect(viewModel.detourNote == "UAT dynamic note should survive sync.")
}

@MainActor
@Test func frictionEvidenceProjectionUsesCapturedResourceAndNote() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_011_000),
        Date(timeIntervalSince1970: 1_775_011_060),
        Date(timeIntervalSince1970: 1_775_011_120),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic friction projection activity",
        sessionId: UUID(uuidString: "40404040-4040-4040-8040-404040404040")!,
        deviceId: "ios-friction-projection-device",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    #expect(viewModel.frictionEvidence.title == "No friction evidence yet")
    #expect(viewModel.frictionEvidence.canConfirm == false)

    await viewModel.startRun()
    await viewModel.logFriction(
        resourceName: "Dynamic blocked resource",
        note: "Drawer should show the actual user-entered blocker note."
    )

    let projection = viewModel.frictionEvidence
    #expect(projection.title == "Dynamic blocked resource")
    #expect(projection.evidenceLines.contains("Drawer should show the actual user-entered blocker note."))
    #expect(projection.canConfirm)
    #expect(projection.canCorrect)
    #expect(projection.canIgnore)
    #expect(projection.canKeepNoteOnly)
}

@MainActor
@Test func pauseDurationDoesNotAccumulateAsActiveTime() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_012_000),
        Date(timeIntervalSince1970: 1_775_012_060),
        Date(timeIntervalSince1970: 1_775_012_660),
        Date(timeIntervalSince1970: 1_775_012_780),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic pause activity",
        sessionId: UUID(uuidString: "77777777-7777-4777-8777-777777777777")!,
        deviceId: "ios-pause-duration-device",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()
    await viewModel.pauseCurrentStep()
    await viewModel.resumeRun()
    await viewModel.finishRun()

    let completed = try #require(try await store.load().last)
    #expect(viewModel.elapsedSeconds == 780)
    #expect(viewModel.activeSeconds == 180)
    #expect(completed.timerElapsedSeconds == 780)
    #expect(completed.timerActiveSeconds == 180)
}

@MainActor
@Test func refreshTimerUpdatesLiveDurationsWithoutAppendingEvents() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_012_000),
        Date(timeIntervalSince1970: 1_775_012_045),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic wall clock activity",
        sessionId: UUID(uuidString: "99999999-9999-4999-8999-999999999999")!,
        deviceId: "ios-refresh-timer-device",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()
    viewModel.refreshTimer()

    #expect(viewModel.elapsedSeconds == 45)
    #expect(viewModel.activeSeconds == 45)
    #expect(try await store.load().map(\.eventType) == [.sessionStarted])
}

@MainActor
@Test func resourceDetourUsesActualOpenSpanTimeInsteadOfFixedPlaceholderDuration() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_013_000),
        Date(timeIntervalSince1970: 1_775_013_060),
        Date(timeIntervalSince1970: 1_775_013_180),
    ]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic detour activity",
        sessionId: UUID(uuidString: "88888888-8888-4888-8888-888888888888")!,
        deviceId: "ios-detour-duration-device",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()
    await viewModel.recordResourceDetour(resourceName: "dynamic blocker", note: "Had to resolve dynamic blocker.")
    await viewModel.finishRun()

    let completed = try #require(try await store.load().last)
    #expect(viewModel.elapsedSeconds == 180)
    #expect(viewModel.activeSeconds == 60)
    #expect(viewModel.detourSeconds == 120)
    #expect(completed.timerElapsedSeconds == 180)
    #expect(completed.timerActiveSeconds == 60)
}

@Test func phase8DrawerWorkflowAliasesMatchFigmaHandoffNames() {
    #expect(Phase8DrawerWorkflow(rawDemoValue: "step_detail") == .stepDetail)
    #expect(Phase8DrawerWorkflow(rawDemoValue: "friction_evidence") == .frictionEvidence)
    #expect(Phase8DrawerWorkflow(rawDemoValue: "forgotten_timer") == .forgottenTimer)
    #expect(Phase8DrawerWorkflow(rawDemoValue: "review_decision") == .reviewDecision)
    #expect(Phase8DrawerWorkflow(rawDemoValue: "preflight_evidence") == .preflightEvidence)
    #expect(Phase8DrawerWorkflow(rawDemoValue: "checkpoint_setup") == .checkpointSetup)
}

@Test func reviewDecisionDisplayProjectsCanonicalDomainValues() {
    let frictionOnly = ReviewDecisionDisplayFactory.option(for: .frictionOnly)

    #expect(frictionOnly.modelInclusion == .frictionPatternsOnly)
    #expect(frictionOnly.scopes == [.frictionPatterns, .preflightSuggestions])
    #expect(frictionOnly.title == "Friction / evidence only")
}

@Test func reviewDecisionDisplayExposesEveryCanonicalModelUpdateDecision() {
    let options = ReviewDecisionDisplayFactory.options()
    let optionDecisions = Set(options.map(\.decision))

    #expect(optionDecisions == Set(ModelUpdateDecision.allCases))

    for decision in ModelUpdateDecision.allCases {
        let option = ReviewDecisionDisplayFactory.option(for: decision)
        #expect(option.decision == decision)
        #expect(option.selected)
    }
}

@MainActor
@Test func forgottenTimerCorrectionTrimsInflatedDurations() async throws {
    let fileURL = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("pending-events.json")
    defer { try? FileManager.default.removeItem(at: fileURL.deletingLastPathComponent()) }

    var timestamps = [
        Date(timeIntervalSince1970: 1_775_020_000),
        Date(timeIntervalSince1970: 1_775_023_600),
        Date(timeIntervalSince1970: 1_775_023_601),
    ]
    let store = FilePendingTimingEventStore(fileURL: fileURL)
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic test activity",
        sessionId: UUID(uuidString: "55555555-5555-4555-8555-555555555555")!,
        deviceId: "ios-trim-test-device",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()
    await viewModel.finishRun()
    #expect(viewModel.elapsedSeconds == 3_600)
    #expect(viewModel.activeSeconds == 3_600)

    await viewModel.trimForgottenTimerAtPlaceChange()

    let correction = try #require(try await store.load().last)
    #expect(viewModel.elapsedSeconds == 2_520)
    #expect(viewModel.activeSeconds == 1_860)
    #expect(correction.timerElapsedSeconds == 2_520)
    #expect(correction.timerActiveSeconds == 1_860)
    #expect(correction.payload["original_elapsed_seconds"] == "3600")
    #expect(correction.payload["trimmed_elapsed_seconds"] == "2520")
}

@MainActor
@Test func discardReviewDecisionUsesDiscardStateAndSyncOperation() async throws {
    let fileURL = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("pending-events.json")
    defer { try? FileManager.default.removeItem(at: fileURL.deletingLastPathComponent()) }

    var timestamps = [
        Date(timeIntervalSince1970: 1_775_030_000),
        Date(timeIntervalSince1970: 1_775_030_900),
        Date(timeIntervalSince1970: 1_775_030_920),
    ]
    let store = FilePendingTimingEventStore(fileURL: fileURL)
    let sessionId = UUID(uuidString: "66666666-6666-4666-8666-666666666666")!
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic test activity",
        sessionId: sessionId,
        deviceId: "ios-discard-test-device",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()
    await viewModel.finishRun()
    await viewModel.saveReviewDecision(.discardTimingKeepNote)

    let discardEvent = try #require(try await store.load().last)
    #expect(viewModel.status == .discarded)
    #expect(viewModel.reviewDecision == .discardTimingKeepNote)
    #expect(discardEvent.eventType == .reviewSaved)
    #expect(discardEvent.payload["decision"] == ModelUpdateDecision.discardTimingKeepNote.rawValue)
    #expect(discardEvent.payload["model_inclusion"] == ModelInclusion.exclude.rawValue)
    #expect(discardEvent.payload["sync_operation"] == "discard_timing_session")
    #expect(discardEvent.payload["sync_path"] == "/v1/timing/sessions/\(sessionId.uuidString)/discard")
}

@MainActor
@Test func preflightDrawerDecisionPersistsPendingMutation() async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    let timingURL = directory.appendingPathComponent("pending-events.json")
    let preflightURL = directory.appendingPathComponent("pending-preflight-decisions.json")
    defer { try? FileManager.default.removeItem(at: directory) }

    var timestamps = [Date(timeIntervalSince1970: 1_775_040_000)]
    let preflightStore = FilePendingPreflightDecisionStore(fileURL: preflightURL)
    let activityId = UUID(uuidString: "77777777-7777-4777-8777-777777777777")!
    let checkId = UUID(uuidString: "88888888-8888-4888-8888-888888888888")!
    let viewModel = TimingSliceViewModel(
        activityId: activityId,
        activityName: "Dynamic test activity",
        deviceId: "ios-preflight-test-device",
        eventStore: FilePendingTimingEventStore(fileURL: timingURL),
        preflightDecisionStore: preflightStore,
        now: { timestamps.removeFirst() }
    )

    await viewModel.decidePreflightCheck(.hide, checkId: checkId, reason: "not useful")

    let decisions = try await preflightStore.load()
    #expect(decisions.count == 1)
    #expect(decisions[0].activityId == activityId)
    #expect(decisions[0].checkId == checkId)
    #expect(decisions[0].decision == .hide)
    #expect(decisions[0].reason == "not useful")
    #expect(decisions[0].mutation.clientSequence == 1)
    #expect(viewModel.pendingEventCount == 1)
}

@MainActor
@Test func preflightSnoozeDefaultsToTomorrowWhenDrawerOmitsDate() async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    let preflightURL = directory.appendingPathComponent("pending-preflight-decisions.json")
    defer { try? FileManager.default.removeItem(at: directory) }

    let now = Date(timeIntervalSince1970: 1_775_040_000)
    let preflightStore = FilePendingPreflightDecisionStore(fileURL: preflightURL)
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "77777777-7777-4777-8777-777777777777")!,
        activityName: "Dynamic test activity",
        deviceId: "ios-preflight-snooze-device",
        eventStore: InMemoryPendingTimingEventStore(),
        preflightDecisionStore: preflightStore,
        now: { now }
    )

    await viewModel.decidePreflightCheck(
        .snooze,
        checkId: UUID(uuidString: "88888888-8888-4888-8888-888888888888")!
    )

    let decision = try #require(try await preflightStore.load().first)
    #expect(decision.decision == .snooze)
    #expect(decision.snoozedUntil == now.addingTimeInterval(86_400))
}

@MainActor
@Test func mutationFactorySeedsFromPersistedEventsBeforeAppending() async throws {
    let fileURL = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("pending-events.json")
    defer { try? FileManager.default.removeItem(at: fileURL.deletingLastPathComponent()) }

    let deviceId = "ios-seeded-device"
    let store = FilePendingTimingEventStore(fileURL: fileURL)
    let existingMutation = MutationEnvelope(
        idempotencyKey: "\(deviceId):7",
        clientMutationId: "session_started-7",
        clientDeviceId: deviceId,
        clientSequence: 7,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_049_000)
    )
    try await store.append(
        PendingTimingEvent(
            sessionId: UUID(uuidString: "99999999-9999-4999-8999-999999999999")!,
            eventType: .sessionStarted,
            mutation: existingMutation,
            clientTime: Date(timeIntervalSince1970: 1_775_049_001),
            captureMethod: .manualButton
        )
    )

    var timestamps = [Date(timeIntervalSince1970: 1_775_050_000)]
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic test activity",
        deviceId: deviceId,
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await viewModel.startRun()

    let events = try await store.load()
    #expect(events.count == 2)
    #expect(events[1].mutation.clientSequence == 8)
    #expect(events[1].mutation.idempotencyKey == "\(deviceId):8")
    #expect(events[1].captureMethod == .manualButton)
    #expect(viewModel.pendingEventCount == 2)
}

@MainActor
@Test func mutationFactorySeedsFromDurableSequenceWhenQueuesAreEmpty() async throws {
    let deviceId = "ios-persisted-sequence-device"
    let sequenceStore = InMemoryMutationSequenceStore(sequences: [deviceId: 4])
    let preflightStore = InMemoryPendingPreflightDecisionStore()
    let timestamp = Date(timeIntervalSince1970: 1_775_060_000)
    let viewModel = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic test activity",
        deviceId: deviceId,
        eventStore: InMemoryPendingTimingEventStore(),
        preflightDecisionStore: preflightStore,
        mutationSequenceStore: sequenceStore,
        now: { timestamp }
    )

    await viewModel.decidePreflightCheck(
        .hide,
        checkId: UUID(uuidString: "88888888-8888-4888-8888-888888888888")!
    )

    let decision = try #require(try await preflightStore.load().first)
    #expect(decision.mutation.clientSequence == 5)
    #expect(decision.mutation.idempotencyKey == "\(deviceId):5")
    #expect(try await sequenceStore.loadSequence(clientDeviceId: deviceId) == 5)
}

@MainActor
@Test func syncQueueProjectionUsesUserFacingPendingChangesInSequenceOrder() async throws {
    let activityId = UUID(uuidString: "11111111-1111-4111-8111-111111111111")!
    let sessionId = UUID(uuidString: "22222222-2222-4222-8222-222222222222")!
    let checkId = UUID(uuidString: "33333333-3333-4333-8333-333333333333")!
    let eventStore = InMemoryPendingTimingEventStore(events: [
        pendingEvent(
            .annotationCaptured,
            sessionId: sessionId,
            sequence: 7,
            notePreview: "UAT typed note",
            payload: ["source": "temporal_home"]
        ),
        pendingEvent(.sessionStarted, sessionId: sessionId, sequence: 5),
    ])
    let preflightStore = InMemoryPendingPreflightDecisionStore(decisions: [
        PendingPreflightDecision(
            activityId: activityId,
            checkId: checkId,
            mutation: mutation(sequence: 6, prefix: "decide_preflight_check"),
            decision: .hide,
            decidedAt: Date(timeIntervalSince1970: 1_775_080_006),
            reason: "not useful here"
        )
    ])
    let viewModel = TimingSliceViewModel(
        activityId: activityId,
        activityName: "Dynamic sync activity",
        sessionId: sessionId,
        deviceId: "ios-sync-projection-device",
        eventStore: eventStore,
        preflightDecisionStore: preflightStore
    )

    await viewModel.loadPendingEvents()

    #expect(viewModel.pendingEventCount == 3)
    #expect(viewModel.pendingSyncRows.map(\.title) == [
        "Timer started",
        "Preflight: Hide",
        "Note captured",
    ])
    #expect(viewModel.pendingSyncRows.map(\.detail) == [
        "Sync item 5",
        "Sync item 6",
        "Sync item 7",
    ])
    #expect(viewModel.pendingSyncRows.allSatisfy { !$0.title.contains("resource_detour") })
    #expect(viewModel.pendingSyncRows.allSatisfy { !$0.title.contains("review_saved") })
}

private func pendingEvent(
    _ eventType: TimingEventType,
    sessionId: UUID,
    sequence: Int,
    notePreview: String? = nil,
    payload: [String: String] = [:]
) -> PendingTimingEvent {
    PendingTimingEvent(
        sessionId: sessionId,
        eventType: eventType,
        mutation: mutation(sequence: sequence, prefix: eventType.rawValue),
        clientTime: Date(timeIntervalSince1970: 1_775_080_000 + Double(sequence)),
        timerElapsedSeconds: sequence,
        timerActiveSeconds: sequence,
        captureMethod: .manualButton,
        notePreview: notePreview,
        payload: payload
    )
}

private func mutation(sequence: Int, prefix: String) -> MutationEnvelope {
    MutationEnvelope(
        idempotencyKey: "ios-sync-projection-device:\(sequence)",
        clientMutationId: "\(prefix)-\(sequence)",
        clientDeviceId: "ios-sync-projection-device",
        clientSequence: sequence,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_080_000 + Double(sequence))
    )
}
