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
    #expect(events[2].timerActiveSeconds == 1_200)
    #expect(viewModel.status == .reviewed)
    #expect(viewModel.reviewDecision == .saveUsefulRun)
    #expect(viewModel.pendingEventCount == 4)
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

    await viewModel.startRun()
    await viewModel.completeCurrentCheckpoint()
    await viewModel.confirmFrictionEvidence(resourceName: "missing resource", note: "Had to fetch a missing resource.", suggestedPreflightText: "Check the dynamic resource before starting.")
    await viewModel.finishRun()
    await viewModel.trimForgottenTimerAtPlaceChange()
    await viewModel.saveReviewDecision(.frictionOnly)

    let events = try await store.load()
    #expect(events.map(\.eventType) == [
        .sessionStarted,
        .checkpointCompleted,
        .extractedEventCreated,
        .sessionCompleted,
        .userCorrectionApplied,
        .reviewSaved,
    ])
    #expect(events[2].payload["confirmation_state"] == "user_confirmed")
    #expect(events[2].payload["suggested_preflight_text"] == "Check the dynamic resource before starting.")
    #expect(events[4].payload["privacy_display"] == "human_explanation_only")
    #expect(events[5].payload["decision"] == ModelUpdateDecision.frictionOnly.rawValue)
    #expect(events[5].payload["model_inclusion"] == ModelInclusion.frictionPatternsOnly.rawValue)
    #expect(events[5].payload["scopes"] == "friction_patterns,preflight_suggestions")
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
