import Foundation
import ParallaxApp
import ParallaxCore
import Testing

@MainActor
@Test func connectedActivityCreationPostsCanonicalActivityAndSelectsBackendActivity() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(
            201,
            """
            {
              "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
              "user_id": "11111111-1111-4111-8111-111111111111",
              "display_name": "Dynamic backend activity",
              "canonical_key": "dynamic-backend-activity",
              "status": "active",
              "default_timing_mode": "whole_task",
              "privacy_class": "normal",
              "created_at": "2026-05-05T00:00:00Z",
              "updated_at": "2026-05-05T00:00:00Z"
            }
            """
        ),
    ])
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
        transport: transport
    )
    let store = ParallaxAppStore(
        config: ParallaxRuntimeConfig(
            apiBaseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
            deviceId: "ios-uat-create-device"
        ),
        apiClient: client,
        eventStoreFactory: { _ in InMemoryPendingTimingEventStore() }
    )

    await store.createActivity(named: "Dynamic backend activity")

    #expect(store.selectedActivity?.displayName == "Dynamic backend activity")
    #expect(store.selectedActivity?.source == .backend)
    #expect(store.selectedActivity?.id == UUID(uuidString: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"))
    let requests = await transport.recordedRequests()
    #expect(requests.map(\.path) == ["/v1/activities"])
    #expect(requests.first?.method == "POST")
    #expect(requests.first?.header("X-Parallax-User-Id") == "11111111-1111-4111-8111-111111111111")
    let body = try #require(requests.first?.bodyData)
    let json = try #require(try JSONSerialization.jsonObject(with: body) as? [String: Any])
    #expect(json["display_name"] as? String == "Dynamic backend activity")
    #expect(json["default_timing_mode"] as? String == MeasurementMode.wholeTask.rawValue)
    #expect(json["mutation"] is [String: Any])
}

@MainActor
@Test func connectedBootstrapSelectsOnlyBackendActivityAfterRelaunch() async throws {
    let config = ParallaxRuntimeConfig(
        apiBaseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
        deviceId: "ios-uat-relaunch-device"
    )
    UserDefaults.standard.removeObject(forKey: "parallax.selectedActivityId.\(config.localStorageScope)")
    let transport = RecordingHTTPTransport(responses: [
        .json(
            200,
            """
            [{
              "id": "abababab-abab-4aba-8bab-abababababab",
              "user_id": "11111111-1111-4111-8111-111111111111",
              "display_name": "Dynamic persisted activity",
              "canonical_key": "dynamic-persisted-activity",
              "status": "active",
              "default_timing_mode": "whole_task",
              "privacy_class": "normal",
              "created_at": "2026-05-05T00:00:00Z",
              "updated_at": "2026-05-05T00:00:00Z"
            }]
            """
        ),
    ])
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
        transport: transport
    )
    let store = ParallaxAppStore(
        config: config,
        apiClient: client,
        eventStoreFactory: { _ in InMemoryPendingTimingEventStore() }
    )

    await store.bootstrap()

    #expect(store.selectedActivity?.displayName == "Dynamic persisted activity")
    #expect(store.timingViewModel?.activityName == "Dynamic persisted activity")
    #expect(await transport.recordedRequests().map(\.path) == ["/v1/activities"])
}

