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
            activityDisplayName: "Dynamic test activity",
            deviceId: "ios-uat-device"
        )
    )

    #expect(result.uploadedTimingEventCount == 3)
    #expect(try await eventStore.load().isEmpty)
    let requests = await transport.recordedRequests()
    let paths = requests.map(\.path)
    #expect(paths == [
        "/v1/activities/resolve",
        "/v1/activities",
        "/v1/timing/sessions",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/events",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/complete",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/review",
    ])
    let createActivityBody = try #require(requests.first(where: { $0.path == "/v1/activities" })?.body?.data(using: .utf8))
    let createActivityJSON = try #require(try JSONSerialization.jsonObject(with: createActivityBody) as? [String: Any])
    #expect(createActivityJSON["default_timing_mode"] as? String == MeasurementMode.wholeTask.rawValue)
    let headers = requests.map(\.authorization)
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
                activityDisplayName: "Dynamic test activity",
                deviceId: "ios-uat-device"
            )
        )
    }
    #expect(try await eventStore.load().count == 1)
}

@Test func syncUploadsAnnotationCapturedEventsThroughAnnotationEndpoint() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(200, #"{"recommended_activity_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}"#),
        .json(201, #"{"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}"#),
        .json(
            201,
            """
            {
              "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              "user_id": "99999999-9999-4999-8999-999999999999",
              "session_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              "checkpoint_run_id": null,
              "input_mode": "text",
              "raw_text": "UAT dynamic note should survive sync.",
              "redacted_text": null,
              "transcript_confidence": null,
              "audio_object_ref": null,
              "timer_elapsed_seconds": 60,
              "timer_active_seconds": 50,
              "occurred_at": "2026-05-05T00:00:00Z",
              "privacy_class": "normal",
              "status": "captured",
              "client_mutation_id": "annotation_captured-1",
              "client_device_id": "ios-uat-device",
              "idempotency_key": "ios-uat-device:1",
              "capture_context_snapshot_id": null,
              "capture_context_snapshot_ref": null,
              "metadata": {"capture_method": "manual_button"},
              "created_at": "2026-05-05T00:00:00Z",
              "updated_at": "2026-05-05T00:00:00Z"
            }
            """
        ),
    ])
    let localActivityId = UUID(uuidString: "11111111-1111-4111-8111-111111111111")!
    let localSessionId = UUID(uuidString: "22222222-2222-4222-8222-222222222222")!
    let eventStore = InMemoryPendingTimingEventStore(events: [
        pendingEvent(
            .annotationCaptured,
            sessionId: localSessionId,
            sequence: 1,
            notePreview: "UAT dynamic note should survive sync.",
            payload: ["source": "timing_session_friction"]
        ),
    ])
    let service = PendingSyncService(
        client: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .bearer(token: "uat-token"),
            transport: transport
        ),
        eventStore: eventStore,
        preflightDecisionStore: InMemoryPendingPreflightDecisionStore(),
        syncStateStore: InMemoryPendingSyncStateStore()
    )

    let result = try await service.sync(
        context: PendingSyncContext(
            localActivityId: localActivityId,
            activityDisplayName: "Dynamic test activity",
            deviceId: "ios-uat-device"
        )
    )

    #expect(result.uploadedTimingEventCount == 1)
    #expect(try await eventStore.load().isEmpty)
    let requests = await transport.recordedRequests()
    #expect(requests.map(\.path) == [
        "/v1/activities/resolve",
        "/v1/timing/sessions",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/annotations",
    ])
    let body = try #require(requests.last?.body?.data(using: .utf8))
    let json = try #require(try JSONSerialization.jsonObject(with: body) as? [String: Any])
    #expect(json["raw_text"] as? String == "UAT dynamic note should survive sync.")
    #expect(json["input_mode"] as? String == AnnotationInputMode.text.rawValue)
}

