import SwiftUI

struct TimeEntryListView: View {
    @Environment(AppState.self) private var appState

    @State private var entries: [TimeEntryResponse] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    @State private var selectedStatus: StatusFilter = .all
    @State private var searchText = ""

    @State private var showAddEntry = false
    @State private var entryToEdit: TimeEntryResponse?
    @State private var showBillTime = false

    @State private var timerRefreshID = UUID()

    // MARK: - Status Filter

    enum StatusFilter: String, CaseIterable, Identifiable {
        case all = "All"
        case unbilled = "Unbilled"
        case invoiced = "Invoiced"
        case paid = "Paid"

        var id: String { rawValue }
        var queryValue: String? {
            self == .all ? nil : rawValue.lowercased()
        }
    }

    // MARK: - Computed

    private var unbilledEntries: [TimeEntryResponse] {
        entries.filter { $0.status == "unbilled" }
    }

    private var totalUnbilledSeconds: Int {
        unbilledEntries.reduce(0) { $0 + $1.durationSeconds }
    }

    private var totalUnbilledAmount: Double {
        unbilledEntries.compactMap { Double($0.totalAmount) }.reduce(0, +)
    }

    // MARK: - Body

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Timer card pinned above list
                TimerCardView(onTimerStopped: {
                    Task { await loadEntries() }
                })
                .padding(.top, 8)
                .id(timerRefreshID)

                // Status filter
                Picker("Status", selection: $selectedStatus) {
                    ForEach(StatusFilter.allCases) { filter in
                        Text(filter.rawValue).tag(filter)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal, 16)
                .padding(.top, 12)
                .padding(.bottom, 4)

                if isLoading && entries.isEmpty {
                    Spacer()
                    ProgressView()
                    Spacer()
                } else if let error = errorMessage {
                    Spacer()
                    ContentUnavailableView(
                        "Could Not Load Entries",
                        systemImage: "exclamationmark.triangle",
                        description: Text(error)
                    )
                    Spacer()
                } else if entries.isEmpty {
                    Spacer()
                    ContentUnavailableView(
                        "No Time Entries",
                        systemImage: "clock",
                        description: Text("Start a timer or add a manual entry.")
                    )
                    Spacer()
                } else {
                    List {
                        ForEach(entries) { entry in
                            NavigationLink(value: entry) {
                                TimeEntryRow(entry: entry)
                            }
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                Button(role: .destructive) {
                                    Task { await deleteEntry(entry) }
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }

                        // Unbilled summary footer
                        if totalUnbilledSeconds > 0 {
                            Section {
                                HStack {
                                    Label("Unbilled", systemImage: "clock.badge.exclamationmark")
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    VStack(alignment: .trailing, spacing: 1) {
                                        Text(formattedDuration(seconds: totalUnbilledSeconds))
                                            .font(.subheadline.weight(.semibold))
                                        Text(String(format: "$%.2f", totalUnbilledAmount))
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                    }
                    .listStyle(.insetGrouped)
                    .navigationDestination(for: TimeEntryResponse.self) { entry in
                        TimeEntryFormView(entry: entry, onSave: {
                            Task { await loadEntries() }
                        })
                    }
                }
            }
            .navigationTitle("Time Tracking")
            .searchable(text: $searchText, prompt: "Search entries")
            .refreshable {
                await loadEntries()
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if !unbilledEntries.isEmpty {
                        Button {
                            showBillTime = true
                        } label: {
                            Label("Bill Time", systemImage: "dollarsign.circle")
                        }
                        .accessibilityLabel("Bill unbilled time")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showAddEntry = true
                    } label: {
                        Image(systemName: "plus")
                    }
                    .accessibilityLabel("Add time entry")
                }
            }
            .sheet(isPresented: $showAddEntry, onDismiss: {
                Task { await loadEntries() }
            }) {
                NavigationStack {
                    TimeEntryFormView(entry: nil, onSave: {
                        showAddEntry = false
                        Task { await loadEntries() }
                    })
                }
            }
            .sheet(isPresented: $showBillTime, onDismiss: {
                Task { await loadEntries() }
            }) {
                NavigationStack {
                    BillTimeView(onInvoiceCreated: {
                        showBillTime = false
                        Task { await loadEntries() }
                    })
                }
            }
            .onChange(of: selectedStatus) { _, _ in
                Task { await loadEntries() }
            }
            .onChange(of: searchText) { _, _ in
                Task { await loadEntries() }
            }
        }
        .task {
            await loadEntries()
        }
    }

    // MARK: - API

    private func loadEntries() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        var queryItems: [URLQueryItem] = []
        if let status = selectedStatus.queryValue {
            queryItems.append(URLQueryItem(name: "status", value: status))
        }
        if !searchText.isEmpty {
            queryItems.append(URLQueryItem(name: "search", value: searchText))
        }

        do {
            let loaded: [TimeEntryResponse] = try await appState.api.get(
                "time/entries/",
                queryItems: queryItems.isEmpty ? nil : queryItems
            )
            await MainActor.run { entries = loaded }
        } catch {
            await MainActor.run { errorMessage = error.localizedDescription }
        }
    }

    private func deleteEntry(_ entry: TimeEntryResponse) async {
        do {
            try await appState.api.delete("time/entries/\(entry.id)/")
            await MainActor.run {
                entries.removeAll { $0.id == entry.id }
            }
        } catch {
            await MainActor.run { errorMessage = "Could not delete entry." }
        }
    }

    // MARK: - Formatting

    private func formattedDuration(seconds: Int) -> String {
        let h = seconds / 3600
        let m = (seconds % 3600) / 60
        return String(format: "%dh %02dm", h, m)
    }
}

// MARK: - Row

private struct TimeEntryRow: View {
    let entry: TimeEntryResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .top) {
                Text(entry.description)
                    .font(.subheadline.weight(.medium))
                    .lineLimit(1)
                Spacer()
                StatusBadge(status: entry.status)
            }

            HStack {
                if let client = entry.clientName, !client.isEmpty {
                    Label(client, systemImage: "person")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
                Spacer()
                Text(formattedDuration(seconds: entry.durationSeconds))
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
                Text("·")
                    .foregroundStyle(.secondary)
                Text(String(format: "$%.2f", Double(entry.totalAmount) ?? 0))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.primary)
            }

            Text(entry.date)
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding(.vertical, 2)
    }

    private func formattedDuration(seconds: Int) -> String {
        let h = seconds / 3600
        let m = (seconds % 3600) / 60
        return String(format: "%02d:%02d", h, m)
    }
}

#Preview {
    TimeEntryListView()
        .environment(AppState())
}