@MainActor
@Test func connectedBootstrapDoesNotUseCachedActivityFromDifferentRuntimeUser() async throws {
    let base = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
    defer { try? FileManager.default.removeItem(at: base) }

    let oldConfig = ParallaxRuntimeConfig(
        apiBaseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .devHeader(userId: UUID(uuidString: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")!),
        deviceId: "ios-uat-cross-user-device"
    )
    let newConfig = ParallaxRuntimeConfig(
        apiBaseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .devHeader(userId: UUID(uuidString: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")!),
        deviceId: "ios-uat-cross-user-device"
    )
    let oldRoot = ParallaxAppStore.localStorageRoot(base: base, config: oldConfig)
    let newRoot = ParallaxAppStore.localStorageRoot(base: base, config: newConfig)
    #expect(oldRoot != newRoot)

    let oldStore = ParallaxAppStore(
        appStateStore: FileParallaxAppStateStore(fileURL: oldRoot.appendingPathComponent("app-state.json")),
        localStorageRoot: oldRoot
    )
    await oldStore.createActivity(named: "Other user's stale activity")
    #expect(oldStore.selectedActivity?.displayName == "Other user's stale activity")

    let transport = RecordingHTTPTransport(responses: [.json(200, "[]")])
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: newConfig.auth,
        transport: transport
    )
    let newStore = ParallaxAppStore(
        config: newConfig,
        apiClient: client,
        eventStoreFactory: { _ in InMemoryPendingTimingEventStore() },
        appStateStore: FileParallaxAppStateStore(fileURL: newRoot.appendingPathComponent("app-state.json")),
        localStorageRoot: newRoot
    )

    await newStore.bootstrap()

    #expect(newStore.activities.isEmpty)
    #expect(newStore.selectedActivity == nil)
    #expect(newStore.timingViewModel == nil)
    #expect(await transport.recordedRequests().map(\.path) == ["/v1/activities"])
}

@MainActor
@Test func draftTemporalHomePrimaryActionsOpenLauncherAndDoNotOpenReview() async throws {
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "22222222-2222-4222-8222-222222222222")!,
        activityName: "Dynamic draft activity",
        deviceId: "ios-uat-home-actions",
        eventStore: InMemoryPendingTimingEventStore()
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await temporal.perform(.currentFocusDefault)
    #expect(temporal.showsLauncher)
    #expect(temporal.surfaceState == .defaultHome)

    temporal.dismissLauncher()
    await temporal.perform(.runningRowDefault)
    #expect(temporal.showsLauncher)
    #expect(temporal.surfaceState == .defaultHome)

    temporal.dismissLauncher()
    await temporal.perform(.startTimerDefault)
    #expect(temporal.showsLauncher)
    #expect(temporal.surfaceState == .defaultHome)

    temporal.dismissLauncher()
    await temporal.perform(.reviewRunDefault)
    #expect(temporal.activeDrawer == nil)
    #expect(temporal.showsLauncher == false)
}

@MainActor
@Test func stepDetailDrawerDoesNotInventRunningCheckpointForDraftWholeTask() async throws {
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "23232323-2323-4323-8323-232323232323")!,
        activityName: "Dynamic draft step activity",
        deviceId: "ios-uat-draft-step-detail",
        eventStore: InMemoryPendingTimingEventStore()
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await temporal.perform(.waitingRowDefault)

    #expect(temporal.activeDrawer == .phase8(.stepDetail))
    #expect(timing.stepDetail.eyebrow == "No active checkpoint")
    #expect(timing.stepDetail.title == "No run in progress")
    #expect(timing.stepDetail.canCompleteStep == false)
    #expect(timing.stepDetail.canPause == false)
    #expect(timing.stepDetail.canSkip == false)
    #expect(timing.stepDetail.canMove == false)
    #expect(timing.stepDetail.canAddNote == false)
}

@MainActor
@Test func stepDetailProjectionKeepsWholeTaskAndCheckpointedActionsSeparate() async throws {
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_100_100),
        Date(timeIntervalSince1970: 1_775_100_101),
    ]
    let wholeTask = TimingSliceViewModel(
        activityId: UUID(uuidString: "24242424-2424-4424-8424-242424242424")!,
        activityName: "Dynamic whole task step activity",
        deviceId: "ios-uat-whole-step-detail",
        eventStore: InMemoryPendingTimingEventStore(),
        now: { timestamps.removeFirst() }
    )

    await wholeTask.startRun(mode: .wholeTask)

    #expect(wholeTask.stepDetail.eyebrow == "Whole-task run · Running")
    #expect(wholeTask.stepDetail.title == "Dynamic whole task step activity")
    #expect(wholeTask.stepDetail.canCompleteStep == false)
    #expect(wholeTask.stepDetail.canPause)
    #expect(wholeTask.stepDetail.canSkip == false)
    #expect(wholeTask.stepDetail.canMove == false)
    #expect(wholeTask.stepDetail.canAddNote)

    var checkpointTimes = [
        Date(timeIntervalSince1970: 1_775_100_200),
        Date(timeIntervalSince1970: 1_775_100_201),
    ]
    let checkpointed = TimingSliceViewModel(
        activityId: UUID(uuidString: "27272727-2727-4727-8727-272727272727")!,
        activityName: "Dynamic checkpointed step activity",
        deviceId: "ios-uat-checkpoint-step-detail",
        eventStore: InMemoryPendingTimingEventStore(),
        now: { checkpointTimes.removeFirst() }
    )

    await checkpointed.startRun(mode: .checkpointed)

    #expect(checkpointed.stepDetail.eyebrow == "Current checkpoint · Running")
    #expect(checkpointed.stepDetail.title == checkpointed.currentCheckpointLabel)
    #expect(checkpointed.stepDetail.canCompleteStep)
    #expect(checkpointed.stepDetail.canPause)
    #expect(checkpointed.stepDetail.canSkip)
    #expect(checkpointed.stepDetail.canMove)
    #expect(checkpointed.stepDetail.canAddNote)
}

@MainActor
@Test func preflightEvidenceDrawerDoesNotInventBackendEvidenceWhenEmpty() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(200, "[]"),
        .json(200, "[]"),
    ])
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "25252525-2525-4525-8525-252525252525")!,
        activityName: "Dynamic empty preflight activity",
        deviceId: "ios-uat-empty-preflight",
        eventStore: InMemoryPendingTimingEventStore(),
        apiClient: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
            transport: transport
        )
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await temporal.perform(.preflightRowDefault)

    #expect(temporal.activeDrawer == .phase8(.preflightEvidence))
    #expect(timing.preflightEvidence.primaryCheckId == nil)
    #expect(timing.preflightEvidence.hasBackendEvidence == false)
    #expect(timing.preflightEvidence.title == "No preflight evidence yet")
    let renderedText = ([timing.preflightEvidence.title, timing.preflightEvidence.subtitle, timing.preflightEvidence.evidenceTitle, timing.preflightEvidence.noteTitle]
        + timing.preflightEvidence.evidenceLines
        + timing.preflightEvidence.noteLines
        + timing.preflightEvidence.chips)
        .joined(separator: " ")
    #expect(!renderedText.contains("Failure count 3"))
    #expect(!renderedText.contains("confidence 0.81"))
    #expect(Set(await transport.recordedRequests().map(\.path)) == [
        "/v1/activities/25252525-2525-4525-8525-252525252525/preflight-checks",
        "/v1/activities/25252525-2525-4525-8525-252525252525/resource-dependencies",
    ])
}

