import AuthenticationServices
import SwiftUI

struct SignUpView: View {
    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    @State private var email: String = ""
    @State private var password: String = ""
    @State private var confirmPassword: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String?
    @State private var showError: Bool = false

    private var authManager: AuthManager { appState.auth }

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                // MARK: - Header
                VStack(spacing: 8) {
                    Image(systemName: "doc.text.fill")
                        .font(.system(size: 44, weight: .semibold))
                        .foregroundStyle(.blue)
                        .padding(.bottom, 4)

                    Text("Create Account")
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundStyle(.primary)

                    Text("Start invoicing in seconds")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 40)
                .padding(.bottom, 32)

                // MARK: - Social Sign-In
                VStack(spacing: 12) {
                    SignInWithAppleButton(.signUp) { request in
                        request.requestedScopes = [.fullName, .email]
                    } onCompletion: { result in
                        handleAppleSignIn(result: result)
                    }
                    .signInWithAppleButtonStyle(.black)
                    .frame(height: 50)
                    .cornerRadius(10)

                    GoogleSignUpButton {
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

                // MARK: - Registration Fields
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
                        .textContentType(.newPassword)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 14)
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(10)

                    VStack(alignment: .leading, spacing: 6) {
                        SecureField("Confirm Password", text: $confirmPassword)
                            .textContentType(.newPassword)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 14)
                            .background(Color(.secondarySystemBackground))
                            .cornerRadius(10)
                            .overlay(
                                RoundedRectangle(cornerRadius: 10)
                                    .stroke(passwordMismatchBorderColor, lineWidth: 1)
                            )

                        if showPasswordMismatch {
                            Text("Passwords do not match")
                                .font(.caption)
                                .foregroundStyle(.red)
                                .padding(.horizontal, 4)
                        }
                    }
                }
                .padding(.horizontal, 24)

                // MARK: - Create Account Button
                Button(action: register) {
                    Group {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(.circular)
                                .tint(.white)
                        } else {
                            Text("Create Account")
                                .font(.system(size: 16, weight: .semibold))
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .background(createAccountButtonBackground)
                    .foregroundStyle(.white)
                    .cornerRadius(10)
                }
                .disabled(isLoading || !isFormValid)
                .padding(.horizontal, 24)
                .padding(.top, 20)

                // MARK: - Terms Note
                Text("By creating an account, you agree to our Terms of Service and Privacy Policy.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
                    .padding(.top, 16)

                // MARK: - Sign In Link
                Button {
                    dismiss()
                } label: {
                    HStack(spacing: 4) {
                        Text("Already have an account?")
                            .foregroundStyle(.secondary)
                        Text("Sign In")
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
        .navigationBarTitleDisplayMode(.inline)
        .alert("Sign Up Failed", isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "An unexpected error occurred. Please try again.")
        }
    }

    // MARK: - Computed Properties

    private var isFormValid: Bool {
        !email.trimmingCharacters(in: .whitespaces).isEmpty
            && password.count >= 1
            && password == confirmPassword
    }

    private var showPasswordMismatch: Bool {
        !confirmPassword.isEmpty && password != confirmPassword
    }

    private var passwordMismatchBorderColor: Color {
        showPasswordMismatch ? .red : .clear
    }

    private var createAccountButtonBackground: Color {
        isFormValid && !isLoading ? .blue : Color(.systemGray3)
    }

    // MARK: - Actions

    private func register() {
        guard isFormValid else { return }
        isLoading = true
        Task {
            do {
                try await authManager.register(
                    email: email.trimmingCharacters(in: .whitespaces),
                    password: password,
                    passwordConfirm: confirmPassword
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
            let nsError = error as NSError
            if nsError.code != ASAuthorizationError.canceled.rawValue {
                errorMessage = error.localizedDescription
                showError = true
            }
        }
    }
}

// MARK: - Google Sign-Up Button

private struct GoogleSignUpButton: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: "globe")
                    .font(.system(size: 18, weight: .medium))
                    .foregroundStyle(.blue)
                Text("Sign up with Google")
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
    NavigationStack {
        SignUpView()
    }
    .environment(AppState())
}
