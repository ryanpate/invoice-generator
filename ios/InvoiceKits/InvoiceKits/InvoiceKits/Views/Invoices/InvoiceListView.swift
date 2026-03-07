import SwiftUI

struct InvoiceListView: View {
    @Environment(AppState.self) private var appState

    @State private var invoices: [InvoiceResponse] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var searchText = ""
    @State private var selectedStatus: StatusFilter = .all
    @State private var selectedInvoiceId: Int?
    @State private var showCreateForm = false
    @State private var deleteTarget: InvoiceResponse?
    @State private var showDeleteConfirm = false

    // MARK: - Status filter

    enum StatusFilter: String, CaseIterable, Identifiable {
        case all      = "All"
        case draft    = "Draft"
        case sent     = "Sent"
        case paid     = "Paid"
        case overdue  = "Overdue"

        var id: String { rawValue }

        var queryValue: String? {
            self == .all ? nil : rawValue.lowercased()
        }
    }

    // MARK: - Computed

    private var filteredInvoices: [InvoiceResponse] {
        invoices.filter { invoice in
            let matchesSearch = searchText.isEmpty ||
                invoice.clientName.localizedCaseInsensitiveContains(searchText) ||
                invoice.invoiceNumber.localizedCaseInsensitiveContains(searchText) ||
                (invoice.invoiceName?.localizedCaseInsensitiveContains(searchText) == true)
            return matchesSearch
        }
    }

    // MARK: - Body

