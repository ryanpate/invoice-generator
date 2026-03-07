import SwiftUI
import StoreKit

struct SubscriptionView: View {
    @Environment(AppState.self) private var appState

    @State private var isLoadingProducts = false
    @State private var purchasingProductID: String?
    @State private var isRestoring = false
    @State private var errorMessage: String?
    @State private var successMessage: String?

    private var currentTier: String {
        appState.auth.currentUser?.subscriptionTier ?? "free"
    }

    private var tierDisplayName: String {
        switch currentTier.lowercased() {
        case "starter":      return "Starter"
        case "professional": return "Professional"
        case "business":     return "Business"
        default:             return "Free"
        }
    }

    var body: some View {
        List {
            currentPlanSection
            subscriptionsSection
            creditPacksSection
            restoreSection
        }
        .navigationTitle("Subscription & Billing")
        .navigationBarTitleDisplayMode(.inline)
        .task { await loadProducts() }
        .alert("Error", isPresented: .constant(errorMessage != nil)) {
            Button("OK") { errorMessage = nil }
        } message: {
            if let msg = errorMessage { Text(msg) }
        }
        .alert("Purchase Successful", isPresented: .constant(successMessage != nil)) {
            Button("OK") { successMessage = nil }
        } message: {
            if let msg = successMessage { Text(msg) }
        }
    }

    // MARK: - Sections

    private var currentPlanSection: some View {
        Section("Current Plan") {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(tierDisplayName)
                        .font(.headline)
                    Text(planDescription(for: currentTier))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: planIcon(for: currentTier))
                    .font(.title2)
                    .foregroundStyle(planColor(for: currentTier))
            }
            .padding(.vertical, 4)
        }
    }

    private var subscriptionsSection: some View {
        Section {
            if isLoadingProducts {
                HStack {
                    Spacer()
                    ProgressView()
                    Spacer()
                }
            } else if appState.store.subscriptions.isEmpty {
                Text("No subscription plans available.")
                    .foregroundStyle(.secondary)
                    .font(.subheadline)
            } else {
                ForEach(appState.store.subscriptions, id: \.id) { product in
                    SubscriptionProductRow(
                        product: product,
                        isCurrentPlan: isCurrentPlan(product),
                        isPurchasing: purchasingProductID == product.id
                    ) {
                        Task { await purchase(product) }
                    }
                }
            }
        } header: {
            Text("Subscription Plans")
        } footer: {
            Text("Subscriptions renew automatically. Cancel anytime in Settings > Apple ID > Subscriptions.")
        }
    }

    private var creditPacksSection: some View {
        Section {
            if appState.store.creditPacks.isEmpty && !isLoadingProducts {
                Text("No credit packs available.")
                    .foregroundStyle(.secondary)
                    .font(.subheadline)
            } else {
                ForEach(appState.store.creditPacks, id: \.id) { product in
                    CreditPackRow(
                        product: product,
                        isPurchasing: purchasingProductID == product.id
                    ) {
                        Task { await purchase(product) }
                    }
                }
            }
        } header: {
            Text("Credit Packs")
        } footer: {
            Text("Credits are one-time purchases and never expire. Use credits to generate invoices without a subscription.")
        }
    }

    private var restoreSection: some View {
        Section {
            Button {
                Task { await restore() }
            } label: {
                HStack {
                    Spacer()
                    if isRestoring {
                        ProgressView()
                            .scaleEffect(0.8)
                    } else {
                        Text("Restore Purchases")
                            .foregroundStyle(Color.accentColor)
                    }
                    Spacer()
                }
            }
            .disabled(isRestoring)
        }
    }

    // MARK: - Helpers

    private func isCurrentPlan(_ product: Product) -> Bool {
        let tier = currentTier.lowercased()
        let productID = product.id.lowercased()
        return productID.contains(tier) && tier != "free"
    }

    private func planDescription(for tier: String) -> String {
        switch tier.lowercased() {
        case "starter":      return "50 invoices/month, all templates"
        case "professional": return "200 invoices/month, recurring invoices"
        case "business":     return "Unlimited invoices, API access, team seats"
        default:             return "5 lifetime credits, 1 template"
        }
    }

    private func planIcon(for tier: String) -> String {
        switch tier.lowercased() {
        case "starter":      return "star.circle.fill"
        case "professional": return "bolt.circle.fill"
        case "business":     return "crown.fill"
        default:             return "person.circle"
        }
    }

    private func planColor(for tier: String) -> Color {
        switch tier.lowercased() {
        case "starter":      return .blue
        case "professional": return .purple
        case "business":     return .orange
        default:             return .gray
        }
    }

    // MARK: - Actions

    @MainActor
    private func loadProducts() async {
        guard appState.store.subscriptions.isEmpty else { return }
        isLoadingProducts = true
        defer { isLoadingProducts = false }
        await appState.store.loadProducts()
    }

    @MainActor
    private func purchase(_ product: Product) async {
        purchasingProductID = product.id
        defer { purchasingProductID = nil }
        do {
            let purchased = try await appState.store.purchase(product)
            if purchased {
                successMessage = "\(product.displayName) activated successfully."
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func restore() async {
        isRestoring = true
        defer { isRestoring = false }
        await appState.store.restorePurchases()
        successMessage = "Purchases restored. Your entitlements have been updated."
    }
}

// MARK: - Subscription Product Row

private struct SubscriptionProductRow: View {
    let product: Product
    let isCurrentPlan: Bool
    let isPurchasing: Bool
    let onPurchase: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(product.displayName)
                        .font(.subheadline)
                        .fontWeight(.medium)
                    if isCurrentPlan {
                        Text("Current")
                            .font(.caption2)
                            .fontWeight(.semibold)
                            .foregroundStyle(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.green, in: Capsule())
                    }
                }
                if !product.description.isEmpty {
                    Text(product.description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                Text(product.displayPrice + "/month")
                    .font(.caption)
                    .foregroundStyle(Color.accentColor)
            }

            Spacer()

            if isPurchasing {
                ProgressView()
                    .scaleEffect(0.85)
            } else if !isCurrentPlan {
                Button("Subscribe", action: onPurchase)
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Credit Pack Row

private struct CreditPackRow: View {
    let product: Product
    let isPurchasing: Bool
    let onPurchase: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "bolt.circle.fill")
                .font(.title3)
                .foregroundStyle(.yellow)

            VStack(alignment: .leading, spacing: 2) {
                Text(product.displayName)
                    .font(.subheadline)
                    .fontWeight(.medium)
                Text(product.description.isEmpty ? "One-time purchase, never expires" : product.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer()

            if isPurchasing {
                ProgressView()
                    .scaleEffect(0.85)
            } else {
                Button(product.displayPrice, action: onPurchase)
                    .buttonStyle(.bordered)
                    .controlSize(.small)
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        SubscriptionView()
            .environment(AppState())
    }
}
