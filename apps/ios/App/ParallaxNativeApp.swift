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
                ParallaxRootView(appStore: appStore(config: connectedConfig), initialScreen: .launcher, demoDrawer: drawer)
            case "session":
                ParallaxRootView(appStore: appStore(config: connectedConfig), initialScreen: .timingSession, demoDrawer: drawer)
            case "reviewed":
                ParallaxRootView(appStore: appStore(config: connectedConfig), initialScreen: .timingReview, demoDrawer: drawer)
            case "checkpoint_setup":
                ParallaxRootView(appStore: appStore(config: connectedConfig), initialScreen: .checkpointSetup, demoDrawer: drawer)
            default:
                ParallaxRootView(appStore: appStore(config: connectedConfig), demoDrawer: drawer)
            }
        }
    }

    private func appStore(config: ParallaxRuntimeConfig?) -> ParallaxAppStore {
        ParallaxAppStore.live(config: config)
    }
}
