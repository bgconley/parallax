import Foundation
import ParallaxApp
import ParallaxCore
import Testing

@MainActor
@Test func appStoreStartsEmptyWhenNoSeedActivityExists() async throws {
    let store = ParallaxAppStore.localEmpty()

    await store.bootstrap()

    #expect(store.activities.isEmpty)
    #expect(store.selectedActivity == nil)
    #expect(store.timingViewModel == nil)
}

@MainActor
@Test func appStoreCreatesAndSelectsArbitraryActivity() async throws {
    let store = ParallaxAppStore.localEmpty()

    await store.createActivity(named: "UAT Dynamic Activity")

    let selected = try #require(store.selectedActivity)
    #expect(selected.displayName == "UAT Dynamic Activity")
    #expect(store.activities.map(\.displayName) == ["UAT Dynamic Activity"])
    #expect(store.timingViewModel?.activityName == "UAT Dynamic Activity")
}

@MainActor
@Test func localCreatedActivitySurvivesRelaunchFromAppStateCache() async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    let cacheURL = directory.appendingPathComponent("app-state.json")
    defer { try? FileManager.default.removeItem(at: directory) }
    let stateStore = FileParallaxAppStateStore(fileURL: cacheURL)

    let firstLaunch = ParallaxAppStore(appStateStore: stateStore)
    await firstLaunch.bootstrap()
    await firstLaunch.createActivity(named: "UAT Offline Relaunch Activity")
    let created = try #require(firstLaunch.selectedActivity)

    let secondLaunch = ParallaxAppStore(appStateStore: stateStore)
    await secondLaunch.bootstrap()

    #expect(secondLaunch.activities == [created])
    #expect(secondLaunch.selectedActivity == created)
    #expect(secondLaunch.timingViewModel?.activityName == "UAT Offline Relaunch Activity")
}

@MainActor
@Test func appStoreUsesExplicitSeedOnlyWhenProvided() async throws {
    let activityId = UUID(uuidString: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")!
    let config = ParallaxRuntimeConfig(
        apiBaseURL: URL(string: "http://127.0.0.1:18000")!,
        auth: .devHeader(userId: UUID(uuidString: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")!),
        activityId: activityId,
        activityName: "Seeded dynamic activity",
        deviceId: "ios-seed-device",
        preflightCheckText: "Check the seeded resource"
    )
    let store = ParallaxAppStore(config: config)

    await store.bootstrap()

    let selected = try #require(store.selectedActivity)
    #expect(selected.id == activityId)
    #expect(selected.displayName == "Seeded dynamic activity")
    #expect(store.timingViewModel?.activityId == activityId)
}
