import ParallaxCore
import SwiftUI

public struct ContextCaptureSheetView: View {
    let note: String?

    public init(note: String? = nil) {
        self.note = note
    }

    public var body: some View {
        Card {
            Text("Say what happened")
                .font(.system(size: 22, weight: .bold, design: .rounded))
            Text(note ?? "Add a note about what changed during this run.")
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(parallax: .elevatedLight))
                .clipShape(RoundedRectangle(cornerRadius: 18))
            HStack {
                SoftBadge(text: "Detour", systemName: "arrow.triangle.branch", role: .detour)
                SoftBadge(text: "Pending", systemName: "sparkles", role: .waiting)
            }
            Label("Saved locally. Interpretation pending.", systemImage: "checkmark.circle")
                .foregroundStyle(Color(parallax: .waitingText))
        }
    }
}

public struct ActivityProfileView: View {
    private let activityName: String

    public init(activityName: String = "Selected activity") {
        self.activityName = activityName
    }

    public var body: some View {
        CanonicalScreen(title: activityName, subtitle: "Personal timing range", leadingIcon: "chevron.left") {
            Card {
                Text("Personal range")
                    .font(.headline)
                HStack {
                    SoftBadge(text: "Active range pending", systemName: "timer", role: .active)
                    SoftBadge(text: "Wall range pending", systemName: "clock", role: .wall)
                }
                Text("Reviewed runs will determine sample size, confidence, common friction, and preflight evidence.")
                    .foregroundStyle(.secondary)
            }
        }
    }
}

public struct AskAboutTimeView: View {
    public init() {}

    public var body: some View {
        CanonicalScreen(title: "Ask about time", subtitle: "Evidence-backed answers only", leadingIcon: "chevron.left") {
            Card {
                Text("Ask a time question")
                    .font(.headline)
                Text("Answers require reviewed evidence and include sample size, confidence, limitations, and evidence.")
                    .foregroundStyle(.secondary)
            }
        }
    }
}

public struct PrivacySettingsView: View {
    public init() {}

    public var body: some View {
        CanonicalScreen(title: "Privacy", subtitle: "Source data remains under your control", leadingIcon: "chevron.left") {
            Card {
                Text("Raw context retention")
                    .font(.headline)
                Text("Keep raw notes until you delete them.")
                    .foregroundStyle(.secondary)
            }
        }
    }
}

public struct OfflineSyncView: View {
    public init() {}

    public var body: some View {
        CanonicalScreen(title: "Offline and sync", subtitle: "Timing continues without connectivity", leadingIcon: "chevron.left") {
            Card {
                Text("Saved on this device")
                    .font(.headline)
                Text("Timing events, notes, and review drafts are queued until the connection returns.")
                    .foregroundStyle(.secondary)
            }
        }
    }
}
