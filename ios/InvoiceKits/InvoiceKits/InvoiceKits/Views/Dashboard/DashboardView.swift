import SwiftUI

struct DashboardView: View {
    @Environment(AppState.self) private var appState

    @State private var stats: DashboardStatsResponse?
    @State private var userProfile: UserProfileResponse?
    @State private var isLoading = false
    @State private var errorMessage: String?

    // MARK: - Grid layout

    private let twoColumnGrid = [
        GridItem(.flexible(), spacing: 16),
        GridItem(.flexible(), spacing: 16)
    ]

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && stats == nil {
                    ProgressView("Loading dashboard...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    scrollContent
                }
            }
            .navigationTitle("Dashboard")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        Task { await load() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(isLoading)
                }
            }
            .task { await load() }
        }
    }

    // MARK: - Scroll Content

    private var scrollContent: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Stats Grid
                if let stats {
                    statsGrid(stats)
                }

                // Timer Widget
                TimerCardView()

                // AI Generations Card
                if let profile = userProfile {
                    aiGenerationsCard(profile)
                }

                // Recent Invoices
                if let stats, !stats.recentInvoices.isEmpty {
                    recentInvoicesSection(stats.recentInvoices)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        .refreshable { await load() }
    }

    // MARK: - Stats Grid

    private func statsGrid(_ stats: DashboardStatsResponse) -> some View {
        LazyVGrid(columns: twoColumnGrid, spacing: 16) {
            StatCard(
                title: "Total Invoices",
                value: "\(stats.totalInvoices)",
                systemImage: "doc.text.fill",
                color: .blue
            )
            StatCard(
                title: "Total Revenue",
                value: "$\(stats.totalRevenue)",
                systemImage: "dollarsign.circle.fill",
                color: .green
            )
            StatCard(
                title: "Outstanding",
                value: "$\(stats.outstandingAmount)",
                systemImage: "clock.fill",
                color: .orange
            )
            StatCard(
                title: "Overdue",
                value: "\(stats.overdueCount)",
                systemImage: "exclamationmark.circle.fill",
                color: stats.overdueCount > 0 ? .red : .gray
            )
        }
    }

    // MARK: - AI Generations Card

    private func aiGenerationsCard(_ profile: UserProfileResponse) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("AI Generations", systemImage: "sparkles")
                    .font(.headline)
                    .foregroundStyle(.white)
                Spacer()
                Text("BETA")
                    .font(.caption2)
                    .fontWeight(.bold)
                    .foregroundStyle(.white.opacity(0.8))
                    .padding(.horizontal, 7)
                    .padding(.vertical, 3)
                    .background(.white.opacity(0.2), in: Capsule())
            }

            if let limit = profile.aiGenerationsLimit {
                let remaining = max(0, limit - profile.aiGenerationsUsed)
                let fraction = limit > 0 ? Double(profile.aiGenerationsUsed) / Double(limit) : 0

                Text("\(remaining) of \(limit) remaining this month")
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.9))

                ProgressView(value: fraction)
                    .tint(.white)
                    .background(.white.opacity(0.3), in: Capsule())
            } else {
                Text("Unlimited")
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.9))
            }
        }
        .padding(16)
        .background(
            LinearGradient(
                colors: [Color.purple, Color.indigo],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 16)
        )
    }

    // MARK: - Recent Invoices

    private func recentInvoicesSection(_ invoices: [InvoiceResponse]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recent Invoices")
                .font(.headline)
                .padding(.horizontal, 4)

            VStack(spacing: 0) {
                ForEach(Array(invoices.prefix(5))) { invoice in
                    NavigationLink {
                        InvoiceDetailView(invoiceId: invoice.id)
                    } label: {
                        RecentInvoiceRow(invoice: invoice)
                    }
                    .buttonStyle(.plain)

                    if invoice.id != invoices.prefix(5).last?.id {
                        Divider()
                            .padding(.horizontal, 4)
                    }
                }
            }
            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 12))
        }
    }

    // MARK: - Data

    @MainActor
    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            async let statsResult: DashboardStatsResponse = appState.api.get("dashboard/stats/")
            async let profileResult: UserProfileResponse = appState.api.get("auth/profile/")
            (stats, userProfile) = try await (statsResult, profileResult)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Stat Card

private struct StatCard: View {
    let title: String
    let value: String
    let systemImage: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Image(systemName: systemImage)
                .font(.title2)
                .foregroundStyle(color)
                .frame(width: 36, height: 36)
                .background(color.opacity(0.12), in: RoundedRectangle(cornerRadius: 8))

            Text(value)
                .font(.title2)
                .fontWeight(.bold)
                .lineLimit(1)
                .minimumScaleFactor(0.7)

            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Recent Invoice Row

private struct RecentInvoiceRow: View {
    let invoice: InvoiceResponse

    private var formattedDate: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        guard let date = formatter.date(from: invoice.dueDate) else { return invoice.dueDate }
        return date.formatted(date: .abbreviated, time: .omitted)
    }

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(invoice.clientName)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .lineLimit(1)
                Text(invoice.invoiceNumber)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text("\(invoice.currencySymbol)\(invoice.total)")
                    .font(.subheadline)
                    .fontWeight(.medium)
                StatusBadge(status: invoice.status)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .contentShape(Rectangle())
    }
}

