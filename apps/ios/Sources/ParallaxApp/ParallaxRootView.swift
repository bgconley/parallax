import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

public struct ParallaxRootView: View {
    @StateObject private var viewModel: TimingSliceViewModel
    @State private var screen: FirstSliceScreen
    @State private var showsLauncher: Bool
    private let demoDrawer: String?

    public init(viewModel: TimingSliceViewModel = .liveDemo(), initialScreen: FirstSliceScreen = .today, demoDrawer: String? = nil) {
        _viewModel = StateObject(wrappedValue: viewModel)
        _screen = State(initialValue: initialScreen)
        _showsLauncher = State(initialValue: initialScreen == .launcher)
        self.demoDrawer = demoDrawer
    }

    public var body: some View {
        ZStack {
            Color(parallax: .canvasLight).ignoresSafeArea()
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
        }
        .task { await viewModel.loadPendingEvents() }
    }
}

public enum FirstSliceScreen {
    case today
    case launcher
    case timingSession
    case timingReview
    case checkpointSetup
}
