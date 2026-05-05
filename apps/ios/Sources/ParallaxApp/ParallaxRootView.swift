import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

public struct ParallaxRootView: View {
    @StateObject private var appStore: ParallaxAppStore
    @State private var screen: FirstSliceScreen
    @State private var showsLauncher: Bool
    private let demoDrawer: String?

    public init(
        appStore: ParallaxAppStore = .localEmpty(),
        initialScreen: FirstSliceScreen = .today,
        demoDrawer: String? = nil
    ) {
        _appStore = StateObject(wrappedValue: appStore)
        _screen = State(initialValue: initialScreen)
        _showsLauncher = State(initialValue: initialScreen == .launcher)
        self.demoDrawer = demoDrawer
    }

    public init(viewModel: TimingSliceViewModel, initialScreen: FirstSliceScreen = .today, demoDrawer: String? = nil) {
        let activity = ParallaxActivitySummary(id: viewModel.activityId, displayName: viewModel.activityName, source: .local)
        _appStore = StateObject(
            wrappedValue: ParallaxAppStore(
                activities: [activity],
                selectedActivity: activity,
                timingViewModel: viewModel,
                eventStoreFactory: { _ in InMemoryPendingTimingEventStore() }
            )
        )
        _screen = State(initialValue: initialScreen)
        _showsLauncher = State(initialValue: initialScreen == .launcher)
        self.demoDrawer = demoDrawer
    }

    public var body: some View {
        ZStack {
            Color(parallax: .canvasLight).ignoresSafeArea()
            if let viewModel = appStore.timingViewModel {
                switch screen {
                case .today, .launcher:
                    TodayScreen(
                        viewModel: viewModel,
                        showsLauncher: $showsLauncher,
                        initialDrawer: demoDrawer,
                        startTiming: {
                            await viewModel.startRun()
                            showsLauncher = false
                            screen = .timingSession
                        }
                    )
                case .timingSession:
                    TimingSessionScreen(
                        viewModel: viewModel,
                        initialDrawer: demoDrawer,
                        finishAndReview: {
                            await viewModel.finishRun()
                            screen = .timingReview
                        }
                    )
                case .timingReview:
                    TimingReviewScreen(
                        viewModel: viewModel,
                        initialDrawer: demoDrawer,
                        saveReview: {
                            await viewModel.saveUsefulReview()
                        }
                    )
                case .checkpointSetup:
                    CheckpointSetupScreen(viewModel: viewModel, initialDrawer: demoDrawer)
                }
            } else {
                ActivitySetupScreen(appStore: appStore)
            }
        }
        .task {
            await appStore.bootstrap()
            await appStore.timingViewModel?.loadPendingEvents()
        }
    }
}

public enum FirstSliceScreen {
    case today
    case launcher
    case timingSession
    case timingReview
    case checkpointSetup
}
