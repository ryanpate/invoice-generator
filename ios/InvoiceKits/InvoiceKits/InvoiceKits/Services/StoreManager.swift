import StoreKit

@Observable
final class StoreManager {
    private(set) var subscriptions: [Product] = []
    private(set) var creditPacks: [Product] = []
    private(set) var currentSubscription: Product.SubscriptionInfo.Status?
    private(set) var purchasedProductIDs: Set<String> = []

    private let api: APIClient
    private var updateListenerTask: Task<Void, Never>?

    init(api: APIClient) {
        self.api = api
        updateListenerTask = listenForTransactions()
    }

    func loadProducts() async {
        do {
            let products = try await Product.products(for:
                Constants.StoreKit.subscriptionIDs + Constants.StoreKit.creditIDs
            )
            subscriptions = products.filter { Constants.StoreKit.subscriptionIDs.contains($0.id) }
                .sorted { $0.price < $1.price }
            creditPacks = products.filter { Constants.StoreKit.creditIDs.contains($0.id) }
                .sorted { $0.price < $1.price }
        } catch {
            print("Failed to load products: \(error)")
        }
    }

    func purchase(_ product: Product) async throws -> Bool {
        let result = try await product.purchase()

        switch result {
        case .success(let verification):
            let transaction = try checkVerified(verification)
            await verifyWithBackend(transaction)
            await transaction.finish()
            return true
        case .userCancelled:
            return false
        case .pending:
            return false
        @unknown default:
            return false
        }
    }

    func restorePurchases() async {
        try? await AppStore.sync()
        await refreshEntitlements()
    }

    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified:
            throw StoreError.verificationFailed
        case .verified(let safe):
            return safe
        }
    }

    private func verifyWithBackend(_ transaction: Transaction) async {
        struct Body: Encodable { let transactionJws: String }
        let jws = String(data: transaction.jsonRepresentation, encoding: .utf8) ?? ""
        let _: EmptyResponse? = try? await api.post("billing/verify-receipt/", body: Body(transactionJws: jws))
    }

    private func refreshEntitlements() async {
        for await result in Transaction.currentEntitlements {
            if let transaction = try? checkVerified(result) {
                purchasedProductIDs.insert(transaction.productID)
            }
        }
    }

    private func listenForTransactions() -> Task<Void, Never> {
        Task.detached {
            for await result in Transaction.updates {
                if let transaction = try? self.checkVerified(result) {
                    await self.verifyWithBackend(transaction)
                    await transaction.finish()
                }
            }
        }
    }

    enum StoreError: Error {
        case verificationFailed
    }
}
