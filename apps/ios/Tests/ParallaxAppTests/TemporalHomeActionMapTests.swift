import Foundation
import ParallaxApp
import ParallaxCore
import Testing

@Test func phase10ActionMapJsonMatchesSwiftActionEnum() throws {
    let payload = try loadPhase10ActionMap()
    let jsonIds = Set(payload.actions.map(\.id))
    let swiftIds = Set(TemporalHomeAction.allCases.map(\.rawValue))

    #expect(jsonIds == swiftIds)
    #expect(payload.actions.count == 55)

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
    ]
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        activityName: "Clean pots and pans",
        sessionId: UUID(uuidString: "22222222-2222-4222-8222-222222222222")!,
        deviceId: "phase10-action-test",
        eventStore: store,
        now: { timestamps.removeFirst() }
    )
    let temporal = TemporalHomeViewModel(timingViewModel: timing, initialSurface: .defaultHome)

    await temporal.perform(.currentFocusDefault)
    #expect(temporal.surfaceState == .expandedTimingRun)

    await temporal.perform(.preflightRowDefault)
    #expect(temporal.activeDrawer == .phase8(.preflightEvidence))

    await temporal.perform(.quickCaptureDefault)
    let capture = try #require(try await store.load().last)
    #expect(capture.eventType == .annotationCaptured)
    #expect(capture.payload["source"] == "temporal_home")

    await temporal.perform(.askTimeDefault)
    let queryIntent = try #require(try await store.load().last)
    #expect(temporal.surfaceState == .groundedAnswer)
    #expect(temporal.lastTemporalQuestion == "How long does clean pots and pans usually take?")
    #expect(queryIntent.eventType == .intentRecorded)
    #expect(queryIntent.payload["api_path"] == "/v1/temporal/query")
    #expect(queryIntent.payload["include_raw_quotes"] == "false")
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
