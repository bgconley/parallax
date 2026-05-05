import Foundation

public struct PendingSyncContext: Equatable, Sendable {
    public let localActivityId: UUID
    public let activityDisplayName: String
    public let deviceId: String
    public let preflightCheckText: String?

    public init(
        localActivityId: UUID,
        activityDisplayName: String,
        deviceId: String,
        preflightCheckText: String? = nil
    ) {
        self.localActivityId = localActivityId
        self.activityDisplayName = activityDisplayName
        self.deviceId = deviceId
        self.preflightCheckText = preflightCheckText
    }
}

public struct PendingSyncResult: Equatable, Sendable {
    public let uploadedTimingEventCount: Int
    public let uploadedPreflightDecisionCount: Int
    public let remoteActivityId: UUID?
    public let remoteSessionIds: [UUID]

    public init(
        uploadedTimingEventCount: Int,
        uploadedPreflightDecisionCount: Int,
        remoteActivityId: UUID?,
        remoteSessionIds: [UUID]
    ) {
        self.uploadedTimingEventCount = uploadedTimingEventCount
        self.uploadedPreflightDecisionCount = uploadedPreflightDecisionCount
        self.remoteActivityId = remoteActivityId
        self.remoteSessionIds = remoteSessionIds
    }
}

public actor PendingSyncService {
    private let client: ParallaxAPIClient
    private let eventStore: any PendingTimingEventStore
    private let preflightDecisionStore: any PendingPreflightDecisionStore
    private let syncStateStore: any PendingSyncStateStore
    private let now: @Sendable () -> Date

    public init(
        client: ParallaxAPIClient,
        eventStore: any PendingTimingEventStore,
        preflightDecisionStore: any PendingPreflightDecisionStore,
        syncStateStore: any PendingSyncStateStore,
        now: @escaping @Sendable () -> Date = Date.init
    ) {
        self.client = client
        self.eventStore = eventStore
        self.preflightDecisionStore = preflightDecisionStore
        self.syncStateStore = syncStateStore
        self.now = now
    }

    public func sync(context: PendingSyncContext) async throws -> PendingSyncResult {
        let timingEvents = try await eventStore.load()
            .sorted { $0.mutation.clientSequence < $1.mutation.clientSequence }
        let preflightDecisions = try await preflightDecisionStore.load()
            .sorted { $0.mutation.clientSequence < $1.mutation.clientSequence }
        guard !timingEvents.isEmpty || !preflightDecisions.isEmpty else {
            return PendingSyncResult(
                uploadedTimingEventCount: 0,
                uploadedPreflightDecisionCount: 0,
                remoteActivityId: nil,
                remoteSessionIds: []
            )
        }

        var state = try await syncStateStore.load()
        let activity = try await ensureActivity(context: context, state: &state)
        var remoteSessionIds: [UUID] = []
        var uploadedTimingEventIds: Set<UUID> = []

        for (localSessionId, events) in Dictionary(grouping: timingEvents, by: \.sessionId) {
            let session = try await ensureSession(
                localSessionId: localSessionId,
                events: events,
                activity: activity,
                context: context,
                state: &state
            )
            remoteSessionIds.append(session.remoteSessionId)
            for event in events.sorted(by: { $0.mutation.clientSequence < $1.mutation.clientSequence }) {
                try await upload(event: event, remoteSessionId: session.remoteSessionId)
                uploadedTimingEventIds.insert(event.id)
            }
        }
        if !uploadedTimingEventIds.isEmpty {
            try await eventStore.remove(ids: uploadedTimingEventIds)
        }

        var uploadedPreflightDecisionIds: Set<UUID> = []
        for decision in preflightDecisions {
            let check = try await ensurePreflightCheck(
                decision: decision,
                activity: activity,
                context: context,
                state: &state
            )
            let request = try client.decidePreflightCheckRequest(
                activityId: check.remoteActivityId,
                checkId: check.remoteCheckId,
                mutation: decision.mutation,
                decision: decision.decision,
                snoozedUntil: snoozedUntil(for: decision),
                reason: decision.reason
            )
            _ = try await client.send(request, decode: RemoteIDResponse.self)
            uploadedPreflightDecisionIds.insert(decision.id)
        }
        if !uploadedPreflightDecisionIds.isEmpty {
            try await preflightDecisionStore.remove(ids: uploadedPreflightDecisionIds)
        }

        return PendingSyncResult(
            uploadedTimingEventCount: uploadedTimingEventIds.count,
            uploadedPreflightDecisionCount: uploadedPreflightDecisionIds.count,
            remoteActivityId: activity.remoteActivityId,
            remoteSessionIds: remoteSessionIds
        )
    }

    private func ensureActivity(
        context: PendingSyncContext,
        state: inout PendingSyncState
    ) async throws -> ActivitySyncMapping {
        if let existing = state.activity(localActivityId: context.localActivityId) {
            return existing
        }

        if let resolved = try await resolveActivity(displayName: context.activityDisplayName) {
            let mapping = ActivitySyncMapping(
                localActivityId: context.localActivityId,
                remoteActivityId: resolved,
                displayName: context.activityDisplayName,
                createdAt: now()
            )
            state.upsert(mapping)
            try await syncStateStore.save(state)
            return mapping
        }

        let request = try client.createActivityRequest(
            displayName: context.activityDisplayName,
            mutation: deterministicMutation(
                deviceId: context.deviceId,
                label: "create_activity_\(context.localActivityId.uuidString.lowercased())"
            ),
            defaultTimingMode: .checkpointed
        )
        let response = try await client.send(request, decode: RemoteIDResponse.self)
        let mapping = ActivitySyncMapping(
            localActivityId: context.localActivityId,
            remoteActivityId: response.id,
            displayName: context.activityDisplayName,
            createdAt: now()
        )
        state.upsert(mapping)
        try await syncStateStore.save(state)
        return mapping
    }

    private func resolveActivity(displayName: String) async throws -> UUID? {
        let request = try client.resolveActivityRequest(query: displayName, limit: 5)
        let response = try await client.send(request, decode: ResolveActivityResponse.self)
        return response.recommendedActivityId
    }

    private func ensureSession(
        localSessionId: UUID,
        events: [PendingTimingEvent],
        activity: ActivitySyncMapping,
        context: PendingSyncContext,
        state: inout PendingSyncState
    ) async throws -> TimingSessionSyncMapping {
        if let existing = state.session(localSessionId: localSessionId) {
            return existing
        }
        let request = try client.createTimingSessionRequest(
            activityId: activity.remoteActivityId,
            clientSessionId: localSessionId.uuidString,
            mode: measurementMode(from: events),
            mutation: deterministicMutation(
                deviceId: context.deviceId,
                label: "create_timing_session_\(localSessionId.uuidString.lowercased())"
            ),
            intendedStartAt: events.first(where: { $0.eventType == .sessionStarted })?.clientTime
        )
        let response = try await client.send(request, decode: RemoteIDResponse.self)
        let mapping = TimingSessionSyncMapping(
            localSessionId: localSessionId,
            localActivityId: context.localActivityId,
            remoteActivityId: activity.remoteActivityId,
            remoteSessionId: response.id,
            createdAt: now()
        )
        state.upsert(mapping)
        try await syncStateStore.save(state)
        return mapping
    }

    private func upload(event: PendingTimingEvent, remoteSessionId: UUID) async throws {
        if event.eventType == .sessionCompleted {
            let request = try client.completeTimingSessionRequest(
                sessionId: remoteSessionId,
                mutation: event.mutation,
                completedAt: event.clientTime,
                timerElapsedSeconds: event.timerElapsedSeconds ?? 0,
                timerActiveSeconds: event.timerActiveSeconds ?? 0
            )
            _ = try await client.send(request, decode: RemoteIDResponse.self)
            return
        }
        if let reviewRequest = try reviewRequest(for: event, remoteSessionId: remoteSessionId) {
            _ = try await client.send(reviewRequest, decode: RemoteIDResponse.self)
            return
        }
        let request = try client.appendTimingEventRequest(event, remoteSessionId: remoteSessionId)
        _ = try await client.send(request, decode: RemoteIDResponse.self)
    }

    private func reviewRequest(for event: PendingTimingEvent, remoteSessionId: UUID) throws -> URLRequest? {
        guard event.eventType == .reviewSaved,
              let decisionValue = event.payload["decision"],
              let decision = ModelUpdateDecision(rawValue: decisionValue)
        else {
            return nil
        }
        if decision.isDiscardDecision || event.payload["sync_operation"] == "discard_timing_session" {
            return try client.discardTimingSessionRequest(
                sessionId: remoteSessionId,
                mutation: event.mutation,
                decision: decision,
                userNote: event.notePreview
            )
        }
        let modelInclusion = event.payload["model_inclusion"]
            .flatMap(ModelInclusion.init(rawValue:)) ?? .full
        let scopes = event.payload["scopes"]
            .map(parseScopes) ?? [.activeDuration, .wallDuration, .frictionPatterns]
        return try client.reviewTimingSessionRequest(
            sessionId: remoteSessionId,
            mutation: event.mutation,
            decision: decision,
            modelInclusion: modelInclusion,
            scopes: scopes,
            userNote: event.notePreview
        )
    }

    private func ensurePreflightCheck(
        decision: PendingPreflightDecision,
        activity: ActivitySyncMapping,
        context: PendingSyncContext,
        state: inout PendingSyncState
    ) async throws -> PreflightCheckSyncMapping {
        if let existing = state.preflightCheck(localCheckId: decision.checkId) {
            return existing
        }
        let request = try client.createPreflightCheckRequest(
            activityId: activity.remoteActivityId,
            mutation: deterministicMutation(
                deviceId: context.deviceId,
                label: "create_preflight_check_\(decision.checkId.uuidString.lowercased())"
            ),
            checkText: context.preflightCheckText ?? decision.reason ?? "Review this preflight check"
        )
        let response = try await client.send(request, decode: RemoteIDResponse.self)
        let mapping = PreflightCheckSyncMapping(
            localCheckId: decision.checkId,
            localActivityId: context.localActivityId,
            remoteActivityId: activity.remoteActivityId,
            remoteCheckId: response.id,
            createdAt: now()
        )
        state.upsert(mapping)
        try await syncStateStore.save(state)
        return mapping
    }

    private func measurementMode(from events: [PendingTimingEvent]) -> MeasurementMode {
        events.first(where: { $0.eventType == .sessionStarted })?
            .payload["measurement_mode"]
            .flatMap(MeasurementMode.init(rawValue:)) ?? .wholeTask
    }

    private func parseScopes(_ raw: String) -> [ReviewLearningScope] {
        raw.split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .compactMap(ReviewLearningScope.init(rawValue:))
    }

    private func snoozedUntil(for decision: PendingPreflightDecision) -> Date? {
        guard decision.decision == .snooze else {
            return decision.snoozedUntil
        }
        return decision.snoozedUntil ?? now().addingTimeInterval(86_400)
    }

    private func deterministicMutation(deviceId: String, label: String) -> MutationEnvelope {
        MutationEnvelope(
            idempotencyKey: "\(deviceId):sync:\(label)",
            clientMutationId: "sync_\(label)",
            clientDeviceId: deviceId,
            clientSequence: 0,
            clientTimestamp: now()
        )
    }
}

private struct RemoteIDResponse: Decodable {
    let id: UUID
}

private struct ResolveActivityResponse: Decodable {
    let recommendedActivityId: UUID?
}
