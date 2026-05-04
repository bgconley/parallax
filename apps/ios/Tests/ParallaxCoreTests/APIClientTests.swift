import Foundation
import ParallaxCore
import Testing

@Test func appendTimingEventRequestUsesCanonicalMutationEnvelopeAndDevAuthHeader() throws {
    let userId = UUID(uuidString: "11111111-1111-1111-1111-111111111111")!
    let sessionId = UUID(uuidString: "22222222-2222-2222-2222-222222222222")!
    let client = ParallaxAPIClient(baseURL: URL(string: "http://127.0.0.1:18000")!, userId: userId)
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:10",
        clientMutationId: "mutation-10",
        clientDeviceId: "device-1",
        clientSequence: 10,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )
    let event = PendingTimingEvent(
        sessionId: sessionId,
        eventType: .sessionStarted,
        mutation: mutation,
        clientTime: Date(timeIntervalSince1970: 1_775_000_001),
        timerElapsedSeconds: 0,
        timerActiveSeconds: 0
    )

    let request = try client.appendTimingEventRequest(event)

    #expect(request.httpMethod == "POST")
    #expect(request.url?.path == "/v1/timing/sessions/\(sessionId.uuidString)/events")
    #expect(request.value(forHTTPHeaderField: "X-Parallax-User-Id") == userId.uuidString)

    let json = try #require(request.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    let mutationJson = try #require(json["mutation"] as? [String: Any])
    #expect(json["event_type"] as? String == "session_started")
    #expect(json["timer_elapsed_seconds"] as? Int == 0)
    #expect(mutationJson["idempotency_key"] as? String == "device-1:10")
    #expect(mutationJson["client_device_id"] as? String == "device-1")
    #expect(mutationJson["client_timestamp"] as? String != nil)
    #expect(mutationJson["client_created_at"] == nil)
}

@Test func bearerAuthRequestDoesNotSendDevelopmentHeader() throws {
    let sessionId = UUID(uuidString: "22222222-2222-2222-2222-222222222222")!
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .bearer(token: "uat-token")
    )
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:10",
        clientMutationId: "mutation-10",
        clientDeviceId: "device-1",
        clientSequence: 10,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )
    let event = PendingTimingEvent(
        sessionId: sessionId,
        eventType: .sessionStarted,
        mutation: mutation,
        clientTime: Date(timeIntervalSince1970: 1_775_000_001)
    )

    let request = try client.appendTimingEventRequest(event)

    #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer uat-token")
    #expect(request.value(forHTTPHeaderField: "X-Parallax-User-Id") == nil)
}

@Test func missingBearerTokenIsRejectedBeforeRequestLeavesClient() throws {
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .bearer(token: "   ")
    )
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:10",
        clientMutationId: "mutation-10",
        clientDeviceId: "device-1",
        clientSequence: 10,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )

    #expect(throws: ParallaxAPIError.invalidAuthConfiguration) {
        _ = try client.createActivityRequest(displayName: "Clean pots and pans", mutation: mutation)
    }
}

@Test func runtimeConfigRequiresBearerTokenForExternalBearerMode() throws {
    #expect(throws: ParallaxRuntimeConfigError.missingBearerToken) {
        _ = try ParallaxRuntimeConfig.load(environment: [
            "PARALLAX_API_BASE_URL": "http://127.0.0.1:18000",
            "PARALLAX_AUTH_MODE": "external_bearer",
        ])
    }

    let config = try #require(try ParallaxRuntimeConfig.load(environment: [
        "PARALLAX_API_BASE_URL": "http://127.0.0.1:18000",
        "PARALLAX_AUTH_MODE": "external_bearer",
        "PARALLAX_BEARER_TOKEN": "uat-token",
        "PARALLAX_ACTIVITY_NAME": "Clean the kitchen",
        "PARALLAX_DEVICE_ID": "ios-uat-device",
    ]))
    #expect(config.apiBaseURL.absoluteString == "http://127.0.0.1:18000")
    #expect(config.auth == .bearer(token: "uat-token"))
    #expect(config.activityName == "Clean the kitchen")
    #expect(config.deviceId == "ios-uat-device")
}

