import Foundation
import FirebaseFirestore

struct Conversation: Codable, Identifiable {
    @DocumentID var id: String?
    var participants: [String]
    var participantNames: [String: String]
    var createdAt: Timestamp
    var lastMessagePreview: String?
    var lastMessageTimestamp: Timestamp?
    var isLocationSharingActive: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case participants
        case participantNames
        case createdAt
        case lastMessagePreview
        case lastMessageTimestamp
        case isLocationSharingActive
    }
}
