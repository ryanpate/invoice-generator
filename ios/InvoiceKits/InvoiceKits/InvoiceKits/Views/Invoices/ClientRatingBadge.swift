import SwiftUI

// MARK: - Response Model

struct ClientStatsResponse: Decodable {
    let rating: String
    let averageDays: Int?
    let totalInvoices: Int
    let message: String
}

// MARK: - View

struct ClientRatingBadge: View {
    let email: String

    @Environment(AppState.self) private var appState

    @State private var stats: ClientStatsResponse?
    @State private var debounceTask: Task<Void, Never>?

    var body: some View {
        Group {
            if let stats, !email.isEmpty {
                HStack(spacing: 8) {
                    // Letter grade chip
                    Text(stats.rating)
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundStyle(.white)
                        .frame(width: 24, height: 24)
                        .background(gradeColor(for: stats.rating), in: Circle())

                    VStack(alignment: .leading, spacing: 1) {
                        Text(stats.message)
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Text("\(stats.totalInvoices) invoice\(stats.totalInvoices == 1 ? "" : "s")")
                            .font(.caption2)
                            .foregroundStyle(Color(.tertiaryLabel))
                    }
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .animation(.easeInOut(duration: 0.2), value: stats?.rating)
        .onChange(of: email) { _, newValue in
            scheduleDebounce(for: newValue)
        }
        .onAppear {
            if !email.isEmpty {
                scheduleDebounce(for: email)
            }
        }
    }

    // MARK: - Private Helpers

    private func gradeColor(for rating: String) -> Color {
        switch rating.uppercased() {
        case "A", "B": return .green
        case "C":       return .yellow
        case "D":       return .orange
        case "F":       return .red
        default:        return .gray
        }
    }

    private func scheduleDebounce(for value: String) {
        debounceTask?.cancel()
        guard !value.trimmingCharacters(in: .whitespaces).isEmpty else {
            stats = nil
            return
        }
        debounceTask = Task {
            try? await Task.sleep(for: .milliseconds(500))
            guard !Task.isCancelled else { return }
            await fetchStats(for: value)
        }
    }

    @MainActor
    private func fetchStats(for emailValue: String) async {
        do {
            let result: ClientStatsResponse = try await appState.api.get(
                "clients/stats/",
                queryItems: [URLQueryItem(name: "email", value: emailValue)]
            )
            withAnimation {
                stats = result
            }
        } catch {
            // Silently clear — badge is supplemental, not critical
            withAnimation {
                stats = nil
            }
        }
    }
}

// MARK: - Preview

#Preview {
    VStack(alignment: .leading, spacing: 16) {
        ClientRatingBadge(email: "good@example.com")
        ClientRatingBadge(email: "slow@example.com")
        ClientRatingBadge(email: "")
    }
    .padding()
    .environment(AppState())
}