    var body: some View {
        Group {
            if UIDevice.current.userInterfaceIdiom == .pad {
                ipadLayout
            } else {
                iphoneLayout
            }
        }
        .sheet(isPresented: $showCreateForm) {
            // Placeholder until InvoiceFormView is implemented
            NavigationStack {
                Text("New Invoice")
                    .navigationTitle("New Invoice")
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Cancel") { showCreateForm = false }
                        }
                    }
            }
        }
        .alert("Delete Invoice", isPresented: $showDeleteConfirm, presenting: deleteTarget) { invoice in
            Button("Delete", role: .destructive) {
                Task { await deleteInvoice(invoice) }
            }
            Button("Cancel", role: .cancel) {}
        } message: { invoice in
            Text("Delete invoice \(invoice.invoiceNumber) for \(invoice.clientName)? This cannot be undone.")
        }
    }

    // MARK: - Layouts

    private var iphoneLayout: some View {
        NavigationStack {
            content
                .navigationTitle("Invoices")
                .toolbar { toolbarContent }
                .searchable(text: $searchText, prompt: "Search invoices")
        }
    }

    private var ipadLayout: some View {
        NavigationSplitView {
            content
                .navigationTitle("Invoices")
                .toolbar { toolbarContent }
                .searchable(text: $searchText, prompt: "Search invoices")
        } detail: {
            if let invoiceId = selectedInvoiceId {
                InvoiceDetailView(invoiceId: invoiceId)
            } else {
                ContentUnavailableView(
                    "Select an Invoice",
                    systemImage: "doc.text",
                    description: Text("Choose an invoice from the list to view its details.")
                )
            }
        }
    }

    // MARK: - Content

    private var content: some View {
        Group {
            if isLoading && invoices.isEmpty {
                ProgressView("Loading invoices...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if filteredInvoices.isEmpty {
                emptyState
            } else {
                invoiceList
            }
        }
        .task { await loadInvoices() }
    }

    private var invoiceList: some View {
        List {
            ForEach(filteredInvoices) { invoice in
                NavigationLink(value: invoice.id) {
                    InvoiceRow(invoice: invoice)
                }
                .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                    Button(role: .destructive) {
                        deleteTarget = invoice
                        showDeleteConfirm = true
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                }
                .swipeActions(edge: .leading, allowsFullSwipe: false) {
                    if invoice.status.lowercased() != "paid" {
                        Button {
                            Task { await markPaid(invoice) }
                        } label: {
                            Label("Mark Paid", systemImage: "checkmark.circle")
                        }
                        .tint(.green)
                    }
                }
            }
        }
        .listStyle(.plain)
        .refreshable {
            await loadInvoices()
        }
        .navigationDestination(for: Int.self) { invoiceId in
            InvoiceDetailView(invoiceId: invoiceId)
        }
        .overlay(alignment: .bottomTrailing) {
            createButton
        }
    }

    private var emptyState: some View {
        ContentUnavailableView {
            Label(
                searchText.isEmpty ? "No Invoices" : "No Results",
                systemImage: searchText.isEmpty ? "doc.text" : "magnifyingglass"
            )
        } description: {
            if searchText.isEmpty {
                Text("Create your first invoice to get started.")
            } else {
                Text("No invoices matching \"\(searchText)\".")
            }
        } actions: {
            if searchText.isEmpty {
                Button("Create Invoice") { showCreateForm = true }
                    .buttonStyle(.borderedProminent)
            }
        }
    }

    private var createButton: some View {
        Button {
            showCreateForm = true
        } label: {
            Image(systemName: "plus")
                .font(.title2)
                .fontWeight(.semibold)
                .foregroundStyle(.white)
                .frame(width: 56, height: 56)
                .background(Color.accentColor, in: Circle())
                .shadow(color: .accentColor.opacity(0.4), radius: 8, x: 0, y: 4)
        }
        .padding(.trailing, 20)
        .padding(.bottom, 20)
    }

    // MARK: - Toolbar

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .primaryAction) {
            Menu {
                Picker("Filter by Status", selection: $selectedStatus) {
                    ForEach(StatusFilter.allCases) { filter in
                        Text(filter.rawValue).tag(filter)
                    }
                }
                .pickerStyle(.inline)
            } label: {
                Label("Filter", systemImage: selectedStatus == .all ? "line.3.horizontal.decrease.circle" : "line.3.horizontal.decrease.circle.fill")
            }
            .onChange(of: selectedStatus) {
                Task { await loadInvoices() }
            }
        }

        ToolbarItem(placement: .primaryAction) {
            Button {
                showCreateForm = true
            } label: {
                Image(systemName: "plus")
            }
        }
    }

    // MARK: - Data Loading

    @MainActor
    private func loadInvoices() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            var queryItems: [URLQueryItem] = []
            if let statusValue = selectedStatus.queryValue {
                queryItems.append(URLQueryItem(name: "status", value: statusValue))
            }
            if !searchText.isEmpty {
                queryItems.append(URLQueryItem(name: "search", value: searchText))
            }
            invoices = try await appState.api.get(
                "invoices/",
                queryItems: queryItems.isEmpty ? nil : queryItems
            )
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func deleteInvoice(_ invoice: InvoiceResponse) async {
        do {
            try await appState.api.delete("invoices/\(invoice.id)/")
            invoices.removeAll { $0.id == invoice.id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func markPaid(_ invoice: InvoiceResponse) async {
        do {
            let updated: InvoiceResponse = try await appState.api.post("invoices/\(invoice.id)/mark-paid/")
            if let index = invoices.firstIndex(where: { $0.id == invoice.id }) {
                invoices[index] = updated
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Invoice Row

private struct InvoiceRow: View {
    let invoice: InvoiceResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(invoice.clientName)
                        .font(.headline)
                        .lineLimit(1)
                    if let name = invoice.invoiceName, !name.isEmpty {
                        Text(name)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    } else {
                        Text(invoice.invoiceNumber)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                Text("\(invoice.currencySymbol)\(invoice.total)")
                    .font(.headline)
                    .foregroundStyle(.primary)
            }

            HStack {
                Text(invoice.invoiceNumber)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                Spacer()
                Label("Due \(formattedDate(invoice.dueDate))", systemImage: "calendar")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                StatusBadge(status: invoice.status)
            }
        }
        .padding(.vertical, 4)
    }

    private func formattedDate(_ dateString: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        guard let date = formatter.date(from: dateString) else { return dateString }
        return date.formatted(date: .abbreviated, time: .omitted)
    }
}

// MARK: - Preview

#Preview {
    InvoiceListView()
        .environment(AppState())
}