@MainActor
@Test func preflightDrawerDecisionUsesRealBackendCheckId() async throws {
    let preflightStore = InMemoryPendingPreflightDecisionStore()
    let transport = RecordingHTTPTransport(responses: [
        .json(
            200,
            """
            [{
              "id": "aaaaaaaa-2222-4aaa-8aaa-aaaaaaaa2222",
              "activity_id": "26262626-2626-4626-8626-262626262626",
              "check_text": "Check the real UAT blocker before starting.",
              "state": "suggested",
              "source": "resource_dependency"
            }]
            """
        ),
        .json(
            200,
            """
            [{
              "id": "bbbbbbbb-2222-4bbb-8bbb-bbbbbbbb2222",
              "resource_name": "real UAT blocker",
              "failure_count": 2,
              "confidence": 0.72
            }]
            """
        ),
    ])
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "26262626-2626-4626-8626-262626262626")!,
        activityName: "Dynamic preflight activity",
        deviceId: "ios-uat-real-preflight",
        eventStore: InMemoryPendingTimingEventStore(),
        preflightDecisionStore: preflightStore,
        apiClient: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
            transport: transport
        )
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await temporal.perform(.preflightInsightDefault)
    await temporal.performDrawerAction(.keepPreflightActive)

    let decisions = try await preflightStore.load()
    #expect(timing.preflightEvidence.primaryCheckId == UUID(uuidString: "aaaaaaaa-2222-4aaa-8aaa-aaaaaaaa2222"))
    #expect(decisions.map(\.checkId) == [UUID(uuidString: "aaaaaaaa-2222-4aaa-8aaa-aaaaaaaa2222")!])
    #expect(decisions.map(\.remoteCheckId) == [UUID(uuidString: "aaaaaaaa-2222-4aaa-8aaa-aaaaaaaa2222")!])
    #expect(decisions.map(\.decision) == [.accept])
    #expect(timing.errorMessage == nil)
}

@MainActor
@Test func preflightEvidenceProjectionUsesCheckEvidenceWhenDependencyRowsAreMissing() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(
            200,
            """
            [{
              "id": "abababab-3333-4aba-8bab-abababab3333",
              "activity_id": "28282828-2828-4828-8828-282828282828",
              "check_text": "Check the real UAT kit before starting.",
              "state": "suggested",
              "source": "resource_dependency",
              "confidence": 0.77,
              "failure_count": 2,
              "evidence_count": 2,
              "evidence_summary": "Two confirmed UAT detours suggested this check."
            }]
            """
        ),
        .json(200, "[]"),
    ])
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "28282828-2828-4828-8828-282828282828")!,
        activityName: "Dynamic preflight check-evidence activity",
        deviceId: "ios-uat-check-evidence-preflight",
        eventStore: InMemoryPendingTimingEventStore(),
        apiClient: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
            transport: transport
        )
    )

    await timing.refreshPreflightEvidence()

    #expect(timing.preflightEvidence.primaryCheckId == UUID(uuidString: "abababab-3333-4aba-8bab-abababab3333"))
    #expect(timing.preflightEvidence.evidenceLines.contains("Failure count 2 · confidence 0.77"))
    #expect(timing.preflightEvidence.noteLines.contains("Two confirmed UAT detours suggested this check."))
}

@MainActor
@Test func selectedMeasurementModeIsQueuedOnSessionStart() async throws {
    let store = InMemoryPendingTimingEventStore()
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "33333333-3333-4333-8333-333333333333")!,
        activityName: "Dynamic checkpoint activity",
        deviceId: "ios-uat-mode-device",
        eventStore: store
    )

    await timing.startRun(mode: .checkpointed)

    let event = try #require(try await store.load().first)
    #expect(event.eventType == .sessionStarted)
    #expect(event.payload["measurement_mode"] == MeasurementMode.checkpointed.rawValue)
}

@MainActor
@Test func connectedAskAboutTimeSubmitsTemporalQueryInsteadOfTimingIntentOnly() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(
            202,
            """
            {
              "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              "user_id": "11111111-1111-4111-8111-111111111111",
              "question": "How long does Dynamic ask activity usually take?",
              "answer": "I do not have reviewed timing history for that scope yet.",
              "confidence": "very_low",
              "sample_size": 0,
              "time_window": "last_180_days",
              "computed_facts": {},
              "limitations": ["No reviewed runs yet."],
              "evidence": [],
              "status": "complete"
            }
            """
        ),
    ])
    let eventStore = InMemoryPendingTimingEventStore()
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "44444444-4444-4444-8444-444444444444")!,
        activityName: "Dynamic ask activity",
        deviceId: "ios-uat-ask-device",
        eventStore: eventStore,
        apiClient: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
            transport: transport
        )
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await temporal.perform(.askTimeDefault)
    #expect(temporal.activeDrawer == .askTime)
    #expect(await transport.recordedRequests().isEmpty)

    await temporal.submitTemporalQuestion("How long does Dynamic ask activity usually take?")

    #expect(temporal.surfaceState == .groundedAnswer)
    #expect(temporal.activeDrawer == nil)
    #expect(timing.lastTemporalQueryAnswer?.id == UUID(uuidString: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))
    #expect(timing.lastTemporalQueryAnswer?.answerText == "I do not have reviewed timing history for that scope yet.")
    #expect(timing.lastTemporalQueryAnswer?.status == "complete")
    #expect(timing.lastTemporalQueryAnswer?.sampleSize == 0)
    #expect(try await eventStore.load().isEmpty)
    let requests = await transport.recordedRequests()
    #expect(requests.map(\.path) == ["/v1/temporal/query"])
    let body = try #require(requests.first?.bodyData)
    let json = try #require(try JSONSerialization.jsonObject(with: body) as? [String: Any])
    #expect(json["question"] as? String == "How long does Dynamic ask activity usually take?")
    #expect(json["activity_id"] as? String == "44444444-4444-4444-8444-444444444444")
    #expect(json["include_raw_quotes"] as? Bool == false)
}

