import SwiftUI

struct StatusBadge: View {
    let status: String

    private var badgeColor: Color {
        switch status.lowercased() {
        case "draft":      return .gray
        case "sent":       return .blue
        case "paid":       return .green
        case "overdue":    return .red
        case "cancelled":  return .orange
        default:           return .gray
        }
    }

    var body: some View {
        Text(status.uppercased())
            .font(.caption2)
            .fontWeight(.semibold)
            .foregroundStyle(.white)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(badgeColor, in: Capsule())
    }
}

#Preview {
    HStack(spacing: 8) {
        StatusBadge(status: "draft")
        StatusBadge(status: "sent")
        StatusBadge(status: "paid")
        StatusBadge(status: "overdue")
        StatusBadge(status: "cancelled")
    }
    .padding()
}
