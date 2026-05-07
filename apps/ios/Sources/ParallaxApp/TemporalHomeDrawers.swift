import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

public enum TemporalDrawerActionLayout {
    public static let navigationActionsShowChevron = true
    public static let terminalActionsShowChevron = false
    public static let directActionsShowChevron = false
    public static let disabledActionsHideText = false
}

struct TemporalNavigationDrawerView: View {
    let navigate: (TemporalNavigationDestination) -> Void
    let dismiss: () -> Void

    var body: some View {
        temporalDrawerShell(title: "Temporal navigation", subtitle: "Only timing, review, sync, and grounded answers.", dismiss: dismiss) {
            temporalDrawerButton("Current run", systemName: "timer", role: .active) {
                navigate(.currentRun)
            }
            temporalDrawerButton("Needs review", systemName: "checkmark.seal", role: .checkpoint) {
                navigate(.needsReview)
            }
            temporalDrawerButton("Sync queue", systemName: "arrow.triangle.2.circlepath", role: .waiting) {
                navigate(.syncQueue)
            }
            temporalDrawerButton("Ask about time", systemName: "quote.bubble", role: .detour) {
                navigate(.askTime)
            }
            temporalDrawerButton("Close", systemName: "xmark", role: .wall, showsChevron: TemporalDrawerActionLayout.terminalActionsShowChevron, action: dismiss)
        }
    }
}

struct QuickCaptureDrawerView: View {
    let save: (String) -> Void
    let dismiss: () -> Void
    @State private var note = ""

