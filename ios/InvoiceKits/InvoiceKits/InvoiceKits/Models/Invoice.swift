import SwiftData
import Foundation

// API response struct
struct InvoiceResponse: Codable, Identifiable, Hashable {
    let id: Int
    let invoiceNumber: String
    let invoiceName: String?
    let status: String
    let clientName: String
    let clientEmail: String
    let clientPhone: String?
    let clientAddress: String?
    let invoiceDate: String
    let dueDate: String
    let paymentTerms: String
    let currency: String
    let currencySymbol: String
    let subtotal: String
    let taxRate: String
    let taxAmount: String
    let discountAmount: String
    let total: String
    let notes: String?
    let templateStyle: String
    let lineItems: [LineItemResponse]?
    let remindersPaused: Bool
    let lateFeesPaused: Bool
    let lateFeeApplied: String?
    let paidAt: String?
    let sentAt: String?
    let createdAt: String
    let updatedAt: String
}

// SwiftData cache model
@Model
final class CachedInvoice {
    @Attribute(.unique) var serverId: Int
    var invoiceNumber: String
    var invoiceName: String?
    var status: String
    var clientName: String
    var clientEmail: String
    var total: String
    var currency: String
    var dueDate: String
    var createdAt: String
    var updatedAt: String

    init(from response: InvoiceResponse) {
        self.serverId = response.id
        self.invoiceNumber = response.invoiceNumber
        self.invoiceName = response.invoiceName
        self.status = response.status
        self.clientName = response.clientName
        self.clientEmail = response.clientEmail
        self.total = response.total
        self.currency = response.currency
        self.dueDate = response.dueDate
        self.createdAt = response.createdAt
        self.updatedAt = response.updatedAt
    }
}
