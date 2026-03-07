import SwiftUI

struct BillTimeView: View {
    var onInvoiceCreated: (() -> Void)?

    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    // MARK: - State

    @State private var unbilledEntries: [TimeEntryResponse] = []
    @State private var selectedIDs: Set<Int> = []
    @State private var groupingMode: GroupingMode = .detailed
    @State private var isLoading = true
    @State private var isCreating = false
    @State private var errorMessage: String?
    @State private var showError = false

    // MARK: - Grouping Mode

    enum GroupingMode: String, CaseIterable, Identifiable {
        case detailed = "Detailed"
        case summary = "Summary"
        var id: String { rawValue }
        var apiValue: String { rawValue.lowercased() }
    }

    // MARK: - Computed

    private var selectedEntries: [TimeEntryResponse] {
        unbilledEntries.filter { selectedIDs.contains($0.id) }
    }

    private var totalSelectedSeconds: Int {
        selectedEntries.reduce(0) { $0 + $1.durationSeconds }
    }

    private var totalSelectedAmount: Double {
        selectedEntries.compactMap { Double($0.totalAmount) }.reduce(0, +)
    }

    private var formattedTotalDuration: String {
        let h = totalSelectedSeconds / 3600
        let m = (totalSelectedSeconds % 3600) / 60
        return String(format: "%dh %02dm", h, m)
    }

    // MARK: - Body

    var body: some View {
        Group {
            if isLoading {
                ProgressView("Loading unbilled entries…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if unbilledEntries.isEmpty {
                ContentUnavailableView(
                    "No Unbilled Entries",
                    systemImage: "clock.badge.checkmark",
                    description: Text("All time entries have already been billed.")
                )
            } else {
                mainContent
            }
        }
        .navigationTitle("Bill Time")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Cancel") { dismiss() }
            }
        }
        .alert("Error", isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "An unexpected error occurred.")
        }
        .task {
            await loadUnbilledEntries()
        }
    }

    // MARK: - Main Content

    private var mainContent: some View {
        VStack(spacing: 0) {
            List {
                // Grouping mode picker
                Section {
                    Picker("Grouping", selection: $groupingMode) {
                        ForEach(GroupingMode.allCases) { mode in
                            Text(mode.rawValue).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                } header: {
                    Text("Invoice Line Items")
                } footer: {
                    Text(groupingMode == .detailed
                         ? "Each entry becomes a separate line item."
                         : "Entries are grouped by description into one line item.")
                }

                // Select / Deselect All
                Section {
                    Button {
                        if selectedIDs.count == unbilledEntries.count {
                            selectedIDs.removeAll()
                        } else {
                            selectedIDs = Set(unbilledEntries.map(\.id))
                        }
                    } label: {
                        HStack {
                            Image(systemName: selectedIDs.count == unbilledEntries.count
                                  ? "checkmark.circle.fill"
                                  : "circle")
                                .foregroundStyle(selectedIDs.count == unbilledEntries.count ? .blue : .secondary)
                            Text(selectedIDs.count == unbilledEntries.count ? "Deselect All" : "Select All")
                                .foregroundStyle(.primary)
                        }
                    }
                }

                // Entry rows
                Section("Entries") {
                    ForEach(unbilledEntries) { entry in
                        BillEntryRow(
                            entry: entry,
                            isSelected: selectedIDs.contains(entry.id)
                        )
                        .contentShape(Rectangle())
                        .onTapGesture {
                            if selectedIDs.contains(entry.id) {
                                selectedIDs.remove(entry.id)
                            } else {
                                selectedIDs.insert(entry.id)
                            }
                        }
                    }
                }
            }
            .listStyle(.insetGrouped)

            // Summary + CTA footer
            summaryFooter
        }
    }

    // MARK: - Summary Footer

    private var summaryFooter: some View {
        VStack(spacing: 12) {
            Divider()

            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("\(selectedIDs.count) entries selected")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text(formattedTotalDuration)
                        .font(.headline)
                }
                Spacer()
                Text(String(format: "$%.2f", totalSelectedAmount))
                    .font(.title3.weight(.bold))
                    .foregroundStyle(.primary)
            }
            .padding(.horizontal, 20)

            Button {
                Task { await createInvoice() }
            } label: {
                Group {
                    if isCreating {
                        ProgressView().progressViewStyle(.circular).tint(.white)
                    } else {
                        Text("Create Invoice")
                            .font(.system(size: 16, weight: .semibold))
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .foregroundStyle(.white)
                .background(createButtonBackground, in: RoundedRectangle(cornerRadius: 12))
            }
            .disabled(isCreating || selectedIDs.isEmpty)
            .padding(.horizontal, 20)
            .padding(.bottom, 8)
        }
        .background(Color(.systemBackground))
    }

    private var createButtonBackground: Color {
        selectedIDs.isEmpty || isCreating ? Color(.systemGray3) : .blue
    }

    // MARK: - API

    private func loadUnbilledEntries() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let loaded: [TimeEntryResponse] = try await appState.api.get(
                "time/entries/",
                queryItems: [URLQueryItem(name: "status", value: "unbilled")]
            )
            await MainActor.run {
                unbilledEntries = loaded
                selectedIDs = Set(loaded.map(\.id))
            }
        } catch {
            await MainActor.run { errorMessage = error.localizedDescription }
        }
    }

    private func createInvoice() async {
        guard !selectedIDs.isEmpty else { return }
        isCreating = true
        defer { isCreating = false }

        struct BillBody: Encodable {
            let entryIds: [Int]
            let groupingMode: String
        }

        let body = BillBody(
            entryIds: Array(selectedIDs),
            groupingMode: groupingMode.apiValue
        )

        do {
            let _: InvoiceResponse = try await appState.api.post("time/bill/", body: body)
            await MainActor.run {
                onInvoiceCreated?()
                dismiss()
            }
        } catch {
            await MainActor.run {
                errorMessage = error.localizedDescription
                showError = true
            }
        }
    }
}

// MARK: - Bill Entry Row

private struct BillEntryRow: View {
    let entry: TimeEntryResponse
    let isSelected: Bool

    private var formattedDuration: String {
        let h = entry.durationSeconds / 3600
        let m = (entry.durationSeconds % 3600) / 60
        return String(format: "%02d:%02d", h, m)
    }

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                .font(.title3)
                .foregroundStyle(isSelected ? .blue : Color(.systemGray3))
                .animation(.easeInOut(duration: 0.15), value: isSelected)

            VStack(alignment: .leading, spacing: 3) {
                Text(entry.description)
                    .font(.subheadline.weight(.medium))
                    .lineLimit(1)
                if let client = entry.clientName, !client.isEmpty {
                    Text(client)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Text(entry.date)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text(formattedDuration)
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
                Text(String(format: "$%.2f", Double(entry.totalAmount) ?? 0))
                    .font(.subheadline.weight(.semibold))
            }
        }
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }
}

#Preview {
    NavigationStack {
        BillTimeView()
            .environment(AppState())
    }
}
