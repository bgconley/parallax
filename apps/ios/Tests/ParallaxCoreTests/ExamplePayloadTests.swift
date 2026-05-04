import Foundation
import ParallaxCore
import Testing

@Test func spongeDetourExampleMapsToTemporalProjection() throws {
    let payload: SpongeDetourRun = try loadExamplePayload("sample_sponge_detour_run.json")

    #expect(payload.activity.displayName == "Clean pots and pans")
    #expect(payload.session.status == "running")
    #expect(payload.expectedExtractedEvent.spanType == "resource_detour")
    #expect(payload.expectedExtractedEvent.resourceName == "sponge")
    #expect(payload.expectedExtractedEvent.countPolicy == CountPolicy.wallOnly.rawValue)
    #expect(payload.expectedExtractedEvent.suggestedPreflightText == "Check sponge or scrubber before starting.")

    let projection = TimingSessionProjection(status: .running, openSpan: .resourceDetour)
    #expect(projection.primaryState == .detourActive)
    #expect(TemporalRoleMapper.chip(for: .resourceDetour).label == "Detour")
}

@Test func activityProfilePayloadCarriesPreflightAndConfidenceEvidence() throws {
    let payload: ActivityProfilePayload = try loadExamplePayload("sample_activity_profile_response.json")

    #expect(payload.activity.displayName == "Clean pots and pans")
    #expect(payload.latestStats.sampleSize == 6)
    #expect(payload.latestStats.confidence == "medium")
    #expect(payload.preflightChecks.first?.checkText == "Check sponge or scrubber before starting.")
    #expect(payload.preflightChecks.first?.source == "resource_dependency")
    #expect(payload.limitations.contains("Only 6 reviewed runs. Estimates may still shift."))
}

@Test func temporalQueryPayloadKeepsAnswersEvidenceBackedAndPrivate() throws {
    let payload: TemporalQueryPayload = try loadExamplePayload("sample_temporal_query_answer.json")

    #expect(payload.question == "What usually delays pots and pans?")
    #expect(payload.confidence == "medium")
    #expect(payload.sampleSize == 6)
    #expect(payload.computedFacts.resourceEventCount == 3)
    #expect(payload.evidence.first?.summary.contains("sponge") == true)
    #expect(payload.limitations.contains("Private raw notes were not quoted."))
}

private func loadExamplePayload<T: Decodable>(_ fileName: String) throws -> T {
    let payloadURL = repositoryRoot()
        .appendingPathComponent("parallax_v1_3_artifact_pack/examples/payloads")
        .appendingPathComponent(fileName)
    let data = try Data(contentsOf: payloadURL)
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    return try decoder.decode(T.self, from: data)
}

private func repositoryRoot() -> URL {
    URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
}

private struct SpongeDetourRun: Decodable {
    struct Activity: Decodable {
        let displayName: String
    }

    struct Session: Decodable {
        let status: String
    }

    struct ExpectedExtractedEvent: Decodable {
        let spanType: String
        let resourceName: String
        let countPolicy: String
        let suggestedPreflightText: String
    }

    let activity: Activity
    let session: Session
    let expectedExtractedEvent: ExpectedExtractedEvent
}

private struct ActivityProfilePayload: Decodable {
    struct Activity: Decodable {
        let displayName: String
    }

    struct LatestStats: Decodable {
        let sampleSize: Int
        let confidence: String
    }

    struct PreflightCheck: Decodable {
        let checkText: String
        let source: String
    }

    let activity: Activity
    let latestStats: LatestStats
    let preflightChecks: [PreflightCheck]
    let limitations: [String]
}

private struct TemporalQueryPayload: Decodable {
    struct ComputedFacts: Decodable {
        let resourceEventCount: Int
    }

    struct Evidence: Decodable {
        let summary: String
    }

    let question: String
    let confidence: String
    let sampleSize: Int
    let computedFacts: ComputedFacts
    let limitations: [String]
    let evidence: [Evidence]
}
