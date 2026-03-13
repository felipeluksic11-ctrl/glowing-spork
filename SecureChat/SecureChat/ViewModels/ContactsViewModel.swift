import Foundation

@MainActor
final class ContactsViewModel: ObservableObject {
    @Published var contacts: [AppUser] = []
    @Published var searchResults: [AppUser] = []
    @Published var searchQuery = ""
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let firestoreService = FirestoreService.shared
    private let currentUserId: String

    init(currentUserId: String) {
        self.currentUserId = currentUserId
    }

    func loadContacts() async {
        isLoading = true
        do {
            contacts = try await firestoreService.fetchContacts(userId: currentUserId)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func searchUsers() async {
        let query = searchQuery.trimmingCharacters(in: .whitespaces)
        guard !query.isEmpty else {
            searchResults = []
            return
        }

        do {
            let results = try await firestoreService.searchUsers(byUsername: query)
            // Exclude current user and existing contacts
            let contactIds = Set(contacts.compactMap { $0.id })
            searchResults = results.filter {
                $0.id != currentUserId && !contactIds.contains($0.id ?? "")
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func addContact(_ user: AppUser) async {
        guard let contactId = user.id else { return }

        do {
            try await firestoreService.addContact(userId: currentUserId, contactId: contactId)
            contacts.append(user)
            searchResults.removeAll { $0.id == contactId }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func removeContact(_ user: AppUser) async {
        guard let contactId = user.id else { return }

        do {
            try await firestoreService.removeContact(userId: currentUserId, contactId: contactId)
            contacts.removeAll { $0.id == contactId }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
