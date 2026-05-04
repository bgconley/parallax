import ParallaxApp
import SwiftUI

@main
struct ParallaxNativeApp: App {
    var body: some Scene {
        WindowGroup {
            let drawer = ProcessInfo.processInfo.environment["PARALLAX_DEMO_DRAWER"]
            switch ProcessInfo.processInfo.environment["PARALLAX_DEMO_STATE"] {
            case "launcher":
                ParallaxRootView(viewModel: .liveDemo(), initialScreen: .launcher, demoDrawer: drawer)
            case "session":
                ParallaxRootView(viewModel: .runningDemo(), initialScreen: .timingSession, demoDrawer: drawer)
            case "reviewed":
                ParallaxRootView(viewModel: .reviewedDemo(), initialScreen: .timingReview, demoDrawer: drawer)
            case "checkpoint_setup":
                ParallaxRootView(viewModel: .liveDemo(), initialScreen: .checkpointSetup, demoDrawer: drawer)
            default:
                ParallaxRootView(viewModel: .liveDemo(), demoDrawer: drawer)
            }
        }
    }
}
