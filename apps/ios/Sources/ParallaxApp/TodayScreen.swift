import SwiftUI

struct TodayScreen: View {
    let viewModel: TimingSliceViewModel
    @Binding var showsLauncher: Bool
    let initialDrawer: String?
    let startTiming: () async -> Void

    var body: some View {
        TemporalHomeScreen(
            viewModel: viewModel,
            showsLauncher: $showsLauncher,
            initialDrawer: initialDrawer,
            startTiming: startTiming
        )
    }
}
