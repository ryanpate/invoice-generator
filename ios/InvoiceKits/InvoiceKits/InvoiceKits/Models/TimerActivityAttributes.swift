import ActivityKit
import Foundation

struct TimerActivityAttributes: ActivityAttributes {
    let clientName: String
    let description: String

    struct ContentState: Codable, Hashable {
        let startedAt: Date
        let isRunning: Bool
    }
}
