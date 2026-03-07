import SwiftData
import Foundation

// API response struct
struct CompanyResponse: Codable {
    let id: Int
    let name: String
    let email: String?
    let phone: String?
    let address: String?
    let city: String?
    let state: String?
    let zipCode: String?
    let country: String?
    let website: String?
    let taxId: String?
    let defaultPaymentTerms: String?
    let defaultNotes: String?
    let logoUrl: String?
    let signatureUrl: String?
}

// SwiftData cache model
@Model
final class CachedCompany {
    @Attribute(.unique) var serverId: Int
    var name: String
    var email: String?
    var phone: String?
    var address: String?
    var city: String?
    var state: String?
    var zipCode: String?
    var country: String?
    var logoUrl: String?

    init(from response: CompanyResponse) {
        self.serverId = response.id
        self.name = response.name
        self.email = response.email
        self.phone = response.phone
        self.address = response.address
        self.city = response.city
        self.state = response.state
        self.zipCode = response.zipCode
        self.country = response.country
        self.logoUrl = response.logoUrl
    }
}
