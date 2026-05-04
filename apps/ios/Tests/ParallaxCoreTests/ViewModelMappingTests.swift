import ParallaxCore
import ParallaxDesignSystem
import Testing

@Test func timingSessionStatesProjectFromCanonicalDomainState() {
    #expect(TimingSessionProjection(status: .running).primaryState == .running)
    #expect(TimingSessionProjection(status: .paused).primaryState == .paused)
    #expect(TimingSessionProjection(status: .completedUnreviewed).primaryState == .needsReview)
    #expect(TimingSessionProjection(status: .running, openSpan: .waiting).primaryState == .waitingActive)
    #expect(TimingSessionProjection(status: .running, openSpan: .resourceDetour).primaryState == .detourActive)
    #expect(TimingSessionProjection(status: .running, openSpan: .interruption).primaryState == .interruptionActive)
    #expect(TimingSessionProjection(status: .running, openSpan: .sideQuest).primaryState == .sideQuestActive)
    #expect(TimingSessionProjection(status: .running, isOffline: true).primaryState == .offlineCached)
    #expect(TimingSessionProjection(status: .running, hasPendingSync: true).primaryState == .syncPending)
}

@Test func temporalRolesPreserveCanonicalDesignTokenNames() {
    #expect(TemporalRoleMapper.role(for: .activeWork) == .active)
    #expect(TemporalRoleMapper.role(for: .resourceDetour) == .detour)
    #expect(TemporalRoleMapper.role(for: .setup) == .detour)
    #expect(TemporalRoleMapper.role(for: .interruption) == .interruption)
    #expect(TemporalRoleMapper.role(for: .waiting) == .waiting)
    #expect(TemporalRoleMapper.role(for: .startLatency) == .startLatency)

    #expect(DesignTokenMapper.colorToken(for: .active) == .active)
    #expect(DesignTokenMapper.colorToken(for: .detour, soft: true) == .detourSoft)
    #expect(DesignTokenMapper.colorToken(for: .privacy) == .waitingText)
}

@Test func defaultMeasurementModeChoicesStayWithinDesignTokenLimit() {
    let launcherModes = [MeasurementMode.wholeTask, .checkpointed, .calibration, .routine]
    let visibleModes = Array(launcherModes.prefix(ParallaxDesignTokens.Accessibility.maxDefaultModeChoices))

    #expect(visibleModes == [.wholeTask, .checkpointed, .calibration])
    #expect(ParallaxDesignTokens.Accessibility.colorOnlyStatesAllowed == false)
    #expect(ParallaxDesignTokens.Accessibility.dynamicTypeRequired == true)
}
