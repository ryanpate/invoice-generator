import SwiftData
import Foundation

// API response struct (detailed profile)
struct UserProfileResponse: Codable {
    let id: Int
    let email: String
    let subscriptionTier: String
    let invoicesCreated: Int
    let invoiceLimit: Int?
    let creditsBalance: Int
    let aiGenerationsUsed: Int
    let aiGenerationsLimit: Int?
    let hasActiveSubscription: Bool
    let paymentSource: String?
}

// Dashboard stats response
struct DashboardStatsResponse: Codable {
    let totalInvoices: Int
    let totalRevenue: String
    let outstandingAmount: String
    let overdueCount: Int
    let recentInvoices: [InvoiceResponse]
}

// SwiftData cache model
@Model
final class CachedUserProfile {
    @Attribute(.unique) var serverId: Int
    var email: String
    var subscriptionTier: String
    var invoicesCreated: Int
    var creditsBalance: Int
    var hasActiveSubscription: Bool

    init(from response: UserProfileResponse) {
        self.serverId = response.id
        self.email = response.email
        self.subscriptionTier = response.subscriptionTier
        self.invoicesCreated = response.invoicesCreated
        self.creditsBalance = response.creditsBalance
        self.hasActiveSubscription = response.hasActiveSubscription
    }
}
