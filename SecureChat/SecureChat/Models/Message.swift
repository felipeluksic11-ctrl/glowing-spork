import Foundation
import FirebaseFirestore

struct Message: Codable, Identifiable {
    @DocumentID var id: String?
    var senderId: String
    var encryptedContent: Data
    var timestamp: Timestamp
    var type: MessageType

    enum MessageType: String, Codable {
        case text
        case location
        case image
    }

    enum CodingKeys: String, CodingKey {
        case id
        case senderId
        case encryptedContent
        case timestamp
        case type
    }
}

struct DecryptedMessage: Identifiable {
    let id: String
    let senderId: String
    let content: String
    let timestamp: Date
    let type: Message.MessageType
    let isFromCurrentUser: Bool
}