@Test func syncBindsConfirmedFrictionEvidenceToUploadedAnnotation() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(200, #"{"recommended_activity_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}"#),
        .json(201, #"{"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}"#),
        .json(
            201,
            """
            {
              "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              "user_id": "99999999-9999-4999-8999-999999999999",
              "session_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              "checkpoint_run_id": null,
              "input_mode": "text",
              "raw_text": "Dynamic friction note.",
              "redacted_text": null,
              "transcript_confidence": null,
              "audio_object_ref": null,
              "timer_elapsed_seconds": 60,
              "timer_active_seconds": 50,
              "occurred_at": "2026-05-05T00:00:00Z",
              "privacy_class": "normal",
              "status": "captured",
              "client_mutation_id": "annotation_captured-1",
              "client_device_id": "ios-uat-device",
              "idempotency_key": "ios-uat-device:1",
              "capture_context_snapshot_id": null,
              "capture_context_snapshot_ref": null,
              "metadata": {"source": "timing_session_friction", "capture_method": "manual_timer_button"},
              "created_at": "2026-05-05T00:00:00Z",
              "updated_at": "2026-05-05T00:00:00Z"
            }
            """
        ),
        .json(201, #"{"id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd"}"#),
        .json(201, #"{"id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"}"#),
    ])
    let localActivityId = UUID(uuidString: "11111111-1111-4111-8111-111111111111")!
    let localSessionId = UUID(uuidString: "22222222-2222-4222-8222-222222222222")!
    let eventStore = InMemoryPendingTimingEventStore(events: [
        pendingEvent(
            .annotationCaptured,
            sessionId: localSessionId,
            sequence: 1,
            notePreview: "Dynamic friction note.",
            payload: ["source": "timing_session_friction"]
        ),
        pendingEvent(
            .resourceDetourStarted,
            sessionId: localSessionId,
            sequence: 2,
            payload: [
                "resource_name": "Dynamic blocker",
                "count_policy": CountPolicy.wallOnly.rawValue,
            ]
        ),
        pendingEvent(
            .extractedEventCreated,
            sessionId: localSessionId,
            sequence: 3,
            payload: [
                "resource_name": "Dynamic blocker",
                "span_type": TemporalSpanType.resourceDetour.rawValue,
                "friction_category": TemporalFrictionCategory.resource.rawValue,
                "count_policy": CountPolicy.wallOnly.rawValue,
                "confirmation_state": "user_confirmed",
            ]
        ),
    ])
    let service = PendingSyncService(
        client: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .bearer(token: "uat-token"),
            transport: transport
        ),
        eventStore: eventStore,
        preflightDecisionStore: InMemoryPendingPreflightDecisionStore(),
        syncStateStore: InMemoryPendingSyncStateStore()
    )

    _ = try await service.sync(
        context: PendingSyncContext(
            localActivityId: localActivityId,
            activityDisplayName: "Dynamic test activity",
            deviceId: "ios-uat-device"
        )
    )

    let requests = await transport.recordedRequests()
    #expect(requests.map(\.path) == [
        "/v1/activities/resolve",
        "/v1/timing/sessions",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/annotations",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/events",
        "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/events",
    ])
    let extractedEventBody = try #require(requests.last?.body?.data(using: .utf8))
    let json = try #require(try JSONSerialization.jsonObject(with: extractedEventBody) as? [String: Any])
    let payload = try #require(json["payload"] as? [String: Any])
    #expect(payload["annotation_id"] as? String == "CCCCCCCC-CCCC-4CCC-8CCC-CCCCCCCCCCCC")
    #expect(payload["resource_name"] as? String == "Dynamic blocker")
    #expect(payload["confirmation_state"] as? String == "user_confirmed")
}