@Test func annotationRequestCarriesCaptureMethodInMetadata() throws {
    let userId = UUID(uuidString: "33333333-3333-3333-3333-333333333333")!
    let sessionId = UUID(uuidString: "44444444-4444-4444-4444-444444444444")!
    let client = ParallaxAPIClient(baseURL: URL(string: "http://127.0.0.1:18000")!, userId: userId)
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:11",
        clientMutationId: "mutation-11",
        clientDeviceId: "device-1",
        clientSequence: 11,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )

    let request = try client.createAnnotationRequest(
        sessionId: sessionId,
        mutation: mutation,
        rawText: "I had to find the sponge.",
        occurredAt: Date(timeIntervalSince1970: 1_775_000_002),
        captureMethod: .voice
    )
    let json = try #require(request.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    let metadata = try #require(json["metadata"] as? [String: Any])

    #expect(request.url?.path == "/v1/timing/sessions/\(sessionId.uuidString)/annotations")
    #expect(json["input_mode"] as? String == "voice")
    #expect(json["raw_text"] as? String == "I had to find the sponge.")
    #expect(metadata["capture_method"] as? String == "voice")

    let manualRequest = try client.createAnnotationRequest(
        sessionId: sessionId,
        mutation: mutation,
        rawText: "Started by tapping the timer.",
        occurredAt: Date(timeIntervalSince1970: 1_775_000_003),
        captureMethod: .manualButton
    )
    let manualJson = try #require(manualRequest.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    let manualMetadata = try #require(manualJson["metadata"] as? [String: Any])
    #expect(manualJson["input_mode"] as? String == "text")
    #expect(manualMetadata["capture_method"] as? String == "manual_timer_button")
}

@Test func sessionLifecycleRequestsUseCanonicalPathsAndReviewScopes() throws {
    let userId = UUID(uuidString: "55555555-5555-5555-5555-555555555555")!
    let activityId = UUID(uuidString: "66666666-6666-6666-6666-666666666666")!
    let sessionId = UUID(uuidString: "77777777-7777-7777-7777-777777777777")!
    let client = ParallaxAPIClient(baseURL: URL(string: "http://127.0.0.1:18000")!, userId: userId)
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:12",
        clientMutationId: "mutation-12",
        clientDeviceId: "device-1",
        clientSequence: 12,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )

    let create = try client.createTimingSessionRequest(
        activityId: activityId,
        clientSessionId: "ios-session-1",
        mode: .wholeTask,
        mutation: mutation
    )
    let complete = try client.completeTimingSessionRequest(
        sessionId: sessionId,
        mutation: mutation,
        completedAt: Date(timeIntervalSince1970: 1_775_000_900),
        timerElapsedSeconds: 900,
        timerActiveSeconds: 780
    )
    let review = try client.reviewTimingSessionRequest(
        sessionId: sessionId,
        mutation: mutation,
        decision: .saveUsefulRun,
        modelInclusion: .full,
        scopes: [.activeDuration, .wallDuration, .frictionPatterns],
        userNote: "Useful normal run."
    )

    #expect(create.url?.path == "/v1/timing/sessions")
    #expect(complete.url?.path == "/v1/timing/sessions/\(sessionId.uuidString)/complete")
    #expect(review.url?.path == "/v1/timing/sessions/\(sessionId.uuidString)/review")

    let reviewJson = try #require(review.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    #expect(reviewJson["decision"] as? String == "save_useful_run")
    #expect(reviewJson["model_inclusion"] as? String == "full")
    #expect(reviewJson["scopes"] as? [String] == ["active_duration", "wall_duration", "friction_patterns"])

    let discard = try client.discardTimingSessionRequest(
        sessionId: sessionId,
        mutation: mutation,
        decision: .discardTimingKeepNote,
        userNote: "Keep the note, drop the timing."
    )
    #expect(discard.url?.path == "/v1/timing/sessions/\(sessionId.uuidString)/discard")
    let discardJson = try #require(discard.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    #expect(discardJson["decision"] as? String == "discard_timing_keep_note")
    #expect(discardJson["model_inclusion"] as? String == "exclude")
    #expect(discardJson["scopes"] as? [String] == [])
}

@Test func preflightDecisionRequestUsesCanonicalPhase6LifecycleEndpoint() throws {
    let userId = UUID(uuidString: "88888888-8888-8888-8888-888888888888")!
    let activityId = UUID(uuidString: "99999999-9999-4999-8999-999999999999")!
    let checkId = UUID(uuidString: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")!
    let client = ParallaxAPIClient(baseURL: URL(string: "http://127.0.0.1:18000")!, userId: userId)
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:13",
        clientMutationId: "mutation-13",
        clientDeviceId: "device-1",
        clientSequence: 13,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )

    let request = try client.decidePreflightCheckRequest(
        activityId: activityId,
        checkId: checkId,
        mutation: mutation,
        decision: .snooze,
        snoozedUntil: Date(timeIntervalSince1970: 1_775_086_400),
        reason: "not needed this week"
    )

    #expect(request.httpMethod == "POST")
    #expect(request.url?.path == "/v1/activities/\(activityId.uuidString)/preflight-checks/\(checkId.uuidString)/decision")

    let json = try #require(request.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    #expect(json["decision"] as? String == "snooze")
    #expect(json["snoozed_until"] as? String != nil)
    #expect(json["reason"] as? String == "not needed this week")
}