@MainActor
@Test func temporalHomeViewModelReattachesToReplacementTimingModelBeforeSubmittingAskQuestion() async throws {
    let oldTiming = TimingSliceViewModel(
        activityId: UUID(uuidString: "28282828-2828-4828-8828-282828282828")!,
        activityName: "Stale captured ask activity",
        deviceId: "ios-uat-stale-captured-ask",
        eventStore: InMemoryPendingTimingEventStore()
    )
    let replacementTransport = RecordingHTTPTransport(responses: [
        .json(
            202,
            """
            {
              "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              "user_id": "11111111-1111-4111-8111-111111111111",
              "question": "How long does replacement ask activity take?",
              "answer": "I do not have reviewed timing history for that scope yet.",
              "confidence": "very_low",
              "sample_size": 0,
              "time_window": "last_180_days",
              "computed_facts": {"sample_size": 0},
              "limitations": ["No reviewed runs yet."],
              "evidence": [],
              "status": "complete"
            }
            """
        ),
    ])
    let replacementTiming = TimingSliceViewModel(
        activityId: UUID(uuidString: "29292929-2929-4929-8929-292929292929")!,
        activityName: "Replacement ask activity",
        deviceId: "ios-uat-replacement-ask",
        eventStore: InMemoryPendingTimingEventStore(),
        apiClient: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
            transport: replacementTransport
        )
    )
    let temporal = TemporalHomeViewModel(timingViewModel: oldTiming, initialSurface: .defaultHome)

    temporal.attachTimingViewModel(replacementTiming)
    await temporal.submitTemporalQuestion("How long does replacement ask activity take?")

    #expect(temporal.timingViewModel === replacementTiming)
    #expect(oldTiming.lastTemporalQueryAnswer == nil)
    #expect(replacementTiming.lastTemporalQueryAnswer?.id == UUID(uuidString: "cccccccc-cccc-4ccc-8ccc-cccccccccccc"))
    #expect(replacementTiming.lastTemporalQueryAnswer?.status == "complete")
    #expect(await replacementTransport.recordedRequests().map(\.path) == ["/v1/temporal/query"])
}

@MainActor
@Test func expandedRunReviewProjectionReflectsSavedReviewDecision() async throws {
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_130_000),
        Date(timeIntervalSince1970: 1_775_130_060),
        Date(timeIntervalSince1970: 1_775_130_120),
    ]
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "30303030-3030-4030-8030-303030303030")!,
        activityName: "Expanded run reviewed activity",
        deviceId: "ios-uat-expanded-reviewed-copy",
        eventStore: InMemoryPendingTimingEventStore(),
        now: { timestamps.removeFirst() }
    )

    await timing.startRun()
    await timing.finishRun()

    #expect(timing.expandedRunReviewProjection.title == "Review ready")
    #expect(timing.expandedRunReviewProjection.detail == "model inclusion pending")

    await timing.saveReviewDecision(.saveUsefulRun)

    #expect(timing.expandedRunReviewProjection.title == "Reviewed")
    #expect(timing.expandedRunReviewProjection.detail == "Useful normal run")
    #expect(timing.expandedRunReviewProjection.role == .active)
}

