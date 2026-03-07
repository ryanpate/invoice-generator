import SwiftData
import Foundation

// API response struct
struct TimeEntryResponse: Codable, Identifiable, Hashable {
    let id: Int
    let description: String
    let clientName: String?
    let clientEmail: String?
    let durationSeconds: Int
    let hourlyRate: String
    let totalAmount: String
    let status: String
    let invoiceId: Int?
    let date: String
    let createdAt: String
    let updatedAt: String
}

struct ActiveTimerResponse: Codable {
    let id: Int
    let description: String
    let clientName: String?
    let clientEmail: String?
    let startedAt: String
    let hourlyRate: String
}

// SwiftData cache model
@Model
final class CachedTimeEntry {
    @Attribute(.unique) var serverId: Int
    var entryDescription: String
    var clientName: String?
    var durationSeconds: Int
    var hourlyRate: String
    var totalAmount: String
    var status: String
    var date: String
    var createdAt: String

    init(from response: TimeEntryResponse) {
        self.serverId = response.id
        self.entryDescription = response.description
        self.clientName = response.clientName
        self.durationSeconds = response.durationSeconds
        self.hourlyRate = response.hourlyRate
        self.totalAmount = response.totalAmount
        self.status = response.status
        self.date = response.date
        self.createdAt = response.createdAt
    }
}
