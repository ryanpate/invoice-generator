import AuthenticationServices
import SwiftUI

@Observable
final class AuthManager {
    var isLoggedIn = false
    var currentUser: UserInfo?

    private let api: APIClient

    init(api: APIClient) {
        self.api = api
        self.isLoggedIn = api.isAuthenticated
    }

    struct AuthResponse: Decodable {
        let access: String
        let refresh: String
        let user: UserInfo
    }

    struct UserInfo: Decodable, Sendable {
        let id: Int
        let email: String
        let subscriptionTier: String
    }

    func login(email: String, password: String) async throws {
        struct Body: Encodable { let email: String; let password: String }
        let response: AuthResponse = try await api.post("auth/login/", body: Body(email: email, password: password))
        api.saveTokens(access: response.access, refresh: response.refresh)
        currentUser = response.user
        isLoggedIn = true
    }

    func register(email: String, password: String, passwordConfirm: String) async throws {
        struct Body: Encodable { let email: String; let password: String; let passwordConfirm: String }
        let response: AuthResponse = try await api.post("auth/register/", body: Body(email: email, password: password, passwordConfirm: passwordConfirm))
        api.saveTokens(access: response.access, refresh: response.refresh)
        currentUser = response.user
        isLoggedIn = true
    }

    func signInWithApple(authorization: ASAuthorization) async throws {
        guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
              let tokenData = credential.identityToken,
              let idToken = String(data: tokenData, encoding: .utf8) else {
            throw AuthError.invalidCredential
        }

        struct Body: Encodable {
            let idToken: String
            let firstName: String
            let lastName: String
        }

        let body = Body(
            idToken: idToken,
            firstName: credential.fullName?.givenName ?? "",
            lastName: credential.fullName?.familyName ?? ""
        )

        let response: AuthResponse = try await api.post("auth/social/apple/", body: body)
        api.saveTokens(access: response.access, refresh: response.refresh)
        currentUser = response.user
        isLoggedIn = true
    }

    func signInWithGoogle(idToken: String) async throws {
        struct Body: Encodable { let idToken: String }
        let response: AuthResponse = try await api.post("auth/social/google/", body: Body(idToken: idToken))
        api.saveTokens(access: response.access, refresh: response.refresh)
        currentUser = response.user
        isLoggedIn = true
    }

    func logout() {
        api.clearTokens()
        currentUser = nil
        isLoggedIn = false
    }

    func deleteAccount() async throws {
        try await api.delete("auth/account/")
        logout()
    }

    enum AuthError: Error {
        case invalidCredential
    }
}