    var body: some View {
        temporalDrawerShell(title: "Capture timing evidence", subtitle: "Saved locally first; sync can retry later.", dismiss: dismiss) {
            Card(background: Color(parallax: .elevatedLight)) {
                TextField("What happened?", text: $note, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(3, reservesSpace: true)
                Text("Queued as a quick timing annotation.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
            temporalDrawerButton("Save timing note", systemName: "tray.and.arrow.down", role: .active, showsChevron: TemporalDrawerActionLayout.directActionsShowChevron) {
                save(note.trimmingCharacters(in: .whitespacesAndNewlines))
            }
            temporalDrawerButton("Cancel", systemName: "xmark", role: .wall, showsChevron: TemporalDrawerActionLayout.terminalActionsShowChevron, action: dismiss)
        }
    }
}

struct AskTimeDrawerView: View {
    let activityName: String
    let submit: (String) -> Void
    let dismiss: () -> Void
    @State private var question = ""

    private var trimmedQuestion: String {
        question.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var body: some View {
        temporalDrawerShell(title: "Ask about time", subtitle: "Answers use reviewed runs and evidence.", dismiss: dismiss) {
            Card(background: Color(parallax: .elevatedLight)) {
                Text(activityName)
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color(parallax: .detourText))
                    .lineLimit(2)
                TextField("Ask a timing question", text: $question, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(3, reservesSpace: true)
                Text("Raw note quotes stay off by default.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
            temporalDrawerButton("Submit question", systemName: "quote.bubble", role: .detour, showsChevron: TemporalDrawerActionLayout.directActionsShowChevron) {
                guard !trimmedQuestion.isEmpty else { return }
                submit(trimmedQuestion)
            }
            .disabled(trimmedQuestion.isEmpty)
            temporalDrawerButton("Cancel", systemName: "xmark", role: .wall, showsChevron: TemporalDrawerActionLayout.terminalActionsShowChevron, action: dismiss)
        }
    }
}

struct SyncQueueDrawerView: View {
    let rows: [SyncQueueRowProjection]
    let pendingCount: Int
    let retry: () -> Void
    let dismiss: () -> Void

    var body: some View {
        temporalDrawerShell(title: "Local sync queue", subtitle: pendingCount == 1 ? "1 pending change" : "\(pendingCount) pending changes", dismiss: dismiss) {
            if rows.isEmpty {
                temporalQueueRow("No local changes", detail: "clear", role: .active)
            } else {
                ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                    temporalQueueRow(row.title, detail: row.detail, role: row.role)
                }
            }
            temporalDrawerButton("Retry sync", systemName: "arrow.triangle.2.circlepath", role: .active, showsChevron: TemporalDrawerActionLayout.directActionsShowChevron, action: retry)
            temporalDrawerButton("Close", systemName: "xmark", role: .wall, showsChevron: TemporalDrawerActionLayout.terminalActionsShowChevron, action: dismiss)
        }
    }
}

struct TimingRunEvidenceDrawerView: View {
    let openReview: () -> Void
    let askSimilarTime: () -> Void
    let startAgain: () -> Void
    let dismiss: () -> Void

    var body: some View {
        temporalDrawerShell(title: "Timing run evidence", subtitle: "Run evidence is shown only after timing data exists.", dismiss: dismiss) {
            temporalQueueRow("Reviewed evidence", detail: "from runs", role: .active)
            temporalQueueRow("Resource detours", detail: "from notes", role: .detour)
            temporalQueueRow("Model inclusion", detail: "review decides", role: .checkpoint)
            temporalDrawerButton("Open review", systemName: "checkmark.seal", role: .checkpoint, action: openReview)
            temporalDrawerButton("Ask similar time", systemName: "quote.bubble", role: .detour, action: askSimilarTime)
            temporalDrawerButton("Start this again", systemName: "timer", role: .active, action: startAgain)
        }
    }
}

struct TemporalAnswerEvidenceDrawerView: View {
    let useCheck: () -> Void
    let dismiss: () -> Void

    var body: some View {
        temporalDrawerShell(title: "Grounded answer evidence", subtitle: "Evidence is summarized; raw notes stay hidden by default.", dismiss: dismiss) {
            temporalQueueRow("Reviewed runs", detail: "required", role: .active)
            temporalQueueRow("Median wall time", detail: "computed", role: .wall)
            temporalQueueRow("Slow-case envelope", detail: "computed", role: .waiting)
            temporalQueueRow("Before starting", detail: "from evidence", role: .detour)
            temporalDrawerButton("Use check", systemName: "sparkles", role: .detour, action: useCheck)
            temporalDrawerButton("Close", systemName: "xmark", role: .wall, showsChevron: TemporalDrawerActionLayout.terminalActionsShowChevron, action: dismiss)
        }
    }
}

@ViewBuilder
@MainActor
private func temporalDrawerShell<Content: View>(
    title: String,
    subtitle: String,
    dismiss: @escaping () -> Void,
    @ViewBuilder content: @escaping () -> Content
) -> some View {
    Phase8DrawerOverlay(figmaSheetHeight: 520, dismiss: dismiss) { _ in
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.system(size: 24, weight: .bold, design: .rounded))
                        .foregroundStyle(Color(parallax: .textPrimaryLight))
                    Text(subtitle)
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                        .foregroundStyle(Color(parallax: .textSecondaryLight))
                }
                .padding(.top, 34)
                content()
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 28)
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
        .scrollIndicators(.hidden)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

@MainActor
private func temporalDrawerButton(
    _ title: String,
    systemName: String,
    role: TemporalSemanticRole,
    showsChevron: Bool = TemporalDrawerActionLayout.navigationActionsShowChevron,
    action: @escaping () -> Void
) -> some View {
    Button(action: action) {
        TemporalDrawerActionLabel(title: title, systemName: systemName, role: role, showsChevron: showsChevron)
    }
    .buttonStyle(.plain)
}

private struct TemporalDrawerActionLabel: View {
    let title: String
    let systemName: String
    let role: TemporalSemanticRole
    let showsChevron: Bool
    @Environment(\.isEnabled) private var isEnabled

    var body: some View {
        HStack(spacing: 10) {
            CircleIcon(
                systemName: systemName,
                tint: iconTint,
                fill: iconFill,
                size: 34,
                symbolSize: 14
            )
            Text(title)
                .font(.system(size: 14, weight: .semibold, design: .rounded))
                .foregroundStyle(textColor)
                .lineLimit(1)
                .minimumScaleFactor(0.78)
            Spacer()
            if showsChevron {
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color(parallax: .textTertiaryLight))
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, minHeight: 48)
        .background(backgroundColor)
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(parallax: .separatorLight), lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var textColor: Color {
        if isEnabled {
            return Color(parallax: .textPrimaryLight)
        }
        return Color(parallax: .textSecondaryLight).opacity(ParallaxDrawerActionLayout.disabledLabelOpacity)
    }

    private var iconTint: Color {
        if isEnabled {
            return Color(parallax: DesignTokenMapper.colorToken(for: role))
        }
        return Color(parallax: .textTertiaryLight).opacity(ParallaxDrawerActionLayout.disabledLabelOpacity)
    }

    private var iconFill: Color {
        if isEnabled {
            return Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true))
        }
        return Color(parallax: .separatorLight).opacity(ParallaxDrawerActionLayout.disabledBackgroundOpacity)
    }

    private var backgroundColor: Color {
        Color(parallax: .cardLight)
            .opacity(isEnabled ? 1 : ParallaxDrawerActionLayout.disabledBackgroundOpacity)
    }
}

@MainActor
private func temporalQueueRow(
    _ title: String,
    detail: String,
    role: TemporalSemanticRole
) -> some View {
    HStack(spacing: 10) {
        CircleIcon(
            systemName: "smallcircle.filled.circle",
            tint: Color(parallax: DesignTokenMapper.colorToken(for: role)),
            fill: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)),
            size: 28,
            symbolSize: 11
        )
        Text(title)
            .font(.system(size: 13, weight: .semibold, design: .rounded))
            .lineLimit(2)
            .minimumScaleFactor(0.82)
        Spacer()
        SoftBadge(text: detail, systemName: nil, role: role)
    }
    .padding(.vertical, 2)
}