@Test func syncPersistsCheckpointRunMappingAndUsesItForLaterStepAnnotation() async throws {
    let remoteCheckpointRunId = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    let transport = RecordingHTTPTransport(responses: [
        .json(200, #"{"recommended_activity_id": null}"#),
        .json(201, #"{"id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}"#),
        .json(201, #"{"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}"#),
        .json(
            201,
            """
            {
              "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              "user_id": "99999999-9999-4999-8999-999999999999",
              "session_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              "event_type": "session_started",
              "client_time": "2026-05-05T00:00:01Z",
              "server_time": "2026-05-05T00:00:01Z",
              "timer_elapsed_seconds": 60,
              "timer_active_seconds": 50,
              "client_sequence": 1,
              "client_mutation_id": "session_started-1",
              "client_device_id": "ios-uat-device",
              "idempotency_key": "ios-uat-device:1",
              "capture_context_snapshot_id": null,
              "capture_context_snapshot_ref": null,
              "payload": {"measurement_mode": "checkpointed"}
            }
            """
        ),
        .json(
            201,
            """
            {
              "id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
              "user_id": "99999999-9999-4999-8999-999999999999",
              "session_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              "event_type": "checkpoint_started",
              "client_time": "2026-05-05T00:00:02Z",
              "server_time": "2026-05-05T00:00:02Z",
              "timer_elapsed_seconds": 120,
              "timer_active_seconds": 100,
              "client_sequence": 2,
              "client_mutation_id": "checkpoint_started-2",
              "client_device_id": "ios-uat-device",
              "idempotency_key": "ios-uat-device:2",
              "capture_context_snapshot_id": null,
              "capture_context_snapshot_ref": null,
              "payload": {
                "sequence_order": "2",
                "checkpoint_label": "Current checkpoint",
                "checkpoint_run_id": "\(remoteCheckpointRunId)"
              }
            }
            """
        ),
        .json(201, #"{"id": "ffffffff-ffff-4fff-8fff-ffffffffffff"}"#),
    ])
    let localActivityId = UUID(uuidString: "11111111-1111-4111-8111-111111111111")!
    let localSessionId = UUID(uuidString: "22222222-2222-4222-8222-222222222222")!
    let eventStore = InMemoryPendingTimingEventStore(events: [
        pendingEvent(
            .sessionStarted,
            sessionId: localSessionId,
            sequence: 1,
            payload: ["measurement_mode": MeasurementMode.checkpointed.rawValue]
        ),
        pendingEvent(
            .checkpointStarted,
            sessionId: localSessionId,
            sequence: 2,
            payload: [
                "sequence_order": "2",
                "checkpoint_label": "Current checkpoint",
            ]
        ),
    ])
    let stateStore = InMemoryPendingSyncStateStore()
    let service = PendingSyncService(
        client: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .bearer(token: "uat-token"),
            transport: transport
        ),
        eventStore: eventStore,
        preflightDecisionStore: InMemoryPendingPreflightDecisionStore(),
        syncStateStore: stateStore
    )
    let context = PendingSyncContext(
        localActivityId: localActivityId,
        activityDisplayName: "Dynamic checkpoint note activity",
        deviceId: "ios-uat-device"
    )

    _ = try await service.sync(context: context)
    try await eventStore.append(
        pendingEvent(
            .annotationCaptured,
            sessionId: localSessionId,
            sequence: 3,
            notePreview: "Checkpoint-scoped note.",
            payload: [
                "source": "timing_session_step_note",
                "sequence_order": "2",
                "checkpoint_label": "Current checkpoint",
            ]
        )
    )
    _ = try await service.sync(context: context)

    let requests = await transport.recordedRequests()
    let annotationBody = try #require(requests.last?.body?.data(using: .utf8))
    let json = try #require(try JSONSerialization.jsonObject(with: annotationBody) as? [String: Any])
    let metadata = try #require(json["metadata"] as? [String: Any])
    #expect(requests.last?.path == "/v1/timing/sessions/BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB/annotations")
    #expect(json["checkpoint_run_id"] as? String == remoteCheckpointRunId.uppercased())
    #expect(json["timer_elapsed_seconds"] as? Int == 180)
    #expect(json["timer_active_seconds"] as? Int == 150)
    #expect(metadata["source"] as? String == "timing_session_step_note")
    #expect(metadata["checkpoint_label"] as? String == "Current checkpoint")
}

@Test func syncCreatesCheckpointedSessionFromCheckpointSetupIntent() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(200, #"{"recommended_activity_id": null}"#),
        .json(201, #"{"id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}"#),
        .json(201, #"{"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}"#),
        .json(
            201,
            """
            {
              "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              "user_id": "99999999-9999-4999-8999-999999999999",
              "session_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              "event_type": "intent_recorded",
              "client_time": "2026-05-05T00:00:01Z",
              "server_time": "2026-05-05T00:00:01Z",
              "timer_elapsed_seconds": 0,
              "timer_active_seconds": 0,
              "client_sequence": 1,
              "client_mutation_id": "intent_recorded-1",
              "client_device_id": "ios-uat-device",
              "idempotency_key": "ios-uat-device:1",
              "capture_context_snapshot_id": null,
              "capture_context_snapshot_ref": null,
              "payload": {"measurement_mode": "checkpointed"}
            }
            """
        ),
        .json(
            201,
            """
            {
              "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
              "user_id": "99999999-9999-4999-8999-999999999999",
              "session_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              "event_type": "checkpoint_started",
              "client_time": "2026-05-05T00:00:02Z",
              "server_time": "2026-05-05T00:00:02Z",
              "timer_elapsed_seconds": 0,
              "timer_active_seconds": 0,
              "client_sequence": 2,
              "client_mutation_id": "checkpoint_started-2",
              "client_device_id": "ios-uat-device",
              "idempotency_key": "ios-uat-device:2",
              "capture_context_snapshot_id": null,
              "capture_context_snapshot_ref": null,
              "payload": {"sequence_order": "3", "checkpoint_run_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"}
            }
            """
        ),
    ])
    let localActivityId = UUID(uuidString: "11111111-1111-4111-8111-111111111111")!
    let localSessionId = UUID(uuidString: "22222222-2222-4222-8222-222222222222")!
    let eventStore = InMemoryPendingTimingEventStore(events: [
        pendingEvent(
            .intentRecorded,
            sessionId: localSessionId,
            sequence: 1,
            payload: [
                "measurement_mode": MeasurementMode.checkpointed.rawValue,
                "checkpoint_action": "update_checkpoint_plan",
            ]
        ),
        pendingEvent(
            .checkpointStarted,
            sessionId: localSessionId,
            sequence: 2,
            payload: [
                "sequence_order": "3",
                "checkpoint_label": "Next checkpoint",
            ]
        ),
    ])
    let service = PendingSyncService(
        client: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .bearer(token: "uat-token"),
            transport: transport
        ),
        eventStore: eventStore,
        preflightDecisionStore: InMemoryPendingPreflightDecisionStore(),
        syncStateStore: InMemoryPendingSyncStateStore()
    )

    _ = try await service.sync(
        context: PendingSyncContext(
            localActivityId: localActivityId,
            activityDisplayName: "Dynamic checkpoint setup intent",
            deviceId: "ios-uat-device"
        )
    )

    let requests = await transport.recordedRequests()
    let createSession = try #require(requests.first { $0.path == "/v1/timing/sessions" })
    let body = try #require(createSession.body?.data(using: .utf8))
    let json = try #require(try JSONSerialization.jsonObject(with: body) as? [String: Any])
    #expect(json["mode"] as? String == MeasurementMode.checkpointed.rawValue)
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
            activityDisplayName: "Dynamic test activity",
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

@Test func syncUsesExistingRemotePreflightCheckWhenDecisionCarriesRemoteId() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(200, #"{"recommended_activity_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}"#),
        .json(200, #"{"id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc"}"#),
    ])
    let localActivityId = UUID(uuidString: "11111111-1111-4111-8111-111111111111")!
    let remoteCheckId = UUID(uuidString: "cccccccc-cccc-4ccc-8ccc-cccccccccccc")!
    let preflightStore = InMemoryPendingPreflightDecisionStore(decisions: [
        PendingPreflightDecision(
            activityId: localActivityId,
            checkId: remoteCheckId,
            remoteCheckId: remoteCheckId,
            mutation: mutation(sequence: 6, prefix: "decide_preflight_check"),
            decision: .accept,
            decidedAt: Date(timeIntervalSince1970: 1_775_000_000)
        ),
    ])
    let stateStore = InMemoryPendingSyncStateStore()
    let service = PendingSyncService(
        client: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .bearer(token: "uat-token"),
            transport: transport
        ),
        eventStore: InMemoryPendingTimingEventStore(),
        preflightDecisionStore: preflightStore,
        syncStateStore: stateStore
    )

    let result = try await service.sync(
        context: PendingSyncContext(
            localActivityId: localActivityId,
            activityDisplayName: "Dynamic test activity",
            deviceId: "ios-uat-device"
        )
    )

    #expect(result.uploadedPreflightDecisionCount == 1)
    #expect(try await preflightStore.load().isEmpty)
    let paths = await transport.recordedRequests().map(\.path)
    #expect(paths == [
        "/v1/activities/resolve",
        "/v1/activities/AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA/preflight-checks/CCCCCCCC-CCCC-4CCC-8CCC-CCCCCCCCCCCC/decision",
    ])
    let state = try await stateStore.load()
    #expect(state.preflightCheck(localCheckId: remoteCheckId)?.remoteCheckId == remoteCheckId)
}

