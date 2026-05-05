import Combine
import Foundation
import ParallaxCore

public struct ParallaxActivitySummary: Equatable, Identifiable, Sendable {
    public let id: UUID
    public let displayName: String
    public let source: Source

    public enum Source: String, Sendable {
        case local
        case backend
        case uatSeed = "uat_seed"
    }

    public init(id: UUID, displayName: String, source: Source) {
        self.id = id
        self.displayName = displayName
        self.source = source
    }
}

@MainActor
public final class ParallaxAppStore: ObservableObject {
    @Published public private(set) var activities: [ParallaxActivitySummary]
    @Published public private(set) var selectedActivity: ParallaxActivitySummary?
    @Published public private(set) var timingViewModel: TimingSliceViewModel?
    @Published public private(set) var errorMessage: String?

    private let config: ParallaxRuntimeConfig?
    private let apiClient: ParallaxAPIClient?
    private let eventStoreFactory: @Sendable (UUID) -> any PendingTimingEventStore
    private let preflightStoreFactory: @Sendable (UUID) -> any PendingPreflightDecisionStore
    private let sequenceStore: (any MutationSequenceStore)?
    private let selectedActivityDefaultsKey: String
    private var appMutationFactory: MutationEnvelopeFactory

    public init(
        config: ParallaxRuntimeConfig? = nil,
        apiClient: ParallaxAPIClient? = nil,
        activities: [ParallaxActivitySummary] = [],
        selectedActivity: ParallaxActivitySummary? = nil,
        timingViewModel: TimingSliceViewModel? = nil,
        eventStoreFactory: @escaping @Sendable (UUID) -> any PendingTimingEventStore = { _ in InMemoryPendingTimingEventStore() },
        preflightStoreFactory: @escaping @Sendable (UUID) -> any PendingPreflightDecisionStore = { _ in InMemoryPendingPreflightDecisionStore() },
        sequenceStore: (any MutationSequenceStore)? = nil
    ) {
        self.config = config
        self.apiClient = apiClient ?? config.map { ParallaxAPIClient(baseURL: $0.apiBaseURL, auth: $0.auth) }
        self.activities = activities
        self.selectedActivity = selectedActivity
        self.eventStoreFactory = eventStoreFactory
        self.preflightStoreFactory = preflightStoreFactory
        self.sequenceStore = sequenceStore
        self.selectedActivityDefaultsKey = "parallax.selectedActivityId.\(config?.deviceId ?? "ios-local-device")"
        self.appMutationFactory = MutationEnvelopeFactory(clientDeviceId: config?.deviceId ?? "ios-local-device")
        if let timingViewModel {
            self.timingViewModel = timingViewModel
        } else if let selectedActivity {
            self.timingViewModel = Self.makeTimingViewModel(
                activity: selectedActivity,
                config: config,
                apiClient: self.apiClient,
                eventStore: eventStoreFactory(selectedActivity.id),
                preflightStore: preflightStoreFactory(selectedActivity.id),
                sequenceStore: sequenceStore
            )
        }
    }

    public static func localEmpty() -> ParallaxAppStore {
        ParallaxAppStore()
    }

    public static func live(config: ParallaxRuntimeConfig?) -> ParallaxAppStore {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        let root = support.appendingPathComponent("Parallax", isDirectory: true)
        let sequenceStore = FileMutationSequenceStore(
            fileURL: root.appendingPathComponent("mutation-sequences.json")
        )
        return ParallaxAppStore(
            config: config,
            eventStoreFactory: { activityId in
                FilePendingTimingEventStore(
                    fileURL: root.appendingPathComponent("\(activityId.uuidString)-pending-events.json")
                )
            },
            preflightStoreFactory: { activityId in
                FilePendingPreflightDecisionStore(
                    fileURL: root.appendingPathComponent("\(activityId.uuidString)-pending-preflight.json")
                )
            },
            sequenceStore: sequenceStore
        )
    }

    public func bootstrap() async {
        guard selectedActivity == nil else { return }
        if let seedName = config?.activityName {
            await bootstrapSeedActivity(named: seedName)
            return
        }
        await loadBackendActivitiesIfAvailable()
    }

    public func createActivity(named rawName: String) async {
        let name = rawName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else {
            errorMessage = "Enter an activity name to start timing."
            return
        }

        if let apiClient {
            do {
                let created = try await createRemoteActivity(named: name, client: apiClient)
                let activity = ParallaxActivitySummary(
                    id: created.id,
                    displayName: created.displayName,
                    source: .backend
                )
                upsertActivity(activity)
                selectActivity(activity)
                return
            } catch {
                errorMessage = "Saved locally. Sync can create the backend activity when reachable."
            }
        }

        let activity = ParallaxActivitySummary(id: UUID(), displayName: name, source: .local)
        activities.append(activity)
        selectActivity(activity)
    }

    public func selectActivity(_ activity: ParallaxActivitySummary) {
        selectedActivity = activity
        UserDefaults.standard.set(activity.id.uuidString, forKey: selectedActivityDefaultsKey)
        errorMessage = nil
        timingViewModel = Self.makeTimingViewModel(
            activity: activity,
            config: config,
            apiClient: apiClient,
            eventStore: eventStoreFactory(activity.id),
            preflightStore: preflightStoreFactory(activity.id),
            sequenceStore: sequenceStore
        )
    }