@MainActor
@Test func uiPresentationProjectionsHumanizeCanonicalIdentifiers() async throws {
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    let flag = try decoder.decode(
        TimingReviewFlagDTO.self,
        from: Data(
            """
            {
              "id": "41414141-4141-4141-8141-414141414141",
              "session_id": "42424242-4242-4242-8242-424242424242",
              "flag_type": "possible_forgotten_timer",
              "status": "open",
              "severity": "high",
              "confidence": 0.88,
              "reason_code": "place_changed_after_long_idle_gap",
              "user_message": "Timer may have kept running after the place changed.",
              "resolution_note": null
            }
            """.utf8
        )
    )
    let forgotten = ForgottenTimerEvidenceProjection.make(flags: [flag])

    let preflightCheck = try decoder.decode(
        PreflightCheckDTO.self,
        from: Data(
            """
            {
              "id": "51515151-5151-4151-8151-515151515151",
              "activity_id": "52525252-5252-4252-8252-525252525252",
              "check_text": "Check the real blocker before starting.",
              "state": "needs_attention",
              "source": "resource_dependency",
              "confidence": 0.76,
              "failure_count": 2,
              "evidence_count": 2,
              "evidence_summary": "Two confirmed detours suggested this check."
            }
            """.utf8
        )
    )
    let preflight = PreflightEvidenceProjection.make(
        activityName: "Dynamic presentation activity",
        checks: [preflightCheck],
        resourceDependencies: [],
        latestDetourNote: nil
    )

    var timestamps = [Date(timeIntervalSince1970: 1_775_160_000)]
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "53535353-5353-4353-8353-535353535353")!,
        activityName: "Presentation queue activity",
        deviceId: "ios-uat-presentation-copy",
        eventStore: InMemoryPendingTimingEventStore(),
        now: { timestamps.removeFirst() }
    )
    await timing.startRun()

    var visiblePieces: [String] = [forgotten.eyebrow]
    visiblePieces.append(contentsOf: forgotten.evidenceLines)
    visiblePieces.append(contentsOf: forgotten.chips)
    visiblePieces.append(contentsOf: preflight.evidenceLines)
    visiblePieces.append(contentsOf: preflight.chips)
    for row in timing.pendingSyncRows {
        visiblePieces.append(row.title)
        visiblePieces.append(row.detail)
    }
    let visibleText = visiblePieces.joined(separator: " ")

    #expect(visibleText.contains("Possible forgotten timer"))
    #expect(visibleText.contains("Place changed after a long idle gap"))
    #expect(visibleText.contains("Repeated resource friction"))
    #expect(visibleText.contains("Needs attention"))
    #expect(visibleText.contains("Timer started"))
    #expect(!visibleText.contains("possible_forgotten_timer"))
    #expect(!visibleText.contains("place_changed_after_long_idle_gap"))
    #expect(!visibleText.contains("resource_dependency"))
    #expect(!visibleText.contains("needs_attention"))
    #expect(!visibleText.contains("session_started"))
    #expect(!visibleText.localizedCaseInsensitiveContains("mutation"))
    #expect(visibleText.contains("Sync item"))
}

@Test func timingInstrumentLayoutKeepsInfoLaneSeparatedFromTimerRing() {
    let compactCardWidth: CGFloat = 332
    let regularCardWidth: CGFloat = 520

    #expect(TimingInstrumentLayout.instrumentCardPadding >= 12)
    #expect(TimingInstrumentLayout.instrumentSectionSpacing >= 10)
    #expect(TimingInstrumentLayout.badgeFontSize >= 10)
    #expect(TimingInstrumentLayout.badgeMinHeight >= 24)
    #expect(TimingInstrumentLayout.infoLaneSpacing(for: compactCardWidth) > 10)
    #expect(TimingInstrumentLayout.infoLaneSpacing(for: compactCardWidth) >= 24)
    #expect(TimingInstrumentLayout.infoLaneWidth(for: compactCardWidth) >= 190)
    #expect(TimingInstrumentLayout.infoLaneSpacing(for: regularCardWidth) > TimingInstrumentLayout.infoLaneSpacing(for: compactCardWidth))
    #expect(TimingInstrumentLayout.infoLaneSpacing(for: regularCardWidth) <= 34)
    #expect(TimingInstrumentLayout.primaryButtonHeight >= 46)
    #expect(TimingInstrumentLayout.secondaryButtonHeight >= 44)
    #expect(TimingInstrumentLayout.secondaryButtonUsesSystemBorderedStyle)
    #expect(TimingInstrumentLayout.secondaryButtonUsesCompactVerticalLabel)
    #expect(TimingInstrumentLayout.bottomDockIsAnchoredToSafeArea)
    #expect(TimingInstrumentLayout.bottomDockReservesScrollContentSpace)
    #expect(TimingInstrumentLayout.bottomDockUsesSheetShape)
    #expect(TimingInstrumentLayout.bottomDockUsesOverlayAttachment)
    #expect(TimingInstrumentLayout.bottomDockExtendsThroughBottomSafeArea)
    #expect(TimingInstrumentLayout.bottomDockSafeAreaFillMinimum >= 12)
    #expect(TimingInstrumentLayout.bottomDockSafeAreaExtension(for: 34) == 34)
    #expect(TimingInstrumentLayout.bottomDockAttachmentOffset(for: 34) == 34)
    #expect(TimingInstrumentLayout.bottomDockBottomPadding(for: 34) >= ParallaxBottomSheetLayout.bottomContentPadding + 68)
    #expect(TimingInstrumentLayout.stepPreviewDoesNotDuplicateMainNoteAction)
    #expect(!TimingInstrumentLayout.bottomDockRepeatsPrimaryActions)
}

@Test func pullUpDrawerSurfacesUseBottomAttachedSheetTreatment() {
    #expect(ParallaxBottomSheetLayout.topCornerRadius >= 22)
    #expect(ParallaxBottomSheetLayout.bottomCornerRadius == 0)
    #expect(ParallaxBottomSheetLayout.handleWidth >= 42)
    #expect(ParallaxBottomSheetLayout.handleHeight >= 4)
    #expect(ParallaxBottomSheetLayout.precedingContentGap >= 24)
    #expect(ParallaxBottomSheetLayout.bottomContentPadding >= 10)
    #expect(ParallaxBottomSheetLayout.usesFlatBottomShape)
    #expect(!ParallaxBottomSheetLayout.usesFloatingCardShape)
}

