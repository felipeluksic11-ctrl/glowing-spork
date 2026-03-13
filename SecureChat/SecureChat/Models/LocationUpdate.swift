import Foundation
import FirebaseFirestore

struct LocationUpdate: Codable, Identifiable {
    @DocumentID var id: String?
    var encryptedLatitude: Data
    var encryptedLongitude: Data
    var timestamp: Timestamp

    enum CodingKeys: String, CodingKey {
        case id
        case encryptedLatitude
        case encryptedLongitude
        case timestamp
    }
}
