import SwiftUI

struct AppSettingsView: View {
    @Environment(AppState.self) private var appState

    // MARK: - Persisted Preferences

    @AppStorage("appearanceMode") private var appearanceMode: AppearanceMode = .system

    // MARK: - Computed

    private var isBiometricAvailable: Bool {
        appState.biometric.isBiometricAvailable
    }

    private var biometricName: String {
        appState.biometric.biometricName
    }

    private var isFaceIDEnabled: Bool {
        get { appState.isFaceIDEnabled }
    }

    // MARK: - App Version

    private var appVersion: String {
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—"
        let build   = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "—"
        return "\(version) (\(build))"
    }

    // MARK: - Types

    enum AppearanceMode: String, CaseIterable, Identifiable {
        case system = "system"
        case light  = "light"
        case dark   = "dark"

        var id: String { rawValue }

        var label: String {
            switch self {
            case .system: return "System"
            case .light:  return "Light"
            case .dark:   return "Dark"
            }
        }

        var colorScheme: ColorScheme? {
            switch self {
            case .system: return nil
            case .light:  return .light
            case .dark:   return .dark
            }
        }
    }

    var body: some View {
        List {
            // MARK: Biometrics Section
            if isBiometricAvailable {
                Section {
                    Toggle(isOn: Binding(
                        get: { appState.isFaceIDEnabled },
                        set: { appState.isFaceIDEnabled = $0 }
                    )) {
                        Label(biometricName, systemImage: biometricSystemImage)
                    }
                } header: {
                    Text("Security")
                } footer: {
                    Text("When enabled, \(biometricName) is required each time you open InvoiceKits.")
                }
            }

            // MARK: Appearance Section
            Section("Appearance") {
                Picker("Theme", selection: $appearanceMode) {
                    ForEach(AppearanceMode.allCases) { mode in
                        Label(mode.label, systemImage: appearanceIcon(for: mode))
                            .tag(mode)
                    }
                }
                .pickerStyle(.segmented)
            }

            // MARK: About Section
            Section("About") {
                LabeledContent("Version", value: appVersion)

                Link(destination: URL(string: "https://www.invoicekits.com/privacy/")!) {
                    Label("Privacy Policy", systemImage: "lock.shield")
                }

                Link(destination: URL(string: "https://www.invoicekits.com/terms/")!) {
                    Label("Terms of Service", systemImage: "doc.text")
                }

                Link(destination: URL(string: "https://www.invoicekits.com/help/")!) {
                    Label("Help Center", systemImage: "questionmark.circle")
                }

                Link(destination: URL(string: "https://www.invoicekits.com/contact/")!) {
                    Label("Contact Support", systemImage: "envelope")
                }
            }
        }
        .navigationTitle("App Settings")
        .navigationBarTitleDisplayMode(.inline)
        .preferredColorScheme(appearanceMode.colorScheme)
    }

    // MARK: - Helpers

    private var biometricSystemImage: String {
        switch appState.biometric.biometricName {
        case "Face ID":   return "faceid"
        case "Touch ID":  return "touchid"
        default:          return "lock.shield"
        }
    }

    private func appearanceIcon(for mode: AppearanceMode) -> String {
        switch mode {
        case .system: return "circle.lefthalf.filled"
        case .light:  return "sun.max"
        case .dark:   return "moon"
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        AppSettingsView()
            .environment(AppState())
    }
}