@Test func disabledDrawerActionsKeepReadableLabels() {
    #expect(ParallaxDrawerActionLayout.disabledLabelOpacity >= 0.82)
    #expect(ParallaxDrawerActionLayout.disabledBackgroundOpacity >= 0.72)
    #expect(ParallaxDrawerActionLayout.disabledPrimaryUsesNeutralFill)
    #expect(!ParallaxDrawerActionLayout.disabledActionsHideText)
}

@Test func reviewBottomDockUsesSameAttachedSafeAreaTreatment() {
    #expect(TimingReviewDockLayout.bottomDockUsesOverlayAttachment)
    #expect(TimingReviewDockLayout.bottomDockExtendsThroughBottomSafeArea)
    #expect(TimingReviewDockLayout.bottomDockSafeAreaExtension(for: 34) == 34)
    #expect(TimingReviewDockLayout.bottomDockAttachmentOffset(for: 34) == 34)
    #expect(TimingReviewDockLayout.bottomDockBottomPadding(for: 34) >= ParallaxBottomSheetLayout.bottomContentPadding + 68)
    #expect(TimingReviewDockLayout.bottomDockScrollReservation >= 220)
    #expect(!TimingReviewDockLayout.summaryRowShowsNavigationChevron)
}

@Test func launcherBottomSheetUsesAttachedSafeAreaTreatment() {
    #expect(TimingLauncherSheetLayout.bottomSheetUsesOverlayAttachment)
    #expect(TimingLauncherSheetLayout.bottomSheetExtendsThroughBottomSafeArea)
    #expect(TimingLauncherSheetLayout.bottomSheetSafeAreaExtension(for: 34) == 34)
    #expect(TimingLauncherSheetLayout.bottomSheetAttachmentOffset(for: 34) == 34)
    #expect(TimingLauncherSheetLayout.bottomSheetBottomPadding(for: 34) >= ParallaxBottomSheetLayout.bottomContentPadding + 68)
    #expect(TimingLauncherSheetLayout.directActionsUseBalancedHeights)
    #expect(TimingLauncherSheetLayout.directActionHeight == TimingInstrumentLayout.primaryButtonHeight)
    #expect(TimingLauncherSheetLayout.directActionCornerRadius <= 20)
}

@Test func nonInteractiveSummaryAndStepRowsDoNotShowNavigationChevrons() {
    #expect(!ParallaxStaticRowAccessoryLayout.nonInteractiveSummaryRowsShowChevron)
    #expect(!ParallaxStaticRowAccessoryLayout.nonInteractiveStepRowsShowChevron)
}

@Test func checkpointSetupContextBadgeDoesNotPretendToBeAnAction() {
    #expect(!CheckpointSetupPolishLayout.contextBadgeImpliesAction)
    #expect(CheckpointSetupPolishLayout.contextBadgeUsesInformationalCopy)
}

@Test func terminalTemporalDrawerActionsDoNotShowNavigationChevron() {
    #expect(TemporalDrawerActionLayout.navigationActionsShowChevron)
    #expect(!TemporalDrawerActionLayout.terminalActionsShowChevron)
    #expect(!TemporalDrawerActionLayout.directActionsShowChevron)
    #expect(!TemporalDrawerActionLayout.disabledActionsHideText)
}

@MainActor
@Test func reviewedRunCanStartAgainAsNewSession() async throws {
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_140_000),
        Date(timeIntervalSince1970: 1_775_140_060),
        Date(timeIntervalSince1970: 1_775_140_120),
        Date(timeIntervalSince1970: 1_775_140_180),
    ]
    let store = InMemoryPendingTimingEventStore()
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "31313131-3131-4131-8131-313131313131")!,
        activityName: "Start again activity",
        deviceId: "ios-uat-start-again",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )

    await timing.startRun()
    await timing.finishRun()
    await timing.saveReviewDecision(.markUnusual)
    let reviewedSessionId = timing.sessionId

    await timing.startRun()

    let events = try await store.load()
    #expect(timing.status == .running)
    #expect(timing.sessionId != reviewedSessionId)
    #expect(timing.reviewDecision == nil)
    #expect(timing.elapsedSeconds == 0)
    #expect(events.last?.eventType == .sessionStarted)
    #expect(events.last?.sessionId == timing.sessionId)
}

@MainActor
@Test func localQuickCaptureRefreshesTemporalHomeToSyncPendingSurface() async throws {
    let store = InMemoryPendingTimingEventStore()
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "32323232-3232-4232-8232-323232323232")!,
        activityName: "Sync pending surface activity",
        deviceId: "ios-uat-sync-pending-surface",
        eventStore: store
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await temporal.saveQuickCapture("Offline note that must surface pending sync")

    #expect(timing.pendingEventCount == 1)
    #expect(timing.projection.hasPendingSync)
    #expect(temporal.surfaceState == .syncPending)
}

@MainActor
@Test func temporalHomeProjectionRefreshesLoadedPendingQueueToSyncPendingSurface() async throws {
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_141_000),
    ]
    let store = InMemoryPendingTimingEventStore()
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "34343434-3434-4434-8434-343434343434")!,
        activityName: "Persisted sync pending activity",
        deviceId: "ios-uat-sync-pending-refresh",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await timing.startRun()

    #expect(timing.pendingEventCount == 1)
    #expect(timing.projection.hasPendingSync)
    #expect(temporal.surfaceState == .defaultHome)

    temporal.refreshSurfaceFromTimingProjection()

    #expect(temporal.surfaceState == .syncPending)
}

