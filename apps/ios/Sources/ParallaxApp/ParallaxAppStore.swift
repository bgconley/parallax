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
    private let eventStoreFactory: @Sendable (UUID) -> any PendingTimingEventStore
    private let preflightStoreFactory: @Sendable (UUID) -> any PendingPreflightDecisionStore
    private let sequenceStore: (any MutationSequenceStore)?

    public init(
        config: ParallaxRuntimeConfig? = nil,
        activities: [ParallaxActivitySummary] = [],
        selectedActivity: ParallaxActivitySummary? = nil,
        timingViewModel: TimingSliceViewModel? = nil,
        eventStoreFactory: @escaping @Sendable (UUID) -> any PendingTimingEventStore = { _ in InMemoryPendingTimingEventStore() },
        preflightStoreFactory: @escaping @Sendable (UUID) -> any PendingPreflightDecisionStore = { _ in InMemoryPendingPreflightDecisionStore() },
        sequenceStore: (any MutationSequenceStore)? = nil
    ) {
        self.config = config
        self.activities = activities
        self.selectedActivity = selectedActivity
        self.eventStoreFactory = eventStoreFactory
        self.preflightStoreFactory = preflightStoreFactory
        self.sequenceStore = sequenceStore
        if let timingViewModel {
            self.timingViewModel = timingViewModel
        } else if let selectedActivity {
            self.timingViewModel = Self.makeTimingViewModel(
                activity: selectedActivity,
                config: config,
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
        guard let seedName = config?.activityName else {
            return
        }
        let activity = ParallaxActivitySummary(
            id: config?.activityId ?? UUID(),
            displayName: seedName,
            source: .uatSeed
        )
        activities = [activity]
        selectActivity(activity)
    }

    public func createActivity(named rawName: String) {
        let name = rawName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else {
            errorMessage = "Enter an activity name to start timing."
            return
        }
        let activity = ParallaxActivitySummary(id: UUID(), displayName: name, source: .local)
        activities.append(activity)
        selectActivity(activity)
    }

    public func selectActivity(_ activity: ParallaxActivitySummary) {
        selectedActivity = activity
        errorMessage = nil
        timingViewModel = Self.makeTimingViewModel(
            activity: activity,
            config: config,
            eventStore: eventStoreFactory(activity.id),
            preflightStore: preflightStoreFactory(activity.id),
            sequenceStore: sequenceStore
        )
    }

    private static func makeTimingViewModel(
        activity: ParallaxActivitySummary,
        config: ParallaxRuntimeConfig?,
        eventStore: any PendingTimingEventStore,
        preflightStore: any PendingPreflightDecisionStore,
        sequenceStore: (any MutationSequenceStore)?
    ) -> TimingSliceViewModel {
        let deviceId = config?.deviceId ?? "ios-local-device"
        var pendingSyncService: PendingSyncService?
        var pendingSyncContext: PendingSyncContext?
        if let config {
            let syncStateStore = FilePendingSyncStateStore(
                fileURL: appSupportRoot().appendingPathComponent("pending-sync-state.json")
            )
            let client = ParallaxAPIClient(baseURL: config.apiBaseURL, auth: config.auth)
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
            mutationSequenceStore: sequenceStore
        )
    }

    private static func appSupportRoot() -> URL {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        return support.appendingPathComponent("Parallax", isDirectory: true)
    }
}
