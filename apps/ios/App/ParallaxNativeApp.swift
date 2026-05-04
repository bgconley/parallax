import ParallaxApp
import ParallaxCore
import SwiftUI

@main
struct ParallaxNativeApp: App {
    var body: some Scene {
        WindowGroup {
            let drawer = ProcessInfo.processInfo.environment["PARALLAX_DEMO_DRAWER"]
            let connectedConfig = try? ParallaxRuntimeConfig.load()
            switch ProcessInfo.processInfo.environment["PARALLAX_DEMO_STATE"] {
            case "launcher":
                ParallaxRootView(viewModel: viewModel(config: connectedConfig), initialScreen: .launcher, demoDrawer: drawer)
            case "session":
                ParallaxRootView(viewModel: .runningDemo(), initialScreen: .timingSession, demoDrawer: drawer)
            case "reviewed":
                ParallaxRootView(viewModel: .reviewedDemo(), initialScreen: .timingReview, demoDrawer: drawer)
            case "checkpoint_setup":
                ParallaxRootView(viewModel: viewModel(config: connectedConfig), initialScreen: .checkpointSetup, demoDrawer: drawer)
            default:
                ParallaxRootView(viewModel: viewModel(config: connectedConfig), demoDrawer: drawer)
            }
        }
    }

    private func viewModel(config: ParallaxRuntimeConfig?) -> TimingSliceViewModel {
        guard let config else {
            return .liveDemo()
        }
        return .liveConnected(config: config)
    }
}
