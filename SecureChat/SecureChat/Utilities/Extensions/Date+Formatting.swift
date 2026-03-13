import Foundation

extension Date {
    var chatTimestamp: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "es")

        if Calendar.current.isDateInToday(self) {
            formatter.timeStyle = .short
            return formatter.string(from: self)
        } else if Calendar.current.isDateInYesterday(self) {
            return "Ayer"
        } else {
            formatter.dateStyle = .short
            return formatter.string(from: self)
        }
    }

    var messageTime: String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        formatter.locale = Locale(identifier: "es")
        return formatter.string(from: self)
    }
}
