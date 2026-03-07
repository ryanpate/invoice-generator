import Foundation

struct LineItemResponse: Codable, Identifiable, Hashable {
    let id: Int
    let description: String
    let quantity: String
    let unitPrice: String
    let total: String
}

struct LineItemRequest: Encodable {
    let description: String
    let quantity: String
    let unitPrice: String
}
