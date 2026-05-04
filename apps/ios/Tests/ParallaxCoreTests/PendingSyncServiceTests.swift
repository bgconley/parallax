import Foundation
import ParallaxCore
import Testing

@Test func syncCreatesRemoteSessionBeforeUploadingQueuedTimingEvents() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(200, #"{"recommended_activity_id": null}"#),
        .json(201, #"{"id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}"#),
        .json(201, #"{"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}"#),
        .json(201, #"{"id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc"}"#),
        .json(200, #"{"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}"#),
        .json(200, #"{"id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd"}"#),
    ])
    let localActivityId = UUID(uuidString: "11111111-1111-4111-8111-111111111111")!
    let localSessionId = UUID(uuidString: "22222222-2222-4222-8222-222222222222")!
    let eventStore = InMemoryPendingTimingEventStore(events: [
        pendingEvent(.sessionStarted, sessionId: localSessionId, sequence: 1),
        pendingEvent(.sessionCompleted, sessionId: localSessionId, sequence: 2),
        pendingEvent(
            .reviewSaved,
            sessionId: localSessionId,
            sequence: 3,
            payload: [
                "decision": ModelUpdateDecision.saveUsefulRun.rawValue,
                "model_inclusion": ModelInclusion.full.rawValue,
                "scopes": "active_duration,wall_duration,friction_patterns",
            ]
        ),
    ])
    let preflightStore = InMemoryPendingPreflightDecisionStore()
    let stateStore = InMemoryPendingSyncStateStore()
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .bearer(token: "uat-token"),
        transport: transport
    )
    let service = PendingSyncService(
        client: client,
        eventStore: eventStore,
        preflightDecisionStore: preflightStore,
        syncStateStore: stateStore,
        now: { Date(timeIntervalSince1970: 1_775_000_000) }
    )

    let result = try await service.sync(
        context: PendingSyncContext(
            localActivityId: localActivityId,
            activityDisplayName: "Clean pots and pans",
            deviceId: "ios-uat-device"
        )
    )

    #expect(result.uploadedTimingEventCount == 3)
    #expect(try await eventStore.load().isEmpty)
    let paths = await transport.recordedRequests().map(\.path)
    #expect(paths == [
        "/v1/activities/resolve",
        "/v1/activities",
        "/v1/timing/sessions",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/events",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/complete",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/review",
    ])
    let headers = await transport.recordedRequests().map(\.authorization)
    #expect(headers.allSatisfy { $0 == "Bearer uat-token" })
    let state = try await stateStore.load()
    #expect(state.session(localSessionId: localSessionId)?.remoteSessionId == UUID(uuidString: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))
}

@Test func syncKeepsQueuedEventsWhenBearerRequestFails() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(401, #"{"error_code": "unauthorized"}"#),
    ])
    let eventStore = InMemoryPendingTimingEventStore(events: [
        pendingEvent(
            .sessionStarted,
            sessionId: UUID(uuidString: "22222222-2222-4222-8222-222222222222")!,
            sequence: 1
        ),
    ])
    let service = PendingSyncService(
        client: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .bearer(token: "bad-token"),
            transport: transport
        ),
        eventStore: eventStore,
        preflightDecisionStore: InMemoryPendingPreflightDecisionStore(),
        syncStateStore: InMemoryPendingSyncStateStore()
    )

    await #expect(throws: ParallaxAPIError.requestFailed(statusCode: 401, body: #"{"error_code": "unauthorized"}"#)) {
        _ = try await service.sync(
            context: PendingSyncContext(
                localActivityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
                activityDisplayName: "Clean pots and pans",
                deviceId: "ios-uat-device"
            )
        )
    }
    #expect(try await eventStore.load().count == 1)
}

@Test func syncCreatesRemotePreflightCheckBeforeUploadingDecision() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(200, #"{"recommended_activity_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}"#),
        .json(201, #"{"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}"#),
        .json(200, #"{"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}"#),
    ])
    let localActivityId = UUID(uuidString: "11111111-1111-4111-8111-111111111111")!
    let localCheckId = UUID(uuidString: "44444444-4444-4444-8444-444444444444")!
    let preflightStore = InMemoryPendingPreflightDecisionStore(decisions: [
        PendingPreflightDecision(
            activityId: localActivityId,
            checkId: localCheckId,
            mutation: mutation(sequence: 5, prefix: "decide_preflight_check"),
            decision: .snooze,
            decidedAt: Date(timeIntervalSince1970: 1_775_000_000),
            reason: "already checked"
        ),
    ])
    let service = PendingSyncService(
        client: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .bearer(token: "uat-token"),
            transport: transport
        ),
        eventStore: InMemoryPendingTimingEventStore(),
        preflightDecisionStore: preflightStore,
        syncStateStore: InMemoryPendingSyncStateStore()
    )

    let result = try await service.sync(
        context: PendingSyncContext(
            localActivityId: localActivityId,
            activityDisplayName: "Clean pots and pans",
            deviceId: "ios-uat-device"
        )
    )

    #expect(result.uploadedPreflightDecisionCount == 1)
    #expect(try await preflightStore.load().isEmpty)
    let paths = await transport.recordedRequests().map(\.path)
    #expect(paths == [
        "/v1/activities/resolve",
        "/v1/activities/AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA/preflight-checks",
        "/v1/activities/AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA/preflight-checks/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/decision",
    ])
    let body = try #require(await transport.recordedRequests().last?.body?.data(using: .utf8))
    let json = try #require(try JSONSerialization.jsonObject(with: body) as? [String: Any])
    #expect(json["snoozed_until"] as? String != nil)
}

private func pendingEvent(
    _ eventType: TimingEventType,
    sessionId: UUID,
    sequence: Int,
    payload: [String: String] = [:]
) -> PendingTimingEvent {
    PendingTimingEvent(
        sessionId: sessionId,
        eventType: eventType,
        mutation: mutation(sequence: sequence, prefix: eventType.rawValue),
        clientTime: Date(timeIntervalSince1970: 1_775_000_000 + Double(sequence)),
        timerElapsedSeconds: sequence * 60,
        timerActiveSeconds: sequence * 50,
        captureMethod: .manualButton,
        payload: payload
    )
}

private func mutation(sequence: Int, prefix: String) -> MutationEnvelope {
    MutationEnvelope(
        idempotencyKey: "ios-uat-device:\(sequence)",
        clientMutationId: "\(prefix)-\(sequence)",
        clientDeviceId: "ios-uat-device",
        clientSequence: sequence,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )
}

private struct RecordedRequest: Equatable, Sendable {
    let method: String
    let path: String
    let authorization: String?
    let body: String?
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
        let body = request.httpBody.flatMap { String(data: $0, encoding: .utf8) }
        requests.append(
            RecordedRequest(
                method: request.httpMethod ?? "",
                path: request.url?.path ?? "",
                authorization: request.value(forHTTPHeaderField: "Authorization"),
                body: body
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
