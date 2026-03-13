import SwiftUI

struct ConversationsListView: View {
    @StateObject private var viewModel: ConversationsViewModel
    @Binding var selectedConversation: Conversation?
    private let currentUserId: String

    init(currentUserId: String, selectedConversation: Binding<Conversation?>) {
        self.currentUserId = currentUserId
        _viewModel = StateObject(wrappedValue: ConversationsViewModel(currentUserId: currentUserId))
        _selectedConversation = selectedConversation
    }

    var body: some View {
        List {
            if viewModel.conversations.isEmpty && !viewModel.isLoading {
                ContentUnavailableView(
                    "Sin conversaciones",
                    systemImage: "bubble.left.and.bubble.right",
                    description: Text("Inicia un chat desde tus contactos")
                )
            }

            ForEach(viewModel.conversations) { conversation in
                Button {
                    selectedConversation = conversation
                } label: {
                    ConversationRow(
                        name: viewModel.otherParticipantName(in: conversation),
                        timestamp: viewModel.formattedTimestamp(conversation.lastMessageTimestamp),
                        hasLocation: conversation.isLocationSharingActive
                    )
                }
            }
        }
        .navigationTitle("Chats")
        .overlay {
            if viewModel.isLoading {
                ProgressView()
            }
        }
    }
}

// MARK: - Conversation Row

private struct ConversationRow: View {
    let name: String
    let timestamp: String
    let hasLocation: Bool

    var body: some View {
        HStack(spacing: 12) {
            // Avatar
            ZStack {
                Circle()
                    .fill(.blue.opacity(0.15))
                    .frame(width: 50, height: 50)

                Text(String(name.prefix(1)).uppercased())
                    .font(.title2.bold())
                    .foregroundStyle(.blue)
            }

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(name)
                        .font(.body.weight(.semibold))
                        .foregroundStyle(.primary)

                    Spacer()

                    Text(timestamp)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                HStack(spacing: 4) {
                    if hasLocation {
                        Image(systemName: "location.fill")
                            .font(.caption2)
                            .foregroundStyle(.green)
                    }

                    Text("Mensaje encriptado")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
        }
        .padding(.vertical, 4)
    }
}
