import Foundation

public enum OFFMateAPIError: Error, Equatable, Sendable {
    case invalidResponse
    case http(statusCode: Int, detail: String)
    case invalidUploadURL
}

public struct RemoteSessionSnapshot: Codable, Equatable, Sendable {
    public let sessionId: String
    public let ownerUserId: String
    public let controllerUserId: String
    public let state: SessionState
    public let defaultPenalty: PenaltyType
    public let activePenalty: PenaltyType?
    public let penaltyWindowClosesAt: Date?
    public let activeProofId: String?
    public let createdAt: Date
    public let updatedAt: Date
}

public struct UploadSlotSnapshot: Codable, Equatable, Sendable {
    public let uploadUrl: String
    public let imageKey: String
    public let expiresAt: Date
    public let requiredContentType: String
}

public struct ProofReceipt: Codable, Equatable, Sendable {
    public let proofId: String
    public let imageKey: String
    public let submittedAt: Date
}

public struct AnalysisEnvelope: Codable, Equatable, Sendable {
    public let session: RemoteSessionSnapshot
    public let analysis: AIAnalysis
}

private struct CreateSessionPayload: Encodable, Sendable {
    let activeMemberIds: [String]
    let defaultPenalty: PenaltyType
}

private struct SelectPenaltyPayload: Encodable, Sendable {
    let penalty: PenaltyType
}

private struct UploadSlotPayload: Encodable, Sendable {
    let contentType: String
}

private struct SubmitProofPayload: Encodable, Sendable {
    let imageKey: String
}

private struct ResolveReviewPayload: Encodable, Sendable {
    let passed: Bool
}

private struct EmptyPayload: Encodable, Sendable {}

