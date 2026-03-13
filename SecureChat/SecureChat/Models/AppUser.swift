import Foundation
import FirebaseFirestore

struct AppUser: Codable, Identifiable, Hashable {
    @DocumentID var id: String?
    var displayName: String
    var username: String
    var phoneNumber: String?
    var publicKey: Data
    var fcmToken: String?
    var createdAt: Timestamp

    enum CodingKeys: String, CodingKey {
        case id
        case displayName
        case username
        case phoneNumber
        case publicKey
        case fcmToken
        case createdAt
    }

    static func == (lhs: AppUser, rhs: AppUser) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}
