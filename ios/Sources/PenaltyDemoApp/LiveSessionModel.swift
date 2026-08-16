import Combine
import Foundation
import PenaltyDomain

@MainActor
final class LiveSessionModel: ObservableObject {
    @Published private(set) var session: RemoteSessionSnapshot?
    @Published private(set) var analysis: AIAnalysis?
    @Published private(set) var isLoading = false
    @Published private(set) var isConnected = false
    @Published var errorMessage: String?

    let ownerUserId = "user_a"
    let controllerUserId = "user_b"

    private let api: OFFMateAPIClient

    init(api: OFFMateAPIClient = OFFMateAPIClient()) {
        self.api = api
    }

    func prepareSession(defaultPenalty: PenaltyType) async -> Bool {
        await perform {
            let created = try await api.createSession(
                ownerUserId: ownerUserId,
                activeMemberIds: [controllerUserId],
                defaultPenalty: defaultPenalty
            )
            session = try await api.startSession(
                sessionId: created.sessionId,
                ownerUserId: ownerUserId
            )
            analysis = nil
            isConnected = true
        }
    }

    func endViewing() async -> Bool {
        await perform {
            let sessionId = try requireSessionId()
            session = try await api.endSession(
                sessionId: sessionId,
                ownerUserId: ownerUserId
            )
        }
    }

    func selectPenalty(_ penalty: PenaltyType) async -> Bool {
        await perform {
            let sessionId = try requireSessionId()
            session = try await api.selectPenalty(
                sessionId: sessionId,
                controllerUserId: controllerUserId,
                penalty: penalty
            )
        }
    }

    func submitAndAnalyze(sample: ProofSample) async -> Bool {
        let sampleBytes: Data
        switch sample {
        case .reading:
            sampleBytes = Data("book sample image".utf8)
        case .gaming:
            sampleBytes = Data("game sample image".utf8)
        case .unclear:
            sampleBytes = Data("ambiguous sample image".utf8)
        }
        return await submitAndAnalyze(
            imageData: sampleBytes,
            contentType: "image/jpeg"
        )
    }

    func submitAndAnalyze(imageData: Data, contentType: String) async -> Bool {
        await perform {
            let sessionId = try requireSessionId()
            let imageKey = try await api.uploadProofImage(
                imageData,
                contentType: contentType,
                ownerUserId: ownerUserId
            )
            _ = try await api.submitProof(
                sessionId: sessionId,
                ownerUserId: ownerUserId,
                imageKey: imageKey
            )
            let envelope = try await api.analyzeProof(
                sessionId: sessionId,
                ownerUserId: ownerUserId
            )
            session = envelope.session
            analysis = envelope.analysis
        }
    }

    func resolveHumanReview(passed: Bool) async -> Bool {
        await perform {
            let sessionId = try requireSessionId()
            session = try await api.resolveHumanReview(
                sessionId: sessionId,
                controllerUserId: controllerUserId,
                passed: passed
            )
        }
    }

    private func perform(_ operation: () async throws -> Void) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            try await operation()
            return true
        } catch {
            errorMessage = Self.message(for: error)
            return false
        }
    }

    private func requireSessionId() throws -> String {
        guard let session else {
            throw LiveSessionError.sessionNotPrepared
        }
        return session.sessionId
    }

    private static func message(for error: Error) -> String {
        if let apiError = error as? OFFMateAPIError {
            switch apiError {
            case .invalidResponse:
                return "서버 응답을 확인할 수 없습니다."
            case let .http(statusCode, detail):
                return "API \(statusCode): \(detail)"
            case .invalidUploadURL:
                return "사진 업로드 주소가 올바르지 않습니다."
            }
        }
        return "서버 연결에 실패했습니다: \(error.localizedDescription)"
    }
}

private enum LiveSessionError: LocalizedError {
    case sessionNotPrepared

    var errorDescription: String? {
        "먼저 이용 세션을 생성해야 합니다."
    }
}
