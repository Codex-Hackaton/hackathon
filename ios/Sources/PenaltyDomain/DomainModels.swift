import Foundation

public enum PenaltyType: String, Codable, CaseIterable, Sendable {
    case block = "BLOCK"
    case grayscale = "GRAYSCALE"
    case obstruction = "OBSTRUCTION"
    case muted = "MUTED"
}

public enum SessionState: String, Codable, Sendable {
    case draft = "DRAFT"
    case scheduled = "SCHEDULED"
    case viewingWindowActive = "VIEWING_WINDOW_ACTIVE"
    case penaltyActive = "PENALTY_ACTIVE"
    case aiAnalyzing = "AI_ANALYZING"
    case humanReview = "HUMAN_REVIEW"
    case completed = "COMPLETED"
}

public enum AIAnalysisDecision: String, Codable, Sendable {
    case pass = "PASS"
    case fail = "FAIL"
    case humanReview = "HUMAN_REVIEW"
}

public struct DetectedActivity: Codable, Equatable, Sendable {
    public let activityId: String
    public let confidence: Double
    public let visualEvidence: [String]

    public init(
        activityId: String,
        confidence: Double,
        visualEvidence: [String]
    ) {
        self.activityId = activityId
        self.confidence = confidence
        self.visualEvidence = visualEvidence
    }

}

public struct AIAnalysis: Codable, Equatable, Sendable {
    public let analysisId: String
    public let detectedActivities: [DetectedActivity]
    public let decision: AIAnalysisDecision
    public let decisionConfidence: Double
    public let matchedPolicyIds: [String]
    public let reason: String
    public let requiresHumanReview: Bool

    public init(
        analysisId: String,
        detectedActivities: [DetectedActivity],
        decision: AIAnalysisDecision,
        decisionConfidence: Double,
        matchedPolicyIds: [String],
        reason: String,
        requiresHumanReview: Bool
    ) {
        self.analysisId = analysisId
        self.detectedActivities = detectedActivities
        self.decision = decision
        self.decisionConfidence = decisionConfidence
        self.matchedPolicyIds = matchedPolicyIds
        self.reason = reason
        self.requiresHumanReview = requiresHumanReview
    }

}

public struct ViewingSessionSnapshot: Codable, Equatable, Sendable {
    public let sessionId: String
    public let ownerUserId: String
    public let state: SessionState
    public let activePenalty: PenaltyType?
    public let penaltyWindowClosesAt: Date?

    public init(
        sessionId: String,
        ownerUserId: String,
        state: SessionState,
        activePenalty: PenaltyType?,
        penaltyWindowClosesAt: Date?
    ) {
        self.sessionId = sessionId
        self.ownerUserId = ownerUserId
        self.state = state
        self.activePenalty = activePenalty
        self.penaltyWindowClosesAt = penaltyWindowClosesAt
    }

}
