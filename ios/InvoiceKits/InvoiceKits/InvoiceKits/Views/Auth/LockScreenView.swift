import SwiftUI

struct LockScreenView: View {
    @Environment(AppState.self) private var appState

    @State private var showAuthError = false
    @State private var authErrorMessage = ""

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient(
                colors: [Color(.systemBackground), Color(.secondarySystemBackground)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            VStack(spacing: 32) {
                Spacer()

                // App icon and name
                VStack(spacing: 16) {
                    Image(systemName: "doc.text.fill")
                        .font(.system(size: 72, weight: .semibold))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [Color.accentColor, Color.accentColor.opacity(0.7)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )

                    Text("InvoiceKits")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("Unlock to continue")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                // Biometric unlock button
                VStack(spacing: 20) {
                    Button {
                        Task { await triggerBiometricAuth() }
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: biometricSystemImageName)
                                .font(.title2)
                            Text("Unlock with \(appState.biometric.biometricName)")
                                .font(.headline)
                        }
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color.accentColor, in: RoundedRectangle(cornerRadius: 14))
                    }
                    .padding(.horizontal, 32)

                    // Sign-out fallback
                    Button {
                        appState.auth.logout()
                    } label: {
                        Text("Sign Out")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.bottom, 48)
            }
        }
        .alert("Authentication Failed", isPresented: $showAuthError) {
            Button("Try Again") {
                Task { await triggerBiometricAuth() }
            }
            Button("Sign Out", role: .destructive) {
                appState.auth.logout()
            }
        } message: {
            Text(authErrorMessage)
        }
        .task {
            await triggerBiometricAuth()
        }
    }

    // MARK: - Private helpers

    private var biometricSystemImageName: String {
        switch appState.biometric.biometricName {
        case "Face ID":  return "faceid"
        case "Touch ID": return "touchid"
        default:         return "lock.open.fill"
        }
    }

    private func triggerBiometricAuth() async {
        guard appState.biometric.isBiometricAvailable else {
            authErrorMessage = "Biometric authentication is not available on this device."
            showAuthError = true
            return
        }

        let success = await appState.biometric.authenticate()
        if success {
            appState.isUnlocked = true
        } else {
            authErrorMessage = "Could not verify your identity. Please try again."
            showAuthError = true
        }
    }
}

#Preview {
    LockScreenView()
        .environment(AppState())
}