    private func bootstrapSeedActivity(named seedName: String) async {
        if let existing = activities.first(where: { $0.displayName.caseInsensitiveCompare(seedName) == .orderedSame }) {
            selectActivity(existing)
            return
        }
        if let activityId = config?.activityId {
            let activity = ParallaxActivitySummary(
                id: activityId,
                displayName: seedName,
                source: .uatSeed
            )
            activities = [activity]
            selectActivity(activity)
            return
        }
        if let apiClient {
            do {
                let activity = try await ensureRemoteActivity(named: seedName, client: apiClient)
                let summary = ParallaxActivitySummary(
                    id: activity.id,
                    displayName: activity.displayName,
                    source: .backend
                )
                upsertActivity(summary)
                selectActivity(summary)
                return
            } catch {
                errorMessage = "Using local seed activity. Backend sync can retry when reachable."
            }
        }
        let activity = ParallaxActivitySummary(
            id: config?.activityId ?? UUID(),
            displayName: seedName,
            source: .uatSeed
        )
        activities = [activity]
        selectActivity(activity)
    }

    private func loadBackendActivitiesIfAvailable() async {
        guard let apiClient else { return }
        do {
            let request = try apiClient.listActivitiesRequest(limit: 25)
            let remoteActivities = try await apiClient.send(request, decode: [ActivityDTO].self)
            let summaries = remoteActivities.map {
                ParallaxActivitySummary(id: $0.id, displayName: $0.displayName, source: .backend)
            }
            activities = summaries
            if let activity = preferredActivity(from: summaries) {
                selectActivity(activity)
            }
            errorMessage = nil
        } catch {
            errorMessage = "Backend activities unavailable. You can still create and time locally."
        }
    }

    private func ensureRemoteActivity(named name: String, client: ParallaxAPIClient) async throws -> ActivityDTO {
        let listRequest = try client.listActivitiesRequest(q: name, limit: 10)
        let matches = try await client.send(listRequest, decode: [ActivityDTO].self)
        if let exact = matches.first(where: { $0.displayName.caseInsensitiveCompare(name) == .orderedSame }) {
            return exact
        }
        return try await createRemoteActivity(named: name, client: client)
    }

    private func createRemoteActivity(named name: String, client: ParallaxAPIClient) async throws -> ActivityDTO {
        let mutation = appMutationFactory.next(prefix: "create_activity", at: Date())
        try await sequenceStore?.saveSequence(
            mutation.clientSequence,
            clientDeviceId: mutation.clientDeviceId
        )
        let request = try client.createActivityRequest(
            displayName: name,
            mutation: mutation,
            defaultTimingMode: .wholeTask
        )
        return try await client.send(request, decode: ActivityDTO.self)
    }

    private func upsertActivity(_ activity: ParallaxActivitySummary) {
        activities.removeAll { $0.id == activity.id }
        activities.append(activity)
    }

    private func preferredActivity(from activities: [ParallaxActivitySummary]) -> ParallaxActivitySummary? {
        if let selectedIdString = UserDefaults.standard.string(forKey: selectedActivityDefaultsKey),
           let selectedId = UUID(uuidString: selectedIdString),
           let selected = activities.first(where: { $0.id == selectedId }) {
            return selected
        }
        return activities.count == 1 ? activities.first : nil
    }

    private static func makeTimingViewModel(
        activity: ParallaxActivitySummary,
        config: ParallaxRuntimeConfig?,
        apiClient: ParallaxAPIClient?,
        eventStore: any PendingTimingEventStore,
        preflightStore: any PendingPreflightDecisionStore,
        sequenceStore: (any MutationSequenceStore)?
    ) -> TimingSliceViewModel {
        let deviceId = config?.deviceId ?? "ios-local-device"
        var pendingSyncService: PendingSyncService?
        var pendingSyncContext: PendingSyncContext?
        if let config, let client = apiClient {
            let syncStateStore = FilePendingSyncStateStore(
                fileURL: appSupportRoot().appendingPathComponent("pending-sync-state.json")
            )
            pendingSyncService = PendingSyncService(
                client: client,
                eventStore: eventStore,
                preflightDecisionStore: preflightStore,
                syncStateStore: syncStateStore
            )
            pendingSyncContext = PendingSyncContext(
                localActivityId: activity.id,
                activityDisplayName: activity.displayName,
                deviceId: deviceId,
                preflightCheckText: config.preflightCheckText
            )
        }
        return TimingSliceViewModel(
            activityId: activity.id,
            activityName: activity.displayName,
            deviceId: deviceId,
            eventStore: eventStore,
            preflightDecisionStore: preflightStore,
            pendingSyncService: pendingSyncService,
            pendingSyncContext: pendingSyncContext,
            mutationSequenceStore: sequenceStore,
            apiClient: apiClient
        )
    }

    private static func appSupportRoot() -> URL {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        return support.appendingPathComponent("Parallax", isDirectory: true)
    }
}
