import AuthenticationServices
import SwiftUI

struct SignInView: View {
    @Environment(AppState.self) private var appState

    @State private var email: String = ""
    @State private var password: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String?
    @State private var showError: Bool = false
    @State private var navigateToSignUp: Bool = false

    private var authManager: AuthManager { appState.auth }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 0) {
                    // MARK: - Header
                    VStack(spacing: 8) {
                        Image(systemName: "doc.text.fill")
                            .font(.system(size: 56, weight: .semibold))
                            .foregroundStyle(.blue)
                            .padding(.bottom, 4)

                        Text("InvoiceKits")
                            .font(.system(size: 32, weight: .bold, design: .rounded))
                            .foregroundStyle(.primary)

                        Text("AI-Powered Invoicing")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.top, 56)
                    .padding(.bottom, 40)

                    // MARK: - Social Sign-In
                    VStack(spacing: 12) {
                        SignInWithAppleButton(.signIn) { request in
                            request.requestedScopes = [.fullName, .email]
                        } onCompletion: { result in
                            handleAppleSignIn(result: result)
                        }
                        .signInWithAppleButtonStyle(.black)
                        .frame(height: 50)
                        .cornerRadius(10)

                        GoogleSignInButton {
                            // GoogleSignIn SDK integration point — replace with GIDSignIn call
                            // when the GoogleSignIn package is added to the project.
                            // Example:
                            //   GIDSignIn.sharedInstance.signIn(withPresenting: rootVC) { result, error in
                            //       guard let idToken = result?.user.idToken?.tokenString else { return }
                            //       Task { try await authManager.signInWithGoogle(idToken: idToken) }
                            //   }
                        }
                    }
                    .padding(.horizontal, 24)

                    // MARK: - Divider
                    HStack(spacing: 12) {
                        Rectangle()
                            .frame(height: 1)
                            .foregroundStyle(.separator)
                        Text("or")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Rectangle()
                            .frame(height: 1)
                            .foregroundStyle(.separator)
                    }
                    .padding(.horizontal, 24)
                    .padding(.vertical, 24)

                    // MARK: - Email / Password Fields
                    VStack(spacing: 14) {
                        TextField("Email", text: $email)
                            .textContentType(.emailAddress)
                            .keyboardType(.emailAddress)
                            .autocapitalization(.none)
                            .autocorrectionDisabled()
                            .padding(.horizontal, 16)
                            .padding(.vertical, 14)
                            .background(Color(.secondarySystemBackground))
                            .cornerRadius(10)

                        SecureField("Password", text: $password)
                            .textContentType(.password)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 14)
                            .background(Color(.secondarySystemBackground))
                            .cornerRadius(10)
                    }
                    .padding(.horizontal, 24)

                    // MARK: - Sign In Button
                    Button(action: signIn) {
                        Group {
                            if isLoading {
                                ProgressView()
                                    .progressViewStyle(.circular)
                                    .tint(.white)
                            } else {
                                Text("Sign In")
                                    .font(.system(size: 16, weight: .semibold))
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(signInButtonBackground)
                        .foregroundStyle(.white)
                        .cornerRadius(10)
                    }
                    .disabled(isLoading || !isFormValid)
                    .padding(.horizontal, 24)
                    .padding(.top, 20)

                    // MARK: - Sign Up Link
                    NavigationLink(destination: SignUpView(), isActive: $navigateToSignUp) {
                        EmptyView()
                    }

                    Button {
                        navigateToSignUp = true
                    } label: {
                        HStack(spacing: 4) {
                            Text("Don't have an account?")
                                .foregroundStyle(.secondary)
                            Text("Sign Up")
                                .fontWeight(.semibold)
                                .foregroundStyle(.blue)
                        }
                        .font(.subheadline)
                    }
                    .padding(.top, 24)
                    .padding(.bottom, 40)
                }
            }
            .scrollBounceBehavior(.basedOnSize)
            .navigationBarHidden(true)
        }
        .alert("Sign In Failed", isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "An unexpected error occurred. Please try again.")
        }
    }

    // MARK: - Computed Properties

    private var isFormValid: Bool {
        !email.trimmingCharacters(in: .whitespaces).isEmpty && !password.isEmpty
    }

    private var signInButtonBackground: Color {
        isFormValid && !isLoading ? .blue : Color(.systemGray3)
    }

    // MARK: - Actions

    private func signIn() {
        guard isFormValid else { return }
        isLoading = true
        Task {
            do {
                try await authManager.login(
                    email: email.trimmingCharacters(in: .whitespaces),
                    password: password
                )
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showError = true
                }
            }
            await MainActor.run { isLoading = false }
        }
    }

    private func handleAppleSignIn(result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            isLoading = true
            Task {
                do {
                    try await authManager.signInWithApple(authorization: authorization)
                } catch {
                    await MainActor.run {
                        errorMessage = error.localizedDescription
                        showError = true
                    }
                }
                await MainActor.run { isLoading = false }
            }
        case .failure(let error):
            // ASAuthorizationError.canceled (code 1001) means the user dismissed the sheet — no alert needed.
            let nsError = error as NSError
            if nsError.code != ASAuthorizationError.canceled.rawValue {
                errorMessage = error.localizedDescription
                showError = true
            }
        }
    }
}

// MARK: - Google Sign-In Button

private struct GoogleSignInButton: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                // Google "G" logo using SF Symbols fallback until the asset is added.
                Image(systemName: "globe")
                    .font(.system(size: 18, weight: .medium))
                    .foregroundStyle(.blue)
                Text("Sign in with Google")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(.primary)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 50)
            .background(Color(.secondarySystemBackground))
            .cornerRadius(10)
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color(.separator), lineWidth: 1)
            )
        }
    }
}

#Preview {
    SignInView()
        .environment(AppState())
}
