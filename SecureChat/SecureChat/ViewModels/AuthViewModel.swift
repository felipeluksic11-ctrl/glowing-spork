import Foundation

@MainActor
final class AuthViewModel: ObservableObject {
    @Published var email = ""
    @Published var password = ""
    @Published var displayName = ""
    @Published var username = ""
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var isShowingSignUp = false

    private let authService: AuthService

    init(authService: AuthService) {
        self.authService = authService
    }

    func signIn() async {
        guard validateSignInFields() else { return }

        isLoading = true
        errorMessage = nil

        do {
            try await authService.signIn(email: email, password: password)
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func signUp() async {
        guard validateSignUpFields() else { return }

        isLoading = true
        errorMessage = nil

        do {
            try await authService.signUp(
                email: email,
                password: password,
                displayName: displayName,
                username: username
            )
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func signOut() {
        do {
            try authService.signOut()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func validateSignInFields() -> Bool {
        if email.trimmingCharacters(in: .whitespaces).isEmpty {
            errorMessage = "Ingresa tu email"
            return false
        }
        if password.isEmpty {
            errorMessage = "Ingresa tu contrasena"
            return false
        }
        return true
    }

    private func validateSignUpFields() -> Bool {
        if displayName.trimmingCharacters(in: .whitespaces).isEmpty {
            errorMessage = "Ingresa tu nombre"
            return false
        }
        if username.trimmingCharacters(in: .whitespaces).isEmpty {
            errorMessage = "Ingresa un nombre de usuario"
            return false
        }
        if email.trimmingCharacters(in: .whitespaces).isEmpty {
            errorMessage = "Ingresa tu email"
            return false
        }
        if password.count < 6 {
            errorMessage = "La contrasena debe tener al menos 6 caracteres"
            return false
        }
        return true
    }
}
