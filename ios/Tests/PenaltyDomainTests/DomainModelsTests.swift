import Foundation
import Testing
@testable import PenaltyDomain

@Test("Penalty enum contains only the four requested values")
func penaltyValues() {
    #expect(Set(PenaltyType.allCases.map(\.rawValue)) == Set([
        "BLOCK",
        "GRAYSCALE",
        "OBSTRUCTION",
        "MUTED",
    ]))
}

@Test("AI analysis decodes the shared snake_case contract")
func decodeAIAnalysis() throws {
    let payload = #"""
    {
      "analysis_id": "analysis_123",
      "detected_activities": [
        {
          "activity_id": "reading_book",
          "confidence": 0.93,
          "visual_evidence": ["open book"]
        }
      ],
      "decision": "PASS",
      "decision_confidence": 0.91,
      "matched_policy_ids": ["policy_self_development"],
      "reason": "The image provides evidence of reading.",
      "requires_human_review": false
    }
    """#.data(using: .utf8)!

    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    let analysis = try decoder.decode(AIAnalysis.self, from: payload)

    #expect(analysis.analysisId == "analysis_123")
    #expect(analysis.decision == .pass)
    #expect(analysis.detectedActivities.first?.activityId == "reading_book")
}
