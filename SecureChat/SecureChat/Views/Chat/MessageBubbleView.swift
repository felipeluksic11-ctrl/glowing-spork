import SwiftUI

struct MessageBubbleView: View {
    let message: DecryptedMessage

    var body: some View {
        HStack {
            if message.isFromCurrentUser { Spacer(minLength: 60) }

            VStack(alignment: message.isFromCurrentUser ? .trailing : .leading, spacing: 4) {
                Text(message.content)
                    .font(.body)
                    .foregroundStyle(message.isFromCurrentUser ? .white : .primary)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(
                        message.isFromCurrentUser
                        ? Color.blue
                        : Color(.systemGray5)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 18))

                HStack(spacing: 4) {
                    Image(systemName: "lock.fill")
                        .font(.system(size: 8))
                        .foregroundStyle(.secondary)

                    Text(formattedTime)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            if !message.isFromCurrentUser { Spacer(minLength: 60) }
        }
    }

    private var formattedTime: String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        formatter.locale = Locale(identifier: "es")
        return formatter.string(from: message.timestamp)
    }
}
