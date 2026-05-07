import Foundation
import ParallaxApp
import ParallaxCore
import Testing

@Test func phase10ActionMapJsonMatchesSwiftActionEnum() throws {
    let payload = try loadPhase10ActionMap()
    let jsonIds = Set(payload.actions.map(\.id))
    let swiftIds = Set(TemporalHomeAction.allCases.map(\.rawValue))

    #expect(jsonIds == swiftIds)
    #expect(payload.actions.count == 56)

    for action in payload.actions {
        let swiftAction = try #require(TemporalHomeAction(rawValue: action.id))
        let spec = TemporalHomeActionMap.spec(for: swiftAction)
        #expect(spec.action == swiftAction)
        #expect(spec.classification.rawValue == action.classification)
        #expect(spec.screenNode == action.screenNode)
    }
}

@MainActor
@Test func temporalHomeActionsRouteToDrawersNavigationAndLocalQueue() async throws {
    let store = InMemoryPendingTimingEventStore()
    var timestamps = [
        Date(timeIntervalSince1970: 1_775_100_000),
        Date(timeIntervalSince1970: 1_775_100_001),
        Date(timeIntervalSince1970: 1_775_100_002),
        Date(timeIntervalSince1970: 1_775_100_003),
        Date(timeIntervalSince1970: 1_775_100_004),
        Date(timeIntervalSince1970: 1_775_100_005),
    ]
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic test activity",
        sessionId: UUID(uuidString: "22222222-2222-4222-8222-222222222222")!,
        deviceId: "phase10-action-test",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await temporal.perform(.currentFocusDefault)
    #expect(temporal.showsLauncher)
    #expect(temporal.surfaceState == .defaultHome)

    temporal.dismissLauncher()
    await temporal.perform(.startTimerDefault)
    #expect(temporal.showsLauncher)
    #expect(temporal.surfaceState == .defaultHome)

    temporal.dismissLauncher()
    await timing.startRun()
    await temporal.perform(.currentFocusDefault)
    #expect(temporal.surfaceState == .expandedTimingRun)

    await temporal.perform(.preflightRowDefault)
    #expect(temporal.activeDrawer == .phase8(.preflightEvidence))

    let eventCountBeforeQuickCapture = try await store.load().count
    await temporal.perform(.quickCaptureDefault)
    #expect(temporal.activeDrawer == .quickCapture)
    #expect(try await store.load().count == eventCountBeforeQuickCapture)

    await temporal.saveQuickCapture("   ")
    #expect(temporal.activeDrawer == .quickCapture)
    #expect(try await store.load().count == eventCountBeforeQuickCapture)

    await temporal.saveQuickCapture("UAT typed quick capture")
    let capture = try #require(try await store.load().last)
    #expect(capture.eventType == .annotationCaptured)
    #expect(capture.payload["source"] == "temporal_home")
    #expect(capture.notePreview == "UAT typed quick capture")

    await temporal.perform(.askTimeDefault)
    #expect(temporal.activeDrawer == .askTime)
    #expect(try await store.load().count == eventCountBeforeQuickCapture + 1)
    await temporal.submitTemporalQuestion("How long does Dynamic test activity usually take?")
    let queryIntent = try #require(try await store.load().last)
    #expect(temporal.surfaceState == .groundedAnswer)
    #expect(temporal.lastTemporalQuestion == "How long does Dynamic test activity usually take?")
    #expect(queryIntent.eventType == .intentRecorded)
    #expect(queryIntent.payload["api_path"] == "/v1/temporal/query")
    #expect(queryIntent.payload["include_raw_quotes"] == "false")
}

@MainActor
@Test func askAnotherDoesNotSubmitPlaceholderQuestion() async throws {
    let store = InMemoryPendingTimingEventStore()
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic ask activity",
        sessionId: UUID(uuidString: "33333333-3333-4333-8333-333333333333")!,
        deviceId: "phase10-ask-placeholder-test",
        eventStore: store
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .groundedAnswer)

    await temporal.perform(.askAnotherGroundedAnswer)

    #expect(temporal.activeDrawer == .askTime)
    #expect(temporal.lastTemporalQuestion == nil)
    #expect(try await store.load().isEmpty)

    await temporal.submitTemporalQuestion("How long did this dynamic run take?")

    #expect(temporal.lastTemporalQuestion == "How long did this dynamic run take?")
    #expect((try await store.load()).allSatisfy { $0.notePreview != "Ask another grounded time question." })
}

@MainActor
@Test func temporalNavigationRoutesSyncAndAskToDrawersWithoutSyntheticState() async throws {
    let store = InMemoryPendingTimingEventStore()
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Dynamic navigation activity",
        deviceId: "phase10-navigation-test",
        eventStore: store
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    temporal.activeDrawer = .temporalNavigation
    temporal.performTemporalNavigation(.syncQueue)
    #expect(temporal.activeDrawer == .syncQueue)
    #expect(temporal.surfaceState == .defaultHome)
    #expect(try await store.load().isEmpty)

    temporal.activeDrawer = .temporalNavigation
    temporal.performTemporalNavigation(.askTime)
    #expect(temporal.activeDrawer == .askTime)
    #expect(temporal.surfaceState == .defaultHome)
    #expect(temporal.lastTemporalQuestion == nil)
    #expect(try await store.load().isEmpty)

    temporal.activeDrawer = .temporalNavigation
    temporal.performTemporalNavigation(.currentRun)
    #expect(temporal.activeDrawer == nil)
    #expect(temporal.surfaceState == .expandedTimingRun)

    temporal.activeDrawer = .temporalNavigation
    temporal.performTemporalNavigation(.needsReview)
    #expect(temporal.activeDrawer == nil)
    #expect(temporal.surfaceState == .needsReview)

    temporal.activeDrawer = .temporalNavigation
    temporal.performTemporalNavigation(.close)
    #expect(temporal.activeDrawer == nil)
    #expect(temporal.surfaceState == .needsReview)
}

private struct Phase10ActionMapPayload: Decodable {
    let actions: [Phase10MappedAction]
}

private struct Phase10MappedAction: Decodable {
    let id: String
    let screenNode: String
    let classification: String
}

private func loadPhase10ActionMap() throws -> Phase10ActionMapPayload {
    let testFile = URL(fileURLWithPath: #filePath)
    let repoRoot = testFile
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
    let url = repoRoot.appendingPathComponent("docs/phase10_temporal_home_interactions/action_map.json")
    let data = try Data(contentsOf: url)
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    return try decoder.decode(Phase10ActionMapPayload.self, from: data)
}
