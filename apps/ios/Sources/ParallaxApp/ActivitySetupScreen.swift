import ParallaxDesignSystem
import SwiftUI

struct ActivitySetupScreen: View {
    @ObservedObject var appStore: ParallaxAppStore
    @State private var activityName = ""

    var body: some View {
        CanonicalScreen(
            title: "Parallax",
            subtitle: "Create or select something real to time.",
            leadingIcon: "timer"
        ) {
            Card {
                Text("What are you timing?")
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                TextField("Activity name", text: $activityName)
                    .textFieldStyle(.roundedBorder)
                    .submitLabel(.done)
                    .onSubmit(createActivity)
                PrimaryButton(title: "Create activity", systemName: "plus") {
                    createActivity()
                }
                if let error = appStore.errorMessage {
                    Text(error)
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .interruptionText))
                }
            }

            if !appStore.activities.isEmpty {
                Card {
                    Text("Recent activities")
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                    ForEach(appStore.activities) { activity in
                        Button {
                            appStore.selectActivity(activity)
                        } label: {
                            HStack {
                                Label(activity.displayName, systemImage: "timer")
                                    .font(.system(size: 14, weight: .semibold, design: .rounded))
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundStyle(Color(parallax: .textTertiaryLight))
                            }
                            .frame(maxWidth: .infinity, minHeight: 40)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            Card(background: Color(parallax: .activeSoft).opacity(0.35)) {
                Label("Timing works locally first. Sync can retry when the backend is reachable.", systemImage: "checkmark.circle")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
        }
        .task {
            await appStore.bootstrap()
        }
    }

    private func createActivity() {
        let name = activityName
        activityName = ""
        Task {
            await appStore.createActivity(named: name)
        }
    }
}
