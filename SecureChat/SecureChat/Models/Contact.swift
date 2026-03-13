import Foundation
import FirebaseFirestore

struct Contact: Codable, Identifiable {
    @DocumentID var id: String?
    var addedAt: Timestamp
    var nickname: String?

    enum CodingKeys: String, CodingKey {
        case id
        case addedAt
        case nickname
    }
}
