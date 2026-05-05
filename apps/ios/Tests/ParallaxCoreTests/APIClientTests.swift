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
        _ = try client.createActivityRequest(displayName: "Dynamic test activity", mutation: mutation)
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
        "PARALLAX_ACTIVITY_NAME": "Dynamic configured activity",
        "PARALLAX_DEVICE_ID": "ios-uat-device",
    ]))
    #expect(config.apiBaseURL.absoluteString == "http://127.0.0.1:18000")
    #expect(config.auth == .bearer(token: "uat-token"))
    #expect(config.activityName == "Dynamic configured activity")
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
        rawText: "I had to find a missing resource.",
        occurredAt: Date(timeIntervalSince1970: 1_775_000_002),
        captureMethod: .voice
    )
    let json = try #require(request.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    let metadata = try #require(json["metadata"] as? [String: Any])

    #expect(request.url?.path == "/v1/timing/sessions/\(sessionId.uuidString)/annotations")
    #expect(json["input_mode"] as? String == "voice")
    #expect(json["raw_text"] as? String == "I had to find a missing resource.")
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

@Test func readHelpersUseCanonicalPathsWithoutMutationBodies() throws {
    let activityId = UUID(uuidString: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")!
    let sessionId = UUID(uuidString: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")!
    let answerId = UUID(uuidString: "cccccccc-cccc-4ccc-8ccc-cccccccccccc")!
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        userId: UUID(uuidString: "dddddddd-dddd-4ddd-8ddd-dddddddddddd")!
    )

    let requests = try [
        client.listActivitiesRequest(q: "mail", limit: 10),
        client.getActivityRequest(activityId: activityId),
        client.getActivityProfileRequest(activityId: activityId),
        client.listCheckpointsRequest(activityId: activityId),
        client.listPreflightChecksRequest(activityId: activityId),
        client.listResourceDependenciesRequest(activityId: activityId),
        client.getTimingSessionRequest(sessionId: sessionId),
        client.getTemporalQueryAnswerRequest(answerId: answerId),
    ]

    #expect(requests.map(\.httpMethod) == Array(repeating: "GET", count: requests.count))
    #expect(requests.map { $0.httpBody == nil }.allSatisfy { $0 })
    #expect(requests.map { $0.url?.path } == [
        "/v1/activities",
        "/v1/activities/\(activityId.uuidString)",
        "/v1/activities/\(activityId.uuidString)/profile",
        "/v1/activities/\(activityId.uuidString)/checkpoints",
        "/v1/activities/\(activityId.uuidString)/preflight-checks",
        "/v1/activities/\(activityId.uuidString)/resource-dependencies",
        "/v1/timing/sessions/\(sessionId.uuidString)",
        "/v1/temporal/query/\(answerId.uuidString)",
    ])
    #expect(requests[0].url?.query == "limit=10&q=mail")
}

@Test func phase10TemporalQueryRequestUsesCanonicalEndpointAndPrivacyDefault() throws {
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        userId: UUID(uuidString: "11111111-1111-1111-1111-111111111111")!
    )
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:14",
        clientMutationId: "mutation-14",
        clientDeviceId: "device-1",
        clientSequence: 14,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )
    let activityId = UUID(uuidString: "22222222-2222-4222-8222-222222222222")!

    let request = try client.createTemporalQueryRequest(
        mutation: mutation,
        question: "How long does Dynamic test activity take?",
        activityId: activityId,
        timeWindow: "last_90_days"
    )

    #expect(request.httpMethod == "POST")
    #expect(request.url?.path == "/v1/temporal/query")
    let json = try #require(request.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    #expect(json["question"] as? String == "How long does Dynamic test activity take?")
    #expect(json["activity_id"] as? String == activityId.uuidString)
    #expect(json["time_window"] as? String == "last_90_days")
    #expect(json["include_raw_quotes"] as? Bool == false)
}

@Test func phase10ReviewFlagRequestsUseCanonicalPromptEndpoints() throws {
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        userId: UUID(uuidString: "33333333-3333-4333-8333-333333333333")!
    )
    let sessionId = UUID(uuidString: "44444444-4444-4444-8444-444444444444")!
    let flagId = UUID(uuidString: "55555555-5555-4555-8555-555555555555")!
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:15",
        clientMutationId: "mutation-15",
        clientDeviceId: "device-1",
        clientSequence: 15,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )

    let list = try client.listTimingReviewFlagsRequest(sessionId: sessionId, status: .open)
    #expect(list.httpMethod == "GET")
    #expect(list.url?.path == "/v1/timing/sessions/\(sessionId.uuidString)/review-flags")
    #expect(list.url?.query == "status=open")

    let update = try client.updateTimingReviewFlagRequest(
        flagId: flagId,
        mutation: mutation,
        status: .dismissed,
        resolutionNote: "Not relevant to this run."
    )
    #expect(update.httpMethod == "PATCH")
    #expect(update.url?.path == "/v1/timing/review-flags/\(flagId.uuidString)")
    let json = try #require(update.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    #expect(json["status"] as? String == "dismissed")
    #expect(json["resolution_note"] as? String == "Not relevant to this run.")
}

@Test func phase10ExtractedEventRequestsUseCanonicalConfirmAndCorrectEndpoints() throws {
    let client = ParallaxAPIClient(
        baseURL: URL(string: "http://127.0.0.1:18000")!,
        userId: UUID(uuidString: "66666666-6666-4666-8666-666666666666")!
    )
    let eventId = UUID(uuidString: "77777777-7777-4777-8777-777777777777")!
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:16",
        clientMutationId: "mutation-16",
        clientDeviceId: "device-1",
        clientSequence: 16,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )

    let confirm = try client.confirmExtractedEventRequest(
        eventId: eventId,
        mutation: mutation,
        confirmationState: .ignored
    )
    #expect(confirm.url?.path == "/v1/timing/extracted-events/\(eventId.uuidString)/confirm")
    let confirmJson = try #require(confirm.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    #expect(confirmJson["confirmation_state"] as? String == "ignored")

    let correct = try client.correctExtractedEventRequest(
        eventId: eventId,
        mutation: mutation,
        spanType: .resourceDetour,
        frictionCategory: .resource,
        durationSeconds: 600,
        countPolicy: .wallOnly,
        countInWallTime: true,
        countInActiveTime: false,
        suggestedPreflightText: "Check the dynamic resource before starting.",
        userNote: "Corrected from drawer."
    )
    #expect(correct.url?.path == "/v1/timing/extracted-events/\(eventId.uuidString)/correct")
    let correctJson = try #require(correct.httpBody.flatMap { body in
        try JSONSerialization.jsonObject(with: body) as? [String: Any]
    })
    #expect(correctJson["span_type"] as? String == "resource_detour")
    #expect(correctJson["friction_category"] as? String == "resource")
    #expect(correctJson["duration_seconds"] as? Int == 600)
    #expect(correctJson["count_policy"] as? String == "wall_only")
    #expect(correctJson["count_in_wall_time"] as? Bool == true)
    #expect(correctJson["count_in_active_time"] as? Bool == false)
}
