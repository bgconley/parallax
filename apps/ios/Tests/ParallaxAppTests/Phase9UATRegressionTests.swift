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
    UserDefaults.standard.removeObject(forKey: "parallax.selectedActivityId.ios-uat-relaunch-device")
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
        config: ParallaxRuntimeConfig(
            apiBaseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .devHeader(userId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!),
            deviceId: "ios-uat-relaunch-device"
        ),
        apiClient: client,
        eventStoreFactory: { _ in InMemoryPendingTimingEventStore() }
    )

    await store.bootstrap()

    #expect(store.selectedActivity?.displayName == "Dynamic persisted activity")
    #expect(store.timingViewModel?.activityName == "Dynamic persisted activity")
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
    await temporal.perform(.reviewRunDefault)
    #expect(temporal.activeDrawer == nil)
    #expect(temporal.showsLauncher == false)
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
              "answer": null,
              "confidence": "very_low",
              "sample_size": 0,
              "time_window": null,
              "computed_facts": {},
              "limitations": ["No reviewed runs yet."],
              "evidence": [],
              "status": "pending"
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

    #expect(temporal.surfaceState == .groundedAnswer)
    #expect(timing.lastTemporalQueryAnswer?.id == UUID(uuidString: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))
    #expect(try await eventStore.load().isEmpty)
    let requests = await transport.recordedRequests()
    #expect(requests.map(\.path) == ["/v1/temporal/query"])
    let body = try #require(requests.first?.bodyData)
    let json = try #require(try JSONSerialization.jsonObject(with: body) as? [String: Any])
    #expect(json["question"] as? String == "How long does Dynamic ask activity usually take?")
    #expect(json["activity_id"] as? String == "44444444-4444-4444-8444-444444444444")
    #expect(json["include_raw_quotes"] as? Bool == false)
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
