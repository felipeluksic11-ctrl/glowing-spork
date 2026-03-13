import SwiftUI

struct ContactsListView: View {
    @StateObject private var viewModel: ContactsViewModel
    @State private var showAddContact = false
    private let onStartChat: (AppUser) -> Void

    init(currentUserId: String, onStartChat: @escaping (AppUser) -> Void) {
        _viewModel = StateObject(wrappedValue: ContactsViewModel(currentUserId: currentUserId))
        self.onStartChat = onStartChat
    }

    var body: some View {
        List {
            if viewModel.contacts.isEmpty && !viewModel.isLoading {
                ContentUnavailableView(
                    "Sin contactos",
                    systemImage: "person.2.slash",
                    description: Text("Agrega contactos para empezar a chatear")
                )
            }

            ForEach(viewModel.contacts) { contact in
                Button {
                    onStartChat(contact)
                } label: {
                    HStack(spacing: 12) {
                        Image(systemName: "person.circle.fill")
                            .font(.title)
                            .foregroundStyle(.blue)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(contact.displayName)
                                .font(.body.weight(.medium))
                                .foregroundStyle(.primary)

                            Text("@\(contact.username)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        Image(systemName: "bubble.left.fill")
                            .foregroundStyle(.blue.opacity(0.6))
                    }
                }
            }
            .onDelete { indexSet in
                Task {
                    for index in indexSet {
                        await viewModel.removeContact(viewModel.contacts[index])
                    }
                }
            }
        }
        .navigationTitle("Contactos")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showAddContact = true
                } label: {
                    Image(systemName: "person.badge.plus")
                }
            }
        }
        .sheet(isPresented: $showAddContact) {
            AddContactView(viewModel: viewModel)
        }
        .task {
            await viewModel.loadContacts()
        }
    }
}
