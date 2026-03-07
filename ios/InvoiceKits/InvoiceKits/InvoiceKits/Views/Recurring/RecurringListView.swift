import SwiftUI

// MARK: - Recurring Invoice Model

struct RecurringInvoiceResponse: Codable, Identifiable {
    let id: Int
    let clientName: String
    let clientEmail: String
    let frequency: String
    let status: String
    let nextGenerationDate: String?
    let startDate: String
    let endDate: String?
    let currency: String
    let currencySymbol: String
    let total: String
    let invoiceName: String?
    let lineItems: [LineItemResponse]?
    let clientPhone: String?
    let clientAddress: String?
    let taxRate: String?
    let discountAmount: String?
    let notes: String?
    let templateStyle: String?
    let defaultPaymentTerms: String?
    let createdAt: String
    let updatedAt: String
}

// MARK: - View

struct RecurringListView: View {
    @Environment(AppState.self) private var appState

    @State private var items: [RecurringInvoiceResponse] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showCreateForm = false
    @State private var deleteTarget: RecurringInvoiceResponse?
    @State private var showDeleteConfirm = false

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Recurring")
                .toolbar {
                    ToolbarItem(placement: .primaryAction) {
                        Button {
                            showCreateForm = true
                        } label: {
                            Image(systemName: "plus")
                        }
                    }
                }
                .task { await load() }
                .sheet(isPresented: $showCreateForm) {
                    RecurringFormView(existing: nil) {
                        Task { await load() }
                    }
                }
                .alert("Delete Recurring Invoice", isPresented: $showDeleteConfirm, presenting: deleteTarget) { item in
                    Button("Delete", role: .destructive) {
                        Task { await delete(item) }
                    }
                    Button("Cancel", role: .cancel) {}
                } message: { item in
                    Text("Delete the recurring invoice for \(item.clientName)? This cannot be undone.")
                }
        }
    }

    // MARK: - Content

    @ViewBuilder
    private var content: some View {
        if isLoading && items.isEmpty {
            ProgressView("Loading...")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if items.isEmpty {
            emptyState
        } else {
            list
        }
    }

    private var list: some View {
        List {
            ForEach(items) { item in
                NavigationLink {
                    RecurringDetailView(recurringId: item.id)
                } label: {
                    RecurringRow(item: item)
                }
                .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                    Button(role: .destructive) {
                        deleteTarget = item
                        showDeleteConfirm = true
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                }
                .swipeActions(edge: .leading, allowsFullSwipe: false) {
                    Button {
                        Task { await toggleStatus(item) }
                    } label: {
                        if item.status.lowercased() == "paused" {
                            Label("Resume", systemImage: "play.circle")
                        } else {
                            Label("Pause", systemImage: "pause.circle")
                        }
                    }
                    .tint(item.status.lowercased() == "paused" ? .green : .orange)
                }
            }
        }
        .listStyle(.plain)
        .refreshable { await load() }
    }

    private var emptyState: some View {
        ContentUnavailableView {
            Label("No Recurring Invoices", systemImage: "repeat.circle")
        } description: {
            Text("Set up automatic invoices to bill clients on a schedule.")
        } actions: {
            Button("Create Recurring Invoice") { showCreateForm = true }
                .buttonStyle(.borderedProminent)
        }
    }

    // MARK: - Data

    @MainActor
    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            items = try await appState.api.get("recurring/")
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func toggleStatus(_ item: RecurringInvoiceResponse) async {
        do {
            let updated: RecurringInvoiceResponse = try await appState.api.post("recurring/\(item.id)/toggle-status/")
            if let index = items.firstIndex(where: { $0.id == item.id }) {
                items[index] = updated
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func delete(_ item: RecurringInvoiceResponse) async {
        do {
            try await appState.api.delete("recurring/\(item.id)/")
            items.removeAll { $0.id == item.id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Row

private struct RecurringRow: View {
    let item: RecurringInvoiceResponse

    private var frequencyLabel: String {
        switch item.frequency.lowercased() {
        case "weekly":     return "Weekly"
        case "bi_weekly":  return "Every 2 Weeks"
        case "monthly":    return "Monthly"
        case "quarterly":  return "Quarterly"
        case "yearly":     return "Yearly"
        default:           return item.frequency.capitalized
        }
    }

    private var statusColor: Color {
        item.status.lowercased() == "active" ? .green : .orange
    }

    private var nextDateText: String {
        guard let raw = item.nextGenerationDate else { return "—" }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        guard let date = formatter.date(from: raw) else { return raw }
        return date.formatted(date: .abbreviated, time: .omitted)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(item.clientName)
                        .font(.headline)
                        .lineLimit(1)
                    if let name = item.invoiceName, !name.isEmpty {
                        Text(name)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    } else {
                        Text(frequencyLabel)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                Text("\(item.currencySymbol)\(item.total)")
                    .font(.headline)
            }

            HStack {
                Label(frequencyLabel, systemImage: "repeat")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Label("Next: \(nextDateText)", systemImage: "calendar")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(item.status.uppercased())
                    .font(.caption2)
                    .fontWeight(.semibold)
                    .foregroundStyle(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(statusColor, in: Capsule())
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Preview

#Preview {
    RecurringListView()
        .environment(AppState())
}
