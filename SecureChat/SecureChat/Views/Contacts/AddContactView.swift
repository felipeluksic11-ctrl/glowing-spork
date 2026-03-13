import SwiftUI

struct AddContactView: View {
    @ObservedObject var viewModel: ContactsViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Search bar
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundStyle(.secondary)

                    TextField("Buscar por nombre de usuario", text: $viewModel.searchQuery)
                        .autocapitalization(.none)
                        .textContentType(.username)
                        .onSubmit {
                            Task { await viewModel.searchUsers() }
                        }

                    if !viewModel.searchQuery.isEmpty {
                        Button {
                            viewModel.searchQuery = ""
                            viewModel.searchResults = []
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(10)
                .padding()

                // Results
                List {
                    if viewModel.searchResults.isEmpty && !viewModel.searchQuery.isEmpty {
                        ContentUnavailableView.search(text: viewModel.searchQuery)
                    }

                    ForEach(viewModel.searchResults) { user in
                        HStack(spacing: 12) {
                            Image(systemName: "person.circle")
                                .font(.title2)
                                .foregroundStyle(.gray)

                            VStack(alignment: .leading, spacing: 2) {
                                Text(user.displayName)
                                    .font(.body.weight(.medium))
                                Text("@\(user.username)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }

                            Spacer()

                            Button("Agregar") {
                                Task {
                                    await viewModel.addContact(user)
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.small)
                        }
                    }
                }
                .listStyle(.plain)
            }
            .navigationTitle("Agregar Contacto")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cerrar") { dismiss() }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button("Buscar") {
                        Task { await viewModel.searchUsers() }
                    }
                    .disabled(viewModel.searchQuery.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}
