import SwiftUI

struct OnboardingView: View {
    @Environment(AppState.self) private var appState

    @State private var currentPage = 0
    @State private var notificationsGranted: Bool?
    @State private var faceIDGranted: Bool?

    let onComplete: () -> Void

    private var biometricName: String {
        appState.biometric.biometricName
    }

    private var biometricIcon: String {
        switch biometricName {
        case "Face ID":  return "faceid"
        case "Touch ID": return "touchid"
        default:         return "lock.shield"
        }
    }

    var body: some View {
        ZStack {
            Color(.systemBackground).ignoresSafeArea()

            VStack(spacing: 0) {
                // Page content
                TabView(selection: $currentPage) {
                    notificationsPage.tag(0)
                    biometricPage.tag(1)
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
                .animation(.easeInOut(duration: 0.3), value: currentPage)

                // Page indicator
                HStack(spacing: 8) {
                    ForEach(0..<2) { index in
                        Circle()
                            .fill(index == currentPage ? Color.accentColor : Color(.systemGray4))
                            .frame(width: 8, height: 8)
                    }
                }
                .padding(.bottom, 32)
            }
        }
    }

    // MARK: - Notifications Page

    private var notificationsPage: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "bell.badge.fill")
                .font(.system(size: 72, weight: .light))
                .foregroundStyle(
                    LinearGradient(
                        colors: [.blue, .cyan],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .symbolEffect(.bounce, value: currentPage == 0)

            VStack(spacing: 12) {
                Text("Stay in the Loop")
                    .font(.title)
                    .fontWeight(.bold)

                Text("Get notified when clients view or pay your invoices, and when payments are overdue.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }

            Spacer()

            VStack(spacing: 12) {
                Button {
                    Task {
                        let mgr = NotificationManager(api: appState.api)
                        await mgr.requestPermission()
                        notificationsGranted = mgr.isPermissionGranted
                        currentPage = 1
                    }
                } label: {
                    Text("Enable Notifications")
                        .font(.headline)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color.accentColor, in: RoundedRectangle(cornerRadius: 14))
                }

                Button {
                    currentPage = 1
                } label: {
                    Text("Not Now")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 32)
            .padding(.bottom, 16)
        }
    }

    // MARK: - Biometric Page

    private var biometricPage: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: biometricIcon)
                .font(.system(size: 72, weight: .light))
                .foregroundStyle(
                    LinearGradient(
                        colors: [.green, .mint],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .symbolEffect(.bounce, value: currentPage == 1)

            VStack(spacing: 12) {
                Text("Secure Your Invoices")
                    .font(.title)
                    .fontWeight(.bold)

                Text("Use \(biometricName) to keep your financial data private. You can change this anytime in Settings.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }

            Spacer()

            VStack(spacing: 12) {
                Button {
                    Task {
                        let success = await appState.biometric.authenticate()
                        if success {
                            appState.isFaceIDEnabled = true
                            appState.isUnlocked = true
                        }
                        finishOnboarding()
                    }
                } label: {
                    Text("Enable \(biometricName)")
                        .font(.headline)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color.green, in: RoundedRectangle(cornerRadius: 14))
                }

                Button {
                    finishOnboarding()
                } label: {
                    Text("Skip")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 32)
            .padding(.bottom, 16)
        }
    }

    private func finishOnboarding() {
        UserDefaults.standard.set(true, forKey: "hasCompletedOnboarding")
        onComplete()
    }
}
