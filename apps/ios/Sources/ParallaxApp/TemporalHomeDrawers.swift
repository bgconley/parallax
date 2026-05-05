import ParallaxCore
import ParallaxDesignSystem
import SwiftUI

struct TemporalNavigationDrawerView: View {
    let navigate: (TemporalHomeSurfaceState) -> Void
    let dismiss: () -> Void

    var body: some View {
        temporalDrawerShell(title: "Temporal navigation", subtitle: "Only timing, review, sync, and grounded answers.") {
            temporalDrawerButton("Current run", systemName: "timer", role: .active) {
                navigate(.expandedTimingRun)
            }
            temporalDrawerButton("Needs review", systemName: "checkmark.seal", role: .checkpoint) {
                navigate(.needsReview)
            }
            temporalDrawerButton("Sync queue", systemName: "arrow.triangle.2.circlepath", role: .waiting) {
                navigate(.syncPending)
            }
            temporalDrawerButton("Ask about time", systemName: "quote.bubble", role: .detour) {
                navigate(.groundedAnswer)
            }
            temporalDrawerButton("Close", systemName: "xmark", role: .wall, action: dismiss)
        }
    }
}

struct QuickCaptureDrawerView: View {
    let save: (String) -> Void
    let dismiss: () -> Void
    @State private var note = ""

    var body: some View {
        temporalDrawerShell(title: "Capture timing evidence", subtitle: "Saved locally first; sync can retry later.") {
            Card(background: Color(parallax: .elevatedLight)) {
                TextField("What happened?", text: $note, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(3, reservesSpace: true)
                Text("Queued as a quick timing annotation.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color(parallax: .textSecondaryLight))
            }
            temporalDrawerButton("Save timing note", systemName: "tray.and.arrow.down", role: .active) {
                save(note.trimmingCharacters(in: .whitespacesAndNewlines))
            }
            temporalDrawerButton("Cancel", systemName: "xmark", role: .wall, action: dismiss)
        }
    }
}

struct SyncQueueDrawerView: View {
    let pendingCount: Int
    let retry: () -> Void
    let dismiss: () -> Void

    var body: some View {
        temporalDrawerShell(title: "Local sync queue", subtitle: "\(pendingCount) pending mutation\(pendingCount == 1 ? "" : "s")") {
            temporalQueueRow("session_started", detail: "queued", role: .active)
            temporalQueueRow("resource_detour", detail: "queued", role: .detour)
            temporalQueueRow("review_saved", detail: "queued", role: .checkpoint)
            temporalQueueRow("preflight decision", detail: "queued", role: .waiting)
            temporalDrawerButton("Retry sync", systemName: "arrow.triangle.2.circlepath", role: .active, action: retry)
            temporalDrawerButton("Close", systemName: "xmark", role: .wall, action: dismiss)
        }
    }
}

struct TimingRunEvidenceDrawerView: View {
    let openReview: () -> Void
    let askSimilarTime: () -> Void
    let startAgain: () -> Void

    var body: some View {
        temporalDrawerShell(title: "Timing run evidence", subtitle: "Run evidence is shown only after timing data exists.") {
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
        temporalDrawerShell(title: "Grounded answer evidence", subtitle: "Evidence is summarized; raw notes stay hidden by default.") {
            temporalQueueRow("Reviewed runs", detail: "required", role: .active)
            temporalQueueRow("Median wall time", detail: "computed", role: .wall)
            temporalQueueRow("Slow-case envelope", detail: "computed", role: .waiting)
            temporalQueueRow("Before starting", detail: "from evidence", role: .detour)
            temporalDrawerButton("Use check", systemName: "sparkles", role: .detour, action: useCheck)
            temporalDrawerButton("Close", systemName: "xmark", role: .wall, action: dismiss)
        }
    }
}

@ViewBuilder
@MainActor
private func temporalDrawerShell<Content: View>(
    title: String,
    subtitle: String,
    @ViewBuilder content: @escaping () -> Content
) -> some View {
    Phase8DrawerOverlay(figmaSheetHeight: 520, dismiss: {}) { _ in
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
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

@MainActor
private func temporalDrawerButton(
    _ title: String,
    systemName: String,
    role: TemporalSemanticRole,
    action: @escaping () -> Void
) -> some View {
    Button(action: action) {
        HStack(spacing: 10) {
            CircleIcon(
                systemName: systemName,
                tint: Color(parallax: DesignTokenMapper.colorToken(for: role)),
                fill: Color(parallax: DesignTokenMapper.colorToken(for: role, soft: true)),
                size: 34,
                symbolSize: 14
            )
            Text(title)
                .font(.system(size: 14, weight: .semibold, design: .rounded))
                .foregroundStyle(Color(parallax: .textPrimaryLight))
            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption.weight(.bold))
                .foregroundStyle(Color(parallax: .textTertiaryLight))
        }
        .padding(10)
        .frame(maxWidth: .infinity, minHeight: 48)
        .background(Color(parallax: .cardLight))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(parallax: .separatorLight), lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
    .buttonStyle(.plain)
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
            .lineLimit(1)
        Spacer()
        SoftBadge(text: detail, systemName: nil, role: role)
    }
    .padding(.vertical, 2)
}
