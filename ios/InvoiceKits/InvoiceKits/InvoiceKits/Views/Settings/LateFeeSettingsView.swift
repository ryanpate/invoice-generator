import SwiftUI

// MARK: - Response Model

struct LateFeeSettingsResponse: Codable {
    let lateFeesEnabled: Bool
    let lateFeeType: String
    let lateFeeAmount: String?
    let lateFeeGraceDays: Int?
    let lateFeeMaxAmount: String?
}

// MARK: - View

struct LateFeeSettingsView: View {
    @Environment(AppState.self) private var appState

    // MARK: - Form State

    @State private var lateFeesEnabled = false
    @State private var feeType: FeeType = .percentage
    @State private var feeAmountText = ""
    @State private var graceDaysText = "3"
    @State private var maxFeeText = ""

    @State private var isLoading = false
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var showSuccessBanner = false

    // MARK: - Types

    enum FeeType: String, CaseIterable, Identifiable {
        case percentage = "percentage"
        case flatFee    = "flat_fee"

        var id: String { rawValue }

        var label: String {
            switch self {
            case .percentage: return "Percentage (%)"
            case .flatFee:    return "Flat Fee ($)"
            }
        }
    }

    // MARK: - Computed

    private var feeAmountLabel: String {
        feeType == .percentage ? "Late Fee Percentage" : "Late Fee Amount"
    }

    private var feeAmountPrompt: String {
        feeType == .percentage ? "e.g. 1.5" : "e.g. 25.00"
    }

    private var feeAmountFooter: String {
        feeType == .percentage
            ? "A percentage of the outstanding invoice total."
            : "A fixed dollar amount added to overdue invoices."
    }

    var body: some View {
        Form {
            masterToggleSection
            if lateFeesEnabled {
                feeTypeSection
                feeAmountSection
                gracePeriodSection
                maxCapSection
                previewSection
            }
        }
        .navigationTitle("Late Fees")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Save") {
                    Task { await save() }
                }
                .disabled(isSaving)
                .overlay {
                    if isSaving { ProgressView().scaleEffect(0.7) }
                }
            }
        }
        .task { await load() }
        .overlay(alignment: .top) {
            if showSuccessBanner { successBanner }
        }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            if let msg = errorMessage { Text(msg) }
        }
    }

    // MARK: - Sections

    private var masterToggleSection: some View {
        Section {
            Toggle("Enable Automatic Late Fees", isOn: $lateFeesEnabled)
        } footer: {
            Text("InvoiceKits will automatically add a late fee to overdue invoices after the grace period.")
        }
    }

    private var feeTypeSection: some View {
        Section("Fee Type") {
            Picker("Fee Type", selection: $feeType) {
                ForEach(FeeType.allCases) { type in
                    Text(type.label).tag(type)
                }
            }
            .pickerStyle(.segmented)
        }
    }

    private var feeAmountSection: some View {
        Section {
            HStack {
                Text(feeAmountLabel)
                Spacer()
                TextField(feeAmountPrompt, text: $feeAmountText)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 100)
                Text(feeType == .percentage ? "%" : "$")
                    .foregroundStyle(.secondary)
            }
        } footer: {
            Text(feeAmountFooter)
        }
    }

    private var gracePeriodSection: some View {
        Section {
            HStack {
                Text("Grace Period (days)")
                Spacer()
                TextField("3", text: $graceDaysText)
                    .keyboardType(.numberPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 60)
            }
        } footer: {
            Text("Number of days after the due date before the late fee is applied. Default is 3 days.")
        }
    }

    private var maxCapSection: some View {
        Section {
            HStack {
                Text("Maximum Fee Cap")
                Spacer()
                TextField("No cap", text: $maxFeeText)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 100)
                if !maxFeeText.isEmpty {
                    Text("$")
                        .foregroundStyle(.secondary)
                }
            }
        } header: {
            Text("Fee Cap (Optional)")
        } footer: {
            Text("Sets an upper limit on late fees. Leave blank for no maximum.")
        }
    }

    private var previewSection: some View {
        let amount = Double(feeAmountText) ?? 0
        let maxCap = Double(maxFeeText)
        let graceDays = Int(graceDaysText) ?? 3
        let exampleInvoice = 1000.0
        let fee: Double = feeType == .percentage
            ? exampleInvoice * (amount / 100)
            : amount
        let cappedFee = maxCap.map { min(fee, $0) } ?? fee

        return Section("Preview") {
            LabeledContent("Example Invoice", value: exampleInvoice, format: .currency(code: "USD"))
            LabeledContent("Grace Period", value: "\(graceDays) days")
            if amount > 0 {
                LabeledContent("Late Fee Applied", value: cappedFee, format: .currency(code: "USD"))
                if let cap = maxCap, fee > cap {
                    LabeledContent("(capped from \(fee, format: .currency(code: "USD")))", value: "")
                        .foregroundStyle(.secondary)
                        .font(.caption)
                }
            }
        }
    }

    private var successBanner: some View {
        Text("Late fee settings saved.")
            .font(.subheadline)
            .fontWeight(.medium)
            .foregroundStyle(.white)
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(Color.green, in: Capsule())
            .padding(.top, 8)
            .transition(.move(edge: .top).combined(with: .opacity))
            .onAppear {
                DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
                    withAnimation { showSuccessBanner = false }
                }
            }
    }

    // MARK: - Data

    @MainActor
    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let settings: LateFeeSettingsResponse = try await appState.api.get("settings/late-fees/")
            lateFeesEnabled = settings.lateFeesEnabled
            feeType         = FeeType(rawValue: settings.lateFeeType) ?? .percentage
            feeAmountText   = settings.lateFeeAmount ?? ""
            graceDaysText   = settings.lateFeeGraceDays.map { "\($0)" } ?? "3"
            maxFeeText      = settings.lateFeeMaxAmount ?? ""
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    struct LateFeeSettingsRequest: Encodable {
        let lateFeesEnabled: Bool
        let lateFeeType: String
        let lateFeeAmount: String?
        let lateFeeGraceDays: Int?
        let lateFeeMaxAmount: String?
    }

    @MainActor
    private func save() async {
        isSaving = true
        defer { isSaving = false }
        do {
            let body = LateFeeSettingsRequest(
                lateFeesEnabled: lateFeesEnabled,
                lateFeeType:     feeType.rawValue,
                lateFeeAmount:   feeAmountText.isEmpty ? nil : feeAmountText,
                lateFeeGraceDays: Int(graceDaysText),
                lateFeeMaxAmount: maxFeeText.isEmpty ? nil : maxFeeText
            )
            let _: LateFeeSettingsResponse = try await appState.api.put("settings/late-fees/", body: body)
            withAnimation { showSuccessBanner = true }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        LateFeeSettingsView()
            .environment(AppState())
    }
}