@MainActor
@Test func forgottenTimerDrawerLoadsRealReviewFlagAndTrimResolvesIt() async throws {
    let sessionId = UUID(uuidString: "41414141-4141-4141-8141-414141414141")!
    let flagId = UUID(uuidString: "51515151-5151-4151-8151-515151515151")!
    let transport = RecordingHTTPTransport(responses: [
        .json(
            200,
            """
            [{
              "id": "\(flagId.uuidString)",
              "user_id": "11111111-1111-4111-8111-111111111111",
              "session_id": "\(sessionId.uuidString)",
              "snapshot_id": null,
              "flag_type": "possible_forgotten_timer",
              "status": "open",
              "severity": "high",
              "confidence": 0.82,
              "reason_code": "place_changed_after_long_idle_gap",
              "user_message": "Timer may have kept running after the place changed.",
              "evidence": {"idle_gap_seconds": 2700},
              "created_at": "2026-05-06T00:00:00Z",
              "resolved_at": null,
              "resolution_note": null
            }]
            """
        ),
        .json(
            200,
            """
            {
              "id": "\(flagId.uuidString)",
              "user_id": "11111111-1111-4111-8111-111111111111",
              "session_id": "\(sessionId.uuidString)",
              "snapshot_id": null,
              "flag_type": "possible_forgotten_timer",
              "status": "resolved",
              "severity": "high",
              "confidence": 0.82,
              "reason_code": "place_changed_after_long_idle_gap",
              "user_message": "Timer may have kept running after the place changed.",
              "evidence": {"idle_gap_seconds": 2700},
              "created_at": "2026-05-06T00:00:00Z",
              "resolved_at": "2026-05-06T00:10:00Z",
              "resolution_note": "Trimmed at place change."
            }
            """
        ),
    ])
    let eventStore = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_777_000_000),
        Date(timeIntervalSince1970: 1_777_003_900),
        Date(timeIntervalSince1970: 1_777_003_901),
    ]
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "61616161-6161-4161-8161-616161616161")!,
        activityName: "Dynamic forgotten timer activity",
        sessionId: sessionId,
        deviceId: "ios-forgotten-flag-test",
        eventStore: eventStore,
        apiClient: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
            transport: transport
        ),
        now: { timestamps.removeFirst() }
    )

    await timing.startRun()
    await timing.finishRun()
    await timing.refreshForgottenTimerEvidence()

    #expect(timing.forgottenTimerEvidence.primaryFlagId == flagId)
    #expect(timing.forgottenTimerEvidence.title == "Timer may have kept running?")
    #expect(timing.forgottenTimerEvidence.evidenceLines.contains("Timer may have kept running after the place changed."))
    #expect(timing.forgottenTimerEvidence.homeRowTitle == "Timer may have kept running?")
    #expect(timing.forgottenTimerEvidence.homeRowDetail == "Timer may have kept running after the place changed.")
    #expect(timing.forgottenTimerEvidence.homeRowTitle != "Evening reset correct")

    await timing.trimForgottenTimerAtPlaceChange()

    let requests = await transport.recordedRequests()
    #expect(requests.map(\.path) == [
        "/v1/timing/sessions/\(sessionId.uuidString)/review-flags",
        "/v1/timing/review-flags/\(flagId.uuidString)",
    ])
    let patchBody = try #require(requests.last?.bodyData)
    let patchJSON = try #require(try JSONSerialization.jsonObject(with: patchBody) as? [String: Any])
    #expect(patchJSON["status"] as? String == "resolved")
    #expect((patchJSON["resolution_note"] as? String)?.contains("Trimmed") == true)
    #expect(try await eventStore.load().last?.eventType == .userCorrectionApplied)
}

@MainActor
@Test func forgottenTimerNotSureSnoozesReviewFlagWithoutChangingTotals() async throws {
    let sessionId = UUID(uuidString: "42424242-4242-4242-8242-424242424242")!
    let flagId = UUID(uuidString: "52525252-5252-4252-8252-525252525252")!
    let transport = RecordingHTTPTransport(responses: [
        .json(
            200,
            """
            [{
              "id": "\(flagId.uuidString)",
              "user_id": "11111111-1111-4111-8111-111111111111",
              "session_id": "\(sessionId.uuidString)",
              "snapshot_id": null,
              "flag_type": "possible_forgotten_timer",
              "status": "open",
              "severity": "medium",
              "confidence": 0.65,
              "reason_code": "long_idle_gap",
              "user_message": "Timer may need another look.",
              "evidence": {"idle_gap_seconds": 1900},
              "created_at": "2026-05-06T00:00:00Z",
              "resolved_at": null,
              "resolution_note": null
            }]
            """
        ),
        .json(
            200,
            """
            {
              "id": "\(flagId.uuidString)",
              "user_id": "11111111-1111-4111-8111-111111111111",
              "session_id": "\(sessionId.uuidString)",
              "snapshot_id": null,
              "flag_type": "possible_forgotten_timer",
              "status": "snoozed",
              "severity": "medium",
              "confidence": 0.65,
              "reason_code": "long_idle_gap",
              "user_message": "Timer may need another look.",
              "evidence": {"idle_gap_seconds": 1900},
              "created_at": "2026-05-06T00:00:00Z",
              "resolved_at": null,
              "resolution_note": "User deferred forgotten timer decision."
            }
            """
        ),
    ])
    var timestamps = [
        Date(timeIntervalSince1970: 1_777_010_000),
        Date(timeIntervalSince1970: 1_777_010_960),
        Date(timeIntervalSince1970: 1_777_010_961),
    ]
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "62626262-6262-4262-8262-626262626262")!,
        activityName: "Dynamic deferred timer activity",
        sessionId: sessionId,
        deviceId: "ios-forgotten-defer-test",
        eventStore: InMemoryPendingTimingEventStore(),
        apiClient: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
            transport: transport
        ),
        now: { timestamps.removeFirst() }
    )

    await timing.startRun()
    await timing.finishRun()
    let elapsedBefore = timing.elapsedSeconds
    let activeBefore = timing.activeSeconds
    await timing.refreshForgottenTimerEvidence()

    await timing.deferForgottenTimerDecision()

    #expect(timing.elapsedSeconds == elapsedBefore)
    #expect(timing.activeSeconds == activeBefore)
    let patchBody = try #require(await transport.recordedRequests().last?.bodyData)
    let patchJSON = try #require(try JSONSerialization.jsonObject(with: patchBody) as? [String: Any])
    #expect(patchJSON["status"] as? String == "snoozed")
    #expect(patchJSON["resolution_note"] as? String == "User deferred forgotten timer decision.")
}

