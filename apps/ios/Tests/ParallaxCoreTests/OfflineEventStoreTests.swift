import Foundation
import ParallaxCore
import Testing

@Test func fileEventStorePersistsPendingEventsIdempotently() async throws {
    let fileURL = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("pending-events.json")
    defer { try? FileManager.default.removeItem(at: fileURL.deletingLastPathComponent()) }

    let store = FilePendingTimingEventStore(fileURL: fileURL)
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:1",
        clientMutationId: "mutation-1",
        clientDeviceId: "device-1",
        clientSequence: 1,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_000)
    )
    let event = PendingTimingEvent(
        sessionId: UUID(),
        eventType: .sessionStarted,
        mutation: mutation,
        clientTime: Date(timeIntervalSince1970: 1_775_000_001),
        captureMethod: .manualButton
    )

    try await store.append(event)
    try await store.append(event)

    let loaded = try await store.load()
    #expect(loaded == [event])

    try await store.remove(ids: [event.id])
    #expect(try await store.load().isEmpty)
}

@Test func filePreflightStorePersistsPendingDecisionsIdempotently() async throws {
    let fileURL = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString)
        .appendingPathComponent("pending-preflight-decisions.json")
    defer { try? FileManager.default.removeItem(at: fileURL.deletingLastPathComponent()) }

    let store = FilePendingPreflightDecisionStore(fileURL: fileURL)
    let mutation = MutationEnvelope(
        idempotencyKey: "device-1:2",
        clientMutationId: "decide-preflight-2",
        clientDeviceId: "device-1",
        clientSequence: 2,
        clientTimestamp: Date(timeIntervalSince1970: 1_775_000_010)
    )
    let decision = PendingPreflightDecision(
        activityId: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!,
        checkId: UUID(uuidString: "22222222-2222-4222-8222-222222222222")!,
        mutation: mutation,
        decision: .snooze,
        decidedAt: Date(timeIntervalSince1970: 1_775_000_011),
        snoozedUntil: Date(timeIntervalSince1970: 1_775_086_400),
        reason: "later"
    )

    try await store.append(decision)
    try await store.append(decision)

    let loaded = try await store.load()
    #expect(loaded == [decision])

    try await store.remove(ids: [decision.id])
    #expect(try await store.load().isEmpty)
}