@Test func remotePreflightDecisionOverridesStaleLocalMapping() async throws {
    let transport = RecordingHTTPTransport(responses: [
        .json(200, #"{"recommended_activity_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}"#),
        .json(200, #"{"id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc"}"#),
    ])
    let localActivityId = UUID(uuidString: "11111111-1111-4111-8111-111111111111")!
    let remoteCheckId = UUID(uuidString: "cccccccc-cccc-4ccc-8ccc-cccccccccccc")!
    let staleDuplicateCheckId = UUID(uuidString: "dddddddd-dddd-4ddd-8ddd-dddddddddddd")!
    let preflightStore = InMemoryPendingPreflightDecisionStore(decisions: [
        PendingPreflightDecision(
            activityId: localActivityId,
            checkId: remoteCheckId,
            remoteCheckId: remoteCheckId,
            mutation: mutation(sequence: 7, prefix: "decide_preflight_check"),
            decision: .hide,
            decidedAt: Date(timeIntervalSince1970: 1_775_000_000)
        ),
    ])
    let stateStore = InMemoryPendingSyncStateStore(
        state: PendingSyncState(preflightChecks: [
            PreflightCheckSyncMapping(
                localCheckId: remoteCheckId,
                localActivityId: localActivityId,
                remoteActivityId: UUID(uuidString: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")!,
                remoteCheckId: staleDuplicateCheckId,
                createdAt: Date(timeIntervalSince1970: 1_775_000_000)
            ),
        ])
    )
    let service = PendingSyncService(
        client: ParallaxAPIClient(
            baseURL: URL(string: "http://127.0.0.1:18000")!,
            auth: .bearer(token: "uat-token"),
            transport: transport
        ),
        eventStore: InMemoryPendingTimingEventStore(),
        preflightDecisionStore: preflightStore,
        syncStateStore: stateStore
    )

    _ = try await service.sync(
        context: PendingSyncContext(
            localActivityId: localActivityId,
            activityDisplayName: "Dynamic test activity",
            deviceId: "ios-uat-device"
        )
    )

    let paths = await transport.recordedRequests().map(\.path)
    #expect(paths == [
        "/v1/activities/resolve",
        "/v1/activities/AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA/preflight-checks/CCCCCCCC-CCCC-4CCC-8CCC-CCCCCCCCCCCC/decision",
    ])
    let state = try await stateStore.load()
    #expect(state.preflightCheck(localCheckId: remoteCheckId)?.remoteCheckId == remoteCheckId)
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
        clientTime: Date(timeIntervalSince1970: 1_775_000_000 + Double(sequence)),
        timerElapsedSeconds: sequence * 60,
        timerActiveSeconds: sequence * 50,
        captureMethod: .manualButton,
        notePreview: notePreview,
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