@MainActor
@Test func forgottenTimerRefreshUsesRemoteSessionIdAfterOnlineSync() async throws {
    let localActivityId = UUID(uuidString: "63636363-6363-4363-8363-636363636363")!
    let remoteActivityId = UUID(uuidString: "64646464-6464-4464-8464-646464646464")!
    let localSessionId = UUID(uuidString: "43434343-4343-4343-8343-434343434343")!
    let remoteSessionId = UUID(uuidString: "44444444-4444-4444-8444-444444444444")!
    let eventStore = InMemoryPendingTimingEventStore()
    let stateStore = InMemoryPendingSyncStateStore()
    let transport = RecordingHTTPTransport(responses: [
        .json(200, #"{"recommended_activity_id": null}"#),
        .json(201, #"{"id": "\#(remoteActivityId.uuidString)"}"#),
        .json(201, #"{"id": "\#(remoteSessionId.uuidString)"}"#),
        .json(201, #"{"id": "45454545-4545-4545-8545-454545454545"}"#),
        .json(200, #"{"id": "\#(remoteSessionId.uuidString)"}"#),
        .json(200, #"[]"#),
    ])
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
        transport: transport
    )
    let syncService = PendingSyncService(
        client: client,
        eventStore: eventStore,
        preflightDecisionStore: InMemoryPendingPreflightDecisionStore(),
        syncStateStore: stateStore
    )
    var timestamps = [
        Date(timeIntervalSince1970: 1_777_020_000),
        Date(timeIntervalSince1970: 1_777_020_300),
    ]
    let timing = TimingSliceViewModel(
        activityId: localActivityId,
        activityName: "Dynamic remote flag activity",
        sessionId: localSessionId,
        deviceId: "ios-remote-flag-session-test",
        eventStore: eventStore,
        pendingSyncService: syncService,
        pendingSyncContext: PendingSyncContext(
            localActivityId: localActivityId,
            activityDisplayName: "Dynamic remote flag activity",
            deviceId: "ios-remote-flag-session-test"
        ),
        apiClient: client,
        now: { timestamps.removeFirst() }
    )

    await timing.startRun()
    await timing.finishRun()
    await timing.refreshForgottenTimerEvidence()

    #expect(await transport.recordedRequests().last?.path == "/v1/timing/sessions/\(remoteSessionId.uuidString)/review-flags")
}

private struct RecordedRequest: Equatable, Sendable {
    let method: String
    let path: String
    let headers: [String: String]
    let body: String?

    var bodyData: Data? {
        body.flatMap { $0.data(using: .utf8) }
    }

    func header(_ key: String) -> String? {
        headers.first { $0.key.caseInsensitiveCompare(key) == .orderedSame }?.value
    }
}

private struct MockResponse: Sendable {
    let statusCode: Int
    let body: String

    static func json(_ statusCode: Int, _ body: String) -> MockResponse {
        MockResponse(statusCode: statusCode, body: body)
    }
}

private actor RecordingHTTPTransport: ParallaxHTTPTransport {
    private var responses: [MockResponse]
    private var requests: [RecordedRequest] = []

    init(responses: [MockResponse]) {
        self.responses = responses
    }

    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let headers = Dictionary(
            uniqueKeysWithValues: request.allHTTPHeaderFields?.map { ($0.key, $0.value) } ?? []
        )
        requests.append(
            RecordedRequest(
                method: request.httpMethod ?? "",
                path: request.url?.path ?? "",
                headers: headers,
                body: request.httpBody.flatMap { String(data: $0, encoding: .utf8) }
            )
        )
        let response = responses.removeFirst()
        let url = request.url ?? URL(string: "http://127.0.0.1")!
        return (
            Data(response.body.utf8),
            HTTPURLResponse(
                url: url,
                statusCode: response.statusCode,
                httpVersion: "HTTP/1.1",
                headerFields: ["Content-Type": "application/json"]
            )!
        )
    }

    func recordedRequests() -> [RecordedRequest] {
        requests
    }
}