public actor OFFMateAPIClient {
    private let baseURL: URL
    private let urlSession: URLSession
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(
        baseURL: URL = URL(string: "http://127.0.0.1:8000")!,
        urlSession: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.urlSession = urlSession
        self.encoder = JSONEncoder.offMate
        self.decoder = JSONDecoder.offMate
    }

    public func createSession(
        ownerUserId: String,
        activeMemberIds: [String],
        defaultPenalty: PenaltyType,
        idempotencyKey: String = UUID().uuidString
    ) async throws -> RemoteSessionSnapshot {
        try await send(
            method: "POST",
            path: "/v1/sessions",
            userId: ownerUserId,
            idempotencyKey: idempotencyKey,
            body: CreateSessionPayload(
                activeMemberIds: activeMemberIds,
                defaultPenalty: defaultPenalty
            )
        )
    }

    public func getSession(
        sessionId: String,
        userId: String
    ) async throws -> RemoteSessionSnapshot {
        try await send(
            method: "GET",
            path: "/v1/sessions/\(sessionId)",
            userId: userId,
            idempotencyKey: nil,
            body: Optional<EmptyPayload>.none
        )
    }

    public func startSession(
        sessionId: String,
        ownerUserId: String,
        idempotencyKey: String = UUID().uuidString
    ) async throws -> RemoteSessionSnapshot {
        try await command(
            path: "/v1/sessions/\(sessionId)/start",
            userId: ownerUserId,
            idempotencyKey: idempotencyKey
        )
    }

    public func endSession(
        sessionId: String,
        ownerUserId: String,
        idempotencyKey: String = UUID().uuidString
    ) async throws -> RemoteSessionSnapshot {
        try await command(
            path: "/v1/sessions/\(sessionId)/end",
            userId: ownerUserId,
            idempotencyKey: idempotencyKey
        )
    }

    public func selectPenalty(
        sessionId: String,
        controllerUserId: String,
        penalty: PenaltyType,
        idempotencyKey: String = UUID().uuidString
    ) async throws -> RemoteSessionSnapshot {
        try await send(
            method: "POST",
            path: "/v1/sessions/\(sessionId)/penalties",
            userId: controllerUserId,
            idempotencyKey: idempotencyKey,
            body: SelectPenaltyPayload(penalty: penalty)
        )
    }

    public func uploadProofImage(
        _ imageData: Data,
        contentType: String,
        ownerUserId: String,
        idempotencyKey: String = UUID().uuidString
    ) async throws -> String {
        let slot: UploadSlotSnapshot = try await send(
            method: "POST",
            path: "/v1/upload-slots",
            userId: ownerUserId,
            idempotencyKey: idempotencyKey,
            body: UploadSlotPayload(contentType: contentType)
        )
        guard let uploadURL = URL(string: slot.uploadUrl, relativeTo: baseURL)?.absoluteURL else {
            throw OFFMateAPIError.invalidUploadURL
        }
        var request = URLRequest(url: uploadURL)
        request.httpMethod = "PUT"
        request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        request.httpBody = imageData
        let (data, response) = try await urlSession.data(for: request)
        try Self.requireSuccess(response: response, data: data)
        return slot.imageKey
    }

    public func submitProof(
        sessionId: String,
        ownerUserId: String,
        imageKey: String,
        idempotencyKey: String = UUID().uuidString
    ) async throws -> ProofReceipt {
        try await send(
            method: "POST",
            path: "/v1/sessions/\(sessionId)/proofs",
            userId: ownerUserId,
            idempotencyKey: idempotencyKey,
            body: SubmitProofPayload(imageKey: imageKey)
        )
    }

    public func analyzeProof(
        sessionId: String,
        ownerUserId: String,
        idempotencyKey: String = UUID().uuidString
    ) async throws -> AnalysisEnvelope {
        try await send(
            method: "POST",
            path: "/v1/sessions/\(sessionId)/analyze",
            userId: ownerUserId,
            idempotencyKey: idempotencyKey,
            body: Optional<EmptyPayload>.none
        )
    }

    public func resolveHumanReview(
        sessionId: String,
        controllerUserId: String,
        passed: Bool,
        idempotencyKey: String = UUID().uuidString
    ) async throws -> RemoteSessionSnapshot {
        try await send(
            method: "POST",
            path: "/v1/sessions/\(sessionId)/review",
            userId: controllerUserId,
            idempotencyKey: idempotencyKey,
            body: ResolveReviewPayload(passed: passed)
        )
    }

    private func command(
        path: String,
        userId: String,
        idempotencyKey: String
    ) async throws -> RemoteSessionSnapshot {
        try await send(
            method: "POST",
            path: path,
            userId: userId,
            idempotencyKey: idempotencyKey,
            body: Optional<EmptyPayload>.none
        )
    }

    private func send<Response: Decodable & Sendable, Body: Encodable & Sendable>(
        method: String,
        path: String,
        userId: String,
        idempotencyKey: String?,
        body: Body?
    ) async throws -> Response {
        let url = baseURL.appending(path: path)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue(userId, forHTTPHeaderField: "X-User-ID")
        if let idempotencyKey {
            request.setValue(idempotencyKey, forHTTPHeaderField: "Idempotency-Key")
        }
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await urlSession.data(for: request)
        try Self.requireSuccess(response: response, data: data)
        return try decoder.decode(Response.self, from: data)
    }

    private static func requireSuccess(response: URLResponse, data: Data) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw OFFMateAPIError.invalidResponse
        }
        guard 200..<300 ~= httpResponse.statusCode else {
            let detail = (try? JSONDecoder().decode(APIErrorEnvelope.self, from: data).detail)
                ?? "Request failed"
            throw OFFMateAPIError.http(
                statusCode: httpResponse.statusCode,
                detail: detail
            )
        }
    }
}

private struct APIErrorEnvelope: Decodable {
    let detail: String
}

private extension JSONEncoder {
    static var offMate: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }
}

private extension JSONDecoder {
    static var offMate: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let value = try container.decode(String.self)
            let withFractionalSeconds = ISO8601DateFormatter()
            withFractionalSeconds.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = withFractionalSeconds.date(from: value) {
                return date
            }
            let standard = ISO8601DateFormatter()
            if let date = standard.date(from: value) {
                return date
            }
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Invalid ISO-8601 date: \(value)"
            )
        }
        return decoder
    }
}
