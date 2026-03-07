import Foundation

@Observable
final class APIClient {
    private(set) var accessToken: String?
    private(set) var refreshToken: String?

    private let keychain = KeychainManager.shared
    private let session = URLSession.shared
    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        d.dateDecodingStrategy = .iso8601
        return d
    }()
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        e.dateEncodingStrategy = .iso8601
        return e
    }()

    init() {
        loadTokens()
    }

    var isAuthenticated: Bool { accessToken != nil }

    // MARK: - Token Management

    func saveTokens(access: String, refresh: String) {
        accessToken = access
        refreshToken = refresh
        try? keychain.save(Data(access.utf8), for: "access_token")
        try? keychain.save(Data(refresh.utf8), for: "refresh_token")
    }

    func clearTokens() {
        accessToken = nil
        refreshToken = nil
        try? keychain.delete(for: "access_token")
        try? keychain.delete(for: "refresh_token")
    }

    private func loadTokens() {
        if let data = try? keychain.load(for: "access_token") {
            accessToken = String(data: data, encoding: .utf8)
        }
        if let data = try? keychain.load(for: "refresh_token") {
            refreshToken = String(data: data, encoding: .utf8)
        }
    }

    // MARK: - Requests

    func request<T: Decodable>(
        _ method: String,
        path: String,
        body: (any Encodable)? = nil,
        queryItems: [URLQueryItem]? = nil
    ) async throws -> T {
        var url = Constants.apiBaseURL.appendingPathComponent(path)
        if let queryItems {
            var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
            components.queryItems = queryItems
            url = components.url!
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body {
            request.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await session.data(for: request)
        let httpResponse = response as! HTTPURLResponse

        if httpResponse.statusCode == 401 {
            if try await refreshAccessToken() {
                return try await self.request(method, path: path, body: body, queryItems: queryItems)
            }
            throw APIError.unauthorized
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode, data)
        }

        return try decoder.decode(T.self, from: data)
    }

    func get<T: Decodable>(_ path: String, queryItems: [URLQueryItem]? = nil) async throws -> T {
        try await request("GET", path: path, queryItems: queryItems)
    }

    func post<T: Decodable>(_ path: String, body: (any Encodable)? = nil) async throws -> T {
        try await request("POST", path: path, body: body)
    }

    func put<T: Decodable>(_ path: String, body: (any Encodable)? = nil) async throws -> T {
        try await request("PUT", path: path, body: body)
    }

    func delete(_ path: String) async throws {
        let _: EmptyResponse = try await request("DELETE", path: path)
    }

    // MARK: - Token Refresh

    private func refreshAccessToken() async throws -> Bool {
        guard let refresh = refreshToken else { return false }

        struct RefreshBody: Encodable { let refresh: String }
        struct RefreshResponse: Decodable { let access: String }

        var request = URLRequest(url: Constants.apiBaseURL.appendingPathComponent("auth/token/refresh/"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(RefreshBody(refresh: refresh))

        let (data, response) = try await session.data(for: request)
        guard (response as! HTTPURLResponse).statusCode == 200 else {
            clearTokens()
            return false
        }

        let result = try decoder.decode(RefreshResponse.self, from: data)
        accessToken = result.access
        try? keychain.save(Data(result.access.utf8), for: "access_token")
        return true
    }

    // MARK: - Multipart Upload

    func upload<T: Decodable>(_ path: String, fileData: Data, filename: String, mimeType: String) async throws -> T {
        let url = Constants.apiBaseURL.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await session.data(for: request)
        guard (200...299).contains((response as! HTTPURLResponse).statusCode) else {
            throw APIError.httpError((response as! HTTPURLResponse).statusCode, data)
        }
        return try decoder.decode(T.self, from: data)
    }
}

enum APIError: Error {
    case unauthorized
    case httpError(Int, Data)
}

struct EmptyResponse: Decodable {}
