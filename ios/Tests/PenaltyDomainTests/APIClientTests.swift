import Foundation
import Testing
@testable import PenaltyDomain

@Test("API client sends auth, idempotency, and snake_case session payload")
func createRemoteSession() async throws {
    let configuration = URLSessionConfiguration.ephemeral
    configuration.protocolClasses = [URLProtocolStub.self]
    let session = URLSession(configuration: configuration)
    let responseJSON = #"""
    {
      "session_id": "session_1",
      "owner_user_id": "user_a",
      "controller_user_id": "user_b",
      "state": "SCHEDULED",
      "default_penalty": "BLOCK",
      "active_penalty": null,
      "penalty_window_closes_at": null,
      "active_proof_id": null,
      "created_at": "2026-08-16T08:00:00Z",
      "updated_at": "2026-08-16T08:00:00Z"
    }
    """#.data(using: .utf8)!

    URLProtocolStub.handler = { request in
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: 201,
            httpVersion: nil,
            headerFields: ["Content-Type": "application/json"]
        )!
        return (response, responseJSON)
    }
    defer {
        URLProtocolStub.handler = nil
        URLProtocolStub.lastRequest = nil
        URLProtocolStub.lastBody = nil
    }

    let client = OFFMateAPIClient(
        baseURL: URL(string: "http://127.0.0.1:8000")!,
        urlSession: session
    )
    let snapshot = try await client.createSession(
        ownerUserId: "user_a",
        activeMemberIds: ["user_b"],
        defaultPenalty: .block,
        idempotencyKey: "create-session-1"
    )

    let request = try #require(URLProtocolStub.lastRequest)
    let requestBody = try #require(URLProtocolStub.lastBody)
    let body = try JSONSerialization.jsonObject(with: requestBody) as? [String: Any]

    #expect(request.value(forHTTPHeaderField: "X-User-ID") == "user_a")
    #expect(request.value(forHTTPHeaderField: "Idempotency-Key") == "create-session-1")
    #expect(body?["default_penalty"] as? String == "BLOCK")
    #expect(body?["active_member_ids"] as? [String] == ["user_b"])
    #expect(snapshot.sessionId == "session_1")
    #expect(snapshot.controllerUserId == "user_b")
}

private final class URLProtocolStub: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?
    nonisolated(unsafe) static var lastRequest: URLRequest?
    nonisolated(unsafe) static var lastBody: Data?

    override class func canInit(with request: URLRequest) -> Bool { true }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        do {
            Self.lastRequest = request
            Self.lastBody = request.httpBody ?? Self.readBodyStream(request.httpBodyStream)
            guard let handler = Self.handler else {
                throw OFFMateAPIError.invalidResponse
            }
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}

    private static func readBodyStream(_ stream: InputStream?) -> Data? {
        guard let stream else { return nil }
        stream.open()
        defer { stream.close() }
        var data = Data()
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: 4096)
        defer { buffer.deallocate() }
        while stream.hasBytesAvailable {
            let count = stream.read(buffer, maxLength: 4096)
            if count <= 0 { break }
            data.append(buffer, count: count)
        }
        return data
    }
}
