// SecureChat Interactive Simulator
const app = {
    currentScreen: 'login',
    currentTab: 0,
    isAuthenticated: false,
    currentUser: { name: 'Felipe', username: 'felipesolar', email: 'felipe@email.com' },
    showFullMap: false,
    locationSharingActive: true,

    contacts: [
        { id: 1, name: 'Maria Garcia', username: 'mariagarcia', initial: 'M' },
        { id: 2, name: 'Carlos Lopez', username: 'carloslopez', initial: 'C' },
        { id: 3, name: 'Ana Martinez', username: 'anamartinez', initial: 'A' },
        { id: 4, name: 'Diego Herrera', username: 'diegoherrera', initial: 'D' },
    ],

    // Users available to search and add (simulated server)
    allUsers: [
        { id: 10, name: 'Sofia Ramirez', username: 'sofiaramirez', initial: 'S' },
        { id: 11, name: 'Pablo Mendoza', username: 'pablomendoza', initial: 'P' },
        { id: 12, name: 'Laura Torres', username: 'lauratorres', initial: 'L' },
        { id: 13, name: 'Roberto Diaz', username: 'robertodiaz', initial: 'R' },
        { id: 14, name: 'Valentina Cruz', username: 'valentinacruz', initial: 'V' },
        { id: 15, name: 'Andres Morales', username: 'andresmorales', initial: 'A' },
        { id: 16, name: 'Camila Vargas', username: 'camilavargas', initial: 'C' },
        { id: 17, name: 'Javier Rios', username: 'javierrios', initial: 'J' },
        { id: 18, name: 'Isabella Flores', username: 'isabellaflores', initial: 'I' },
        { id: 19, name: 'Daniel Gutierrez', username: 'danielgutierrez', initial: 'D' },
    ],

    emergencyActive: false,
    emergencyCountdown: null,
    showAddContact: false,
    addContactSearch: '',
    confirmDeleteContact: null,

    conversations: [
        {
            id: 1, name: 'Maria Garcia', initial: 'M', time: '2:34 PM',
            hasLocation: true, preview: 'Mensaje encriptado',
            messages: [
                { text: 'Hola! Ya llegue al centro', sent: false, time: '2:30 PM' },
                { text: 'Perfecto, te veo en el mapa', sent: true, time: '2:31 PM' },
                { text: 'Voy caminando hacia ti', sent: false, time: '2:33 PM' },
                { text: 'Te espero en la esquina', sent: true, time: '2:34 PM' },
            ]
        },
        {
            id: 2, name: 'Carlos Lopez', initial: 'C', time: '1:15 PM',
            hasLocation: true, preview: 'Mensaje encriptado',
            messages: [
                { text: 'Nos vemos en la oficina?', sent: true, time: '1:10 PM' },
                { text: 'Si, ya estoy llegando', sent: false, time: '1:12 PM' },
                { text: 'Activa tu ubicacion para verte', sent: true, time: '1:15 PM' },
            ]
        },
        {
            id: 3, name: 'Ana Martinez', initial: 'A', time: 'Ayer',
            hasLocation: false, preview: 'Mensaje encriptado',
            messages: [
                { text: 'Revisaste el documento?', sent: false, time: '5:20 PM' },
                { text: 'Si, todo bien. Aprobado!', sent: true, time: '5:45 PM' },
            ]
        },
    ],

    activeChat: null,
    mapPinPositions: { me: { x: 55, y: 45 }, other: { x: 35, y: 65 } },
    mapAnimationInterval: null,

    // Initialize
    init() {
        this.render();
        this.startMapAnimation();
    },

    // Reset to login
    reset() {
        this.isAuthenticated = false;
        this.currentScreen = 'login';
        this.currentTab = 0;
        this.activeChat = null;
        this.showFullMap = false;
        this.showAddContact = false;
        this.newContactForm = { name: '', username: '', phone: '', email: '' };
        this.formError = '';
        this.confirmDeleteContact = null;
        // Restore original contacts
        this.contacts = [
            { id: 1, name: 'Maria Garcia', username: 'mariagarcia', initial: 'M' },
            { id: 2, name: 'Carlos Lopez', username: 'carloslopez', initial: 'C' },
            { id: 3, name: 'Ana Martinez', username: 'anamartinez', initial: 'A' },
            { id: 4, name: 'Diego Herrera', username: 'diegoherrera', initial: 'D' },
        ];
        this.conversations = [
            { id: 1, name: 'Maria Garcia', initial: 'M', time: '2:34 PM', hasLocation: true, preview: 'Mensaje encriptado', messages: [
                { text: 'Hola! Ya llegue al centro', sent: false, time: '2:30 PM' },
                { text: 'Perfecto, te veo en el mapa', sent: true, time: '2:31 PM' },
                { text: 'Voy caminando hacia ti', sent: false, time: '2:33 PM' },
                { text: 'Te espero en la esquina', sent: true, time: '2:34 PM' },
            ]},
            { id: 2, name: 'Carlos Lopez', initial: 'C', time: '1:15 PM', hasLocation: true, preview: 'Mensaje encriptado', messages: [
                { text: 'Nos vemos en la oficina?', sent: true, time: '1:10 PM' },
                { text: 'Si, ya estoy llegando', sent: false, time: '1:12 PM' },
                { text: 'Activa tu ubicacion para verte', sent: true, time: '1:15 PM' },
            ]},
            { id: 3, name: 'Ana Martinez', initial: 'A', time: 'Ayer', hasLocation: false, preview: 'Mensaje encriptado', messages: [
                { text: 'Revisaste el documento?', sent: false, time: '5:20 PM' },
                { text: 'Si, todo bien. Aprobado!', sent: true, time: '5:45 PM' },
            ]},
        ];
        this.render();
    },

    // Map pin animation
    startMapAnimation() {
        if (this.mapAnimationInterval) clearInterval(this.mapAnimationInterval);
        this.mapAnimationInterval = setInterval(() => {
            this.mapPinPositions.other.x += (Math.random() - 0.3) * 3;
            this.mapPinPositions.other.y += (Math.random() - 0.5) * 2;
            this.mapPinPositions.other.x = Math.max(15, Math.min(85, this.mapPinPositions.other.x));
            this.mapPinPositions.other.y = Math.max(20, Math.min(80, this.mapPinPositions.other.y));

            // Update pins if visible
            const otherPin = document.getElementById('otherPin');
            if (otherPin) {
                otherPin.style.left = this.mapPinPositions.other.x + '%';
                otherPin.style.top = this.mapPinPositions.other.y + '%';
            }
        }, 2000);
    },

    // Main render
    render() {
        const screen = document.getElementById('screen');
        if (!this.isAuthenticated) {
            if (this.currentScreen === 'signup') {
                screen.innerHTML = this.renderSignUp();
            } else {
                screen.innerHTML = this.renderLogin();
            }
        } else if (this.activeChat) {
            screen.innerHTML = this.renderChat();
            this.scrollChatToBottom();
        } else if (this.showAddContact) {
            screen.innerHTML = this.renderAddContactScreen();
        } else {
            screen.innerHTML = this.renderMainTabs();
        }
    },

    // Status bar
    renderStatusBar(dark = false) {
        const now = new Date();
        const time = now.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', hour12: false });
        return `
            <div class="status-bar ${dark ? 'dark' : ''}">
                <span>${time}</span>
                <span>&#9679;&#9679;&#9679;&#9679; WiFi &#128267;</span>
            </div>
        `;
    },

    // LOGIN
    renderLogin() {
        return `
            <div class="login-screen">
                ${this.renderStatusBar()}
                <div class="login-logo">&#128274;</div>
                <div class="login-title">SecureChat</div>
                <div class="login-subtitle">Mensajeria encriptada E2E</div>
                <input class="input-field" type="email" placeholder="Email" value="felipe@email.com" id="loginEmail">
                <input class="input-field" type="password" placeholder="Contrasena" value="••••••••" id="loginPass">
                <button class="btn-primary" onclick="app.handleLogin()">Iniciar Sesion</button>
                <button class="btn-link" onclick="app.currentScreen='signup'; app.render();">Crear cuenta</button>
            </div>
        `;
    },

    // SIGNUP
    renderSignUp() {
        return `
            <div class="login-screen">
                ${this.renderStatusBar()}
                <div style="font-size:50px; margin-bottom:8px;">&#128273;</div>
                <div class="login-title">Crear Cuenta</div>
                <div class="login-subtitle">Se generaran tus llaves de encriptacion</div>
                <input class="input-field" placeholder="Nombre completo" value="Felipe Solar">
                <input class="input-field" placeholder="Nombre de usuario" value="felipesolar">
                <input class="input-field" type="email" placeholder="Email" value="felipe@email.com">
                <input class="input-field" type="password" placeholder="Contrasena (min 6 caracteres)">
                <button class="btn-primary" onclick="app.handleSignUp()">Registrarse</button>
                <button class="btn-link" onclick="app.currentScreen='login'; app.render();">Ya tengo cuenta</button>
            </div>
        `;
    },

    handleLogin() {
        this.showKeyGeneration('Verificando llaves de encriptacion...', 'Cargando llave privada desde Keychain');
    },

    handleSignUp() {
        this.showKeyGeneration('Generando par de llaves Curve25519...', 'Llave privada guardada en Keychain\nLlave publica subida a Firestore');
    },

    showKeyGeneration(title, detail) {
        const screen = document.getElementById('screen');
        const overlay = document.createElement('div');
        overlay.className = 'key-gen-overlay';
        overlay.innerHTML = `
            <div class="key-icon">&#128272;</div>
            <div class="key-text">${title}</div>
            <div class="key-progress"><div class="key-progress-bar"></div></div>
            <div class="key-detail">${detail}</div>
        `;
        screen.appendChild(overlay);

        setTimeout(() => {
            this.isAuthenticated = true;
            this.currentScreen = 'main';
            this.render();
            this.showToast('&#128274; Encriptacion E2E configurada');
        }, 2200);
    },

    // MAIN TABS
    renderMainTabs() {
        let content = '';
        if (this.currentTab === 0) content = this.renderConversationsList();
        else if (this.currentTab === 1) content = this.renderContactsList();
        else content = this.renderProfile();

        return `
            ${this.renderStatusBar()}
            ${content}
            <div class="tab-bar">
                <button class="tab-item ${this.currentTab === 0 ? 'active' : ''}" onclick="app.switchTab(0)">
                    <span class="tab-icon">&#128488;</span>
                    <span class="tab-label">Chats</span>
                </button>
                <button class="tab-item sos-tab-item" onclick="app.triggerEmergency()">
                    <span class="sos-tab-btn">SOS</span>
                    <span class="tab-label" style="color:#FF3B30;">Emergencia</span>
                </button>
                <button class="tab-item ${this.currentTab === 1 ? 'active' : ''}" onclick="app.switchTab(1)">
                    <span class="tab-icon">&#128101;</span>
                    <span class="tab-label">Contactos</span>
                </button>
                <button class="tab-item ${this.currentTab === 2 ? 'active' : ''}" onclick="app.switchTab(2)">
                    <span class="tab-icon">&#128100;</span>
                    <span class="tab-label">Perfil</span>
                </button>
            </div>
        `;
    },

    switchTab(tab) {
        this.currentTab = tab;
        this.render();
    },

    // CONVERSATIONS LIST
    renderConversationsList() {
        const rows = this.conversations.map(conv => `
            <div class="conversation-row" onclick="app.openChat(${conv.id})">
                <div class="avatar">${conv.initial}</div>
                <div class="conversation-info">
                    <div class="conversation-name">${conv.name}</div>
                    <div class="conversation-preview">
                        ${conv.hasLocation ? '<span class="location-dot"></span>' : ''}
                        <span>&#128274; ${conv.preview}</span>
                    </div>
                </div>
                <div class="conversation-time">${conv.time}</div>
            </div>
        `).join('');

        return `
            <div class="nav-bar">
                <div class="nav-title">Chats</div>
            </div>
            <div class="screen-content">${rows}</div>
        `;
    },

    // CONTACTS LIST
    renderContactsList() {
        if (this.showAddContact) {
            return this.renderAddContactScreen();
        }

        const rows = this.contacts.length > 0 ? this.contacts.map(c => `
            <div class="contact-row" id="contact-row-${c.id}">
                <div class="contact-avatar" onclick="app.startChatWithContact(${c.id})">${c.initial}</div>
                <div class="contact-info" onclick="app.startChatWithContact(${c.id})">
                    <div class="contact-name">${c.name}</div>
                    <div class="contact-username">@${c.username}</div>
                </div>
                <button class="contact-delete-btn" onclick="app.confirmDeleteContact(${c.id})" title="Eliminar contacto">&#128465;</button>
            </div>
            ${this.confirmDeleteContact === c.id ? `
                <div class="delete-confirm-bar">
                    <span>Eliminar a ${c.name}?</span>
                    <div class="delete-confirm-actions">
                        <button class="delete-confirm-cancel" onclick="app.cancelDelete()">Cancelar</button>
                        <button class="delete-confirm-yes" onclick="app.deleteContact(${c.id})">Eliminar</button>
                    </div>
                </div>
            ` : ''}
        `).join('') : `
            <div class="empty-state">
                <div class="empty-state-icon">&#128101;</div>
                <div class="empty-state-title">Sin contactos</div>
                <div class="empty-state-text">Agrega contactos para empezar a chatear</div>
            </div>
        `;

        return `
            <div class="nav-bar">
                <div class="nav-title">Contactos</div>
                <button class="nav-action" onclick="app.openAddContact()">+</button>
            </div>
            <div class="screen-content">
                <div class="contacts-count">${this.contacts.length} contacto${this.contacts.length !== 1 ? 's' : ''}</div>
                ${rows}
            </div>
        `;
    },

    // ADD CONTACT FORM
    newContactForm: { name: '', username: '', phone: '', email: '' },
    formError: '',

    openAddContact() {
        this.showAddContact = true;
        this.newContactForm = { name: '', username: '', phone: '', email: '' };
        this.formError = '';
        this.render();
        setTimeout(() => {
            const input = document.getElementById('formName');
            if (input) input.focus();
        }, 100);
    },

    closeAddContact() {
        this.showAddContact = false;
        this.newContactForm = { name: '', username: '', phone: '', email: '' };
        this.formError = '';
        this.render();
    },

    renderAddContactScreen() {
        const f = this.newContactForm;
        return `
            <div class="chat-container" style="background:#f2f2f7;">
                ${this.renderStatusBar()}
                <div class="nav-bar" style="border-bottom: 0.5px solid #e5e5ea; background:#fff;">
                    <button class="nav-back" onclick="app.closeAddContact()">Cancelar</button>
                    <span class="nav-title-small">Nuevo Contacto</span>
                    <button class="nav-back" style="font-weight:600;" onclick="app.saveNewContact()">Guardar</button>
                </div>
                <div class="screen-content" style="padding:0;">
                    <!-- Avatar preview -->
                    <div class="form-avatar-section">
                        <div class="form-avatar-circle">
                            ${f.name.trim() ? f.name.trim().charAt(0).toUpperCase() : '&#128100;'}
                        </div>
                        <div class="form-avatar-hint">La inicial se genera automaticamente</div>
                    </div>

                    <!-- Form fields -->
                    <div class="form-section">
                        <div class="form-section-title">INFORMACION</div>
                        <div class="form-group">
                            <div class="form-field">
                                <label class="form-label">Nombre *</label>
                                <input class="form-input" id="formName" placeholder="Nombre completo"
                                    value="${this.escapeHtml(f.name)}"
                                    oninput="app.updateFormField('name', this.value)">
                            </div>
                            <div class="form-divider"></div>
                            <div class="form-field">
                                <label class="form-label">Username *</label>
                                <input class="form-input" id="formUsername" placeholder="nombre_de_usuario"
                                    value="${this.escapeHtml(f.username)}"
                                    oninput="app.updateFormField('username', this.value)"
                                    style="text-transform:lowercase;">
                            </div>
                            <div class="form-divider"></div>
                            <div class="form-field">
                                <label class="form-label">Telefono</label>
                                <input class="form-input" id="formPhone" placeholder="+52 555 123 4567" type="tel"
                                    value="${this.escapeHtml(f.phone)}"
                                    oninput="app.updateFormField('phone', this.value)">
                            </div>
                            <div class="form-divider"></div>
                            <div class="form-field">
                                <label class="form-label">Email</label>
                                <input class="form-input" id="formEmail" placeholder="correo@ejemplo.com" type="email"
                                    value="${this.escapeHtml(f.email)}"
                                    oninput="app.updateFormField('email', this.value)">
                            </div>
                        </div>
                    </div>

                    ${this.formError ? `
                        <div class="form-error">${this.formError}</div>
                    ` : ''}

                    <!-- E2E info -->
                    <div class="form-section">
                        <div class="form-section-title">ENCRIPTACION</div>
                        <div class="form-group">
                            <div class="form-info-row">
                                <span class="form-info-icon">&#128274;</span>
                                <span class="form-info-text">Al iniciar un chat, se generara automaticamente una llave compartida E2E con este contacto via Diffie-Hellman.</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    updateFormField(field, value) {
        this.newContactForm[field] = value;
        this.formError = '';
        // Update avatar preview without full re-render
        const avatar = document.querySelector('.form-avatar-circle');
        if (avatar && field === 'name') {
            avatar.textContent = value.trim() ? value.trim().charAt(0).toUpperCase() : '';
            if (!value.trim()) avatar.innerHTML = '&#128100;';
        }
    },

    saveNewContact() {
        const f = this.newContactForm;
        const name = f.name.trim();
        const username = f.username.trim().toLowerCase().replace(/\s/g, '_');

        // Validation
        if (!name) {
            this.formError = 'El nombre es obligatorio';
            this.render();
            setTimeout(() => document.getElementById('formName')?.focus(), 50);
            return;
        }
        if (!username) {
            this.formError = 'El username es obligatorio';
            this.render();
            setTimeout(() => document.getElementById('formUsername')?.focus(), 50);
            return;
        }
        if (username.length < 3) {
            this.formError = 'El username debe tener al menos 3 caracteres';
            this.render();
            setTimeout(() => document.getElementById('formUsername')?.focus(), 50);
            return;
        }

        // Check duplicate username
        const existingUsername = this.contacts.find(c => c.username === username);
        if (existingUsername) {
            this.formError = `Ya tienes un contacto con username "@${username}"`;
            this.render();
            return;
        }

        // Create new contact
        const newContact = {
            id: Date.now(),
            name: name,
            username: username,
            initial: name.charAt(0).toUpperCase(),
            phone: f.phone.trim() || null,
            email: f.email.trim() || null,
        };

        this.contacts.push(newContact);
        this.showAddContact = false;
        this.newContactForm = { name: '', username: '', phone: '', email: '' };
        this.formError = '';
        this.render();
        this.showToast(`&#9989; ${name} agregado como contacto`);
    },

    // DELETE CONTACT
    confirmDeleteContact(contactId) {
        this.confirmDeleteContact = contactId;
        this.render();
    },

    cancelDelete() {
        this.confirmDeleteContact = null;
        this.render();
    },

    deleteContact(contactId) {
        const contact = this.contacts.find(c => c.id === contactId);
        const name = contact ? contact.name : 'Contacto';

        this.contacts = this.contacts.filter(c => c.id !== contactId);
        this.confirmDeleteContact = null;

        // Also remove conversation if exists
        this.conversations = this.conversations.filter(c => c.name !== name);

        this.render();
        this.showToast(`&#128465; ${name} eliminado`);
    },

    startChatWithContact(contactId) {
        const contact = this.contacts.find(c => c.id === contactId);
        if (!contact) return;

        // Check if conversation exists
        const existing = this.conversations.find(c => c.name === contact.name);
        if (existing) {
            this.openChat(existing.id);
        } else {
            // Create new conversation
            const newConv = {
                id: Date.now(), // unique id
                name: contact.name,
                initial: contact.initial,
                time: 'Ahora',
                hasLocation: true,
                preview: 'Nueva conversacion',
                messages: []
            };
            this.conversations.unshift(newConv);
            this.openChat(newConv.id);
            this.showToast('&#128274; Llave compartida derivada via DH');
        }
    },

    // PROFILE
    renderProfile() {
        const fakeFingerprint = 'A7 3B F2 1C D8 4E 9A 0F B6 52 E1 7D C3 48 FA 2B';
        return `
            <div class="nav-bar">
                <div class="nav-title">Perfil</div>
            </div>
            <div class="screen-content">
                <div class="profile-header">
                    <div class="profile-avatar">F</div>
                    <div>
                        <div class="profile-name">${this.currentUser.name}</div>
                        <div class="profile-username">@${this.currentUser.username}</div>
                    </div>
                </div>

                <div class="profile-section">
                    <div class="profile-section-title">Seguridad</div>
                    <div class="security-banner">
                        <div class="security-banner-title">&#128274; Encriptacion E2E activa</div>
                        <div class="security-banner-text">Tus mensajes y ubicacion estan protegidos con encriptacion de extremo a extremo usando Curve25519 + AES-GCM.</div>
                    </div>
                    <div class="profile-row">
                        <span class="profile-row-icon">&#128273;</span>
                        <span class="profile-row-text">Huella de llave publica</span>
                        <span class="profile-row-detail">${fakeFingerprint}</span>
                    </div>
                </div>

                <div class="profile-section">
                    <div class="profile-section-title">Cuenta</div>
                    <div class="profile-row">
                        <span class="profile-row-icon">&#9993;</span>
                        <span class="profile-row-text">${this.currentUser.email}</span>
                    </div>
                    <div class="profile-row" style="cursor:pointer" onclick="app.handleSignOut()">
                        <span class="profile-row-icon">&#10145;</span>
                        <span class="profile-row-text danger">Cerrar sesion</span>
                    </div>
                </div>

                <div class="profile-section">
                    <div class="profile-section-title">Informacion</div>
                    <div class="profile-row">
                        <span class="profile-row-icon">&#8505;</span>
                        <span class="profile-row-text" style="color:#8e8e93">Version 1.0.0</span>
                    </div>
                </div>
            </div>
        `;
    },

    handleSignOut() {
        this.isAuthenticated = false;
        this.currentScreen = 'login';
        this.activeChat = null;
        this.render();
    },

    // CHAT
    openChat(convId) {
        this.activeChat = this.conversations.find(c => c.id === convId);
        this.render();
    },

    renderChat() {
        const chat = this.activeChat;
        const messages = chat.messages.map(m => `
            <div class="message-bubble ${m.sent ? 'message-sent' : 'message-received'}">${m.text}</div>
            <div class="message-time ${m.sent ? 'sent' : ''}">
                <span class="encryption-badge">&#128274;</span> ${m.time}
            </div>
        `).join('');

        const mapSection = chat.hasLocation && this.locationSharingActive ? `
            <div class="chat-map" onclick="app.openFullMap()">
                <div class="map-grid"></div>
                <div class="map-road horizontal"></div>
                <div class="map-road vertical"></div>
                <div class="map-road diagonal"></div>
                <div class="map-pin" style="left:${this.mapPinPositions.me.x}%;top:${this.mapPinPositions.me.y}%">
                    <div class="pin-dot">F</div>
                    <div class="pin-label">Tu</div>
                </div>
                <div class="map-pin" id="otherPin" style="left:${this.mapPinPositions.other.x}%;top:${this.mapPinPositions.other.y}%">
                    <div class="pin-dot other">${chat.initial}</div>
                    <div class="pin-label">${chat.name.split(' ')[0]}</div>
                </div>
                <div class="map-expand-hint">&#128506; Expandir mapa</div>
            </div>
        ` : '';

        const locIcon = this.locationSharingActive ? '&#128205;' : '&#128683;';

        return `
            <div class="chat-container">
                ${this.renderStatusBar()}
                <div class="nav-bar" style="border-bottom: 0.5px solid #e5e5ea;">
                    <button class="nav-back" onclick="app.closeChat()">&#9664; Chats</button>
                    <span class="nav-title-small">${chat.name}</span>
                    <div style="display:flex;gap:8px;align-items:center;">
                        <button class="sos-chat-btn" onclick="app.triggerEmergency()">SOS</button>
                        <button class="nav-action" onclick="app.openFullMap()">&#128506;</button>
                    </div>
                </div>
                ${mapSection}
                <div class="chat-messages" id="chatMessages">
                    ${messages}
                </div>
                <div class="chat-input-bar">
                    <button class="location-toggle" onclick="app.toggleLocation()" title="Toggle ubicacion">
                        ${locIcon}
                    </button>
                    <input class="chat-input" id="chatInput" placeholder="Mensaje encriptado..."
                        onkeydown="if(event.key==='Enter'){app.sendMessage(); event.preventDefault();}">
                    <button class="send-btn" onclick="app.sendMessage()">&#9650;</button>
                </div>
            </div>
            ${this.showFullMap ? this.renderFullScreenMap() : ''}
        `;
    },

    sendMessage() {
        const input = document.getElementById('chatInput');
        if (!input || !input.value.trim()) return;

        const text = input.value.trim();
        const now = new Date();
        const time = now.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', hour12: true });

        // Show encryption animation
        this.showEncryptAnimation();

        // Add message after brief delay (simulating encryption)
        setTimeout(() => {
            this.activeChat.messages.push({ text, sent: true, time });
            this.render();

            // Simulate reply after 1.5s
            setTimeout(() => {
                const replies = [
                    'Entendido!', 'Perfecto', 'Ya te veo en el mapa',
                    'Voy para alla', 'OK, nos vemos', 'Genial!',
                    'Dame 5 minutos', 'Ya casi llego', 'Listo!',
                    'Te mando mi ubicacion', 'Ahi nos vemos'
                ];
                const reply = replies[Math.floor(Math.random() * replies.length)];
                const replyTime = new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', hour12: true });
                this.activeChat.messages.push({ text: reply, sent: false, time: replyTime });
                this.render();
            }, 1200 + Math.random() * 1500);
        }, 300);

        input.value = '';
    },

    showEncryptAnimation() {
        const container = document.querySelector('.chat-container');
        if (!container) return;

        const anim = document.createElement('div');
        anim.className = 'encrypt-animation';
        const chars = '0123456789ABCDEF';
        let encrypted = 'AES-GCM: ';
        for (let i = 0; i < 12; i++) encrypted += chars[Math.floor(Math.random() * 16)];
        anim.textContent = encrypted;
        container.appendChild(anim);

        setTimeout(() => anim.remove(), 900);
    },

    closeChat() {
        this.activeChat = null;
        this.showFullMap = false;
        this.render();
    },

    toggleLocation() {
        this.locationSharingActive = !this.locationSharingActive;
        this.render();
        if (this.locationSharingActive) {
            this.showToast('&#128205; Ubicacion activada y encriptada');
        } else {
            this.showToast('&#128683; Ubicacion desactivada');
        }
    },

    scrollChatToBottom() {
        setTimeout(() => {
            const el = document.getElementById('chatMessages');
            if (el) el.scrollTop = el.scrollHeight;
        }, 50);
    },

    // FULL SCREEN MAP
    openFullMap() {
        this.showFullMap = true;
        this.render();
    },

    closeFullMap() {
        this.showFullMap = false;
        this.render();
    },

    renderFullScreenMap() {
        const chat = this.activeChat;
        return `
            <div class="fullscreen-map">
                <div class="map-grid"></div>
                <div class="map-road horizontal"></div>
                <div class="map-road vertical"></div>
                <div class="map-road diagonal"></div>

                <div class="map-pin" style="left:${this.mapPinPositions.me.x}%;top:55%;">
                    <div class="pin-dot" style="width:44px;height:44px;font-size:16px;">F</div>
                    <div class="pin-label">Tu</div>
                </div>
                <div class="map-pin" id="otherPin" style="left:${this.mapPinPositions.other.x}%;top:35%;">
                    <div class="pin-dot other" style="width:44px;height:44px;font-size:16px;">${chat.initial}</div>
                    <div class="pin-label">${chat.name.split(' ')[0]}</div>
                </div>

                <div class="map-overlay-bar">
                    <button class="nav-back" onclick="app.closeFullMap()">Cerrar</button>
                    <span class="nav-title-small">Ubicaciones</span>
                    <span style="width:60px"></span>
                </div>

                <div class="map-bottom-pill">
                    &#128101; 2 participantes visibles &bull; &#128274; Ubicaciones encriptadas
                </div>
            </div>
        `;
    },

    // EMERGENCY SOS
    triggerEmergency() {
        if (this.emergencyActive) return;

        // Show confirmation first
        const screen = document.getElementById('screen');
        const confirm = document.createElement('div');
        confirm.className = 'sos-confirm-overlay';
        confirm.id = 'sosConfirm';
        confirm.innerHTML = `
            <div class="sos-confirm-box">
                <div class="sos-confirm-icon">&#9888;&#65039;</div>
                <div class="sos-confirm-title">Enviar alerta de emergencia?</div>
                <div class="sos-confirm-text">Se activara tu camara y microfono, compartiendo video y audio en vivo con TODOS tus contactos junto con tu ubicacion.</div>
                <div class="sos-confirm-buttons">
                    <button class="sos-confirm-cancel" onclick="document.getElementById('sosConfirm').remove()">Cancelar</button>
                    <button class="sos-confirm-send" onclick="app.executeEmergency()">Enviar SOS</button>
                </div>
                <div class="sos-confirm-hint">Manten presionado 3 seg para envio rapido</div>
            </div>
        `;
        screen.appendChild(confirm);
    },

    executeEmergency() {
        const confirmEl = document.getElementById('sosConfirm');
        if (confirmEl) confirmEl.remove();

        this.emergencyActive = true;
        const screen = document.getElementById('screen');

        // Create audio context for alarm sound
        this.playAlarmSound();

        // Full screen emergency overlay
        const overlay = document.createElement('div');
        overlay.className = 'sos-active-overlay';
        overlay.id = 'sosOverlay';
        overlay.innerHTML = `
            <div class="sos-flash"></div>
            <div class="sos-content">
                <div class="sos-siren">&#128680;</div>
                <div class="sos-active-title">ALERTA DE EMERGENCIA</div>
                <div class="sos-active-subtitle">Enviada a ${this.contacts.length} contactos</div>

                <div class="sos-status-list" id="sosStatusList">
                    <!-- Populated dynamically -->
                </div>

                <div class="sos-stream-box" id="sosStreamBox">
                    <div class="sos-stream-header">
                        <div class="sos-stream-rec">&#9679; REC</div>
                        <div class="sos-stream-label">Transmision en vivo</div>
                        <div class="sos-stream-viewers" id="sosViewerCount">0 viendo</div>
                    </div>
                    <div class="sos-camera-feed" id="sosCameraFeed">
                        <video id="sosVideoElement" autoplay playsinline muted></video>
                        <div class="sos-camera-fallback" id="sosCameraFallback">
                            <div class="sos-camera-icon">&#127909;</div>
                            <div>Iniciando camara...</div>
                        </div>
                        <div class="sos-camera-overlay-badge">
                            <span>&#128274; E2E</span>
                        </div>
                    </div>
                    <div class="sos-audio-indicator">
                        <div class="sos-mic-icon">&#127908;</div>
                        <div class="sos-audio-bars" id="sosAudioBars">
                            <div class="sos-audio-bar" style="height:8px"></div>
                            <div class="sos-audio-bar" style="height:14px"></div>
                            <div class="sos-audio-bar" style="height:20px"></div>
                            <div class="sos-audio-bar" style="height:12px"></div>
                            <div class="sos-audio-bar" style="height:18px"></div>
                            <div class="sos-audio-bar" style="height:10px"></div>
                            <div class="sos-audio-bar" style="height:16px"></div>
                            <div class="sos-audio-bar" style="height:8px"></div>
                        </div>
                        <div class="sos-audio-label">Microfono activo</div>
                    </div>
                </div>

                <div class="sos-location-box">
                    <div class="sos-location-icon">&#128205;</div>
                    <div class="sos-location-text">
                        <div>Ubicacion compartida en tiempo real</div>
                        <div class="sos-location-coords">19.4326° N, 99.1332° W</div>
                    </div>
                    <div class="sos-location-live">EN VIVO</div>
                </div>

                <div class="sos-timer" id="sosTimer">Alerta activa: 00:00</div>

                <button class="sos-stop-btn" onclick="app.stopEmergency()">
                    Detener Alerta
                </button>
                <button class="sos-preview-viewer-btn" onclick="app.openSOSViewer('${this.currentUser.name}', 'F')">
                    &#128064; Ver como receptor
                </button>
            </div>
        `;
        screen.appendChild(overlay);

        // Start camera and mic stream
        this.startLiveStream();

        // Animate contact notifications one by one
        this.animateContactNotifications();

        // Start timer
        this.emergencyStartTime = Date.now();
        this.emergencyTimerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.emergencyStartTime) / 1000);
            const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const secs = String(elapsed % 60).padStart(2, '0');
            const timer = document.getElementById('sosTimer');
            if (timer) timer.textContent = `Alerta activa: ${mins}:${secs}`;
        }, 1000);
    },

    animateContactNotifications() {
        const list = document.getElementById('sosStatusList');
        if (!list) return;

        const statuses = ['Enviando...', 'Recibido', 'Alerta sonando'];
        const statusClasses = ['sending', 'received', 'alerting'];

        this.contacts.forEach((contact, index) => {
            setTimeout(() => {
                const row = document.createElement('div');
                row.className = 'sos-contact-status';
                row.innerHTML = `
                    <div class="sos-contact-avatar">${contact.initial}</div>
                    <div class="sos-contact-name">${contact.name}</div>
                    <div class="sos-contact-state sending" id="sosState-${contact.id}">Enviando...</div>
                `;
                list.appendChild(row);

                // Animate through states
                setTimeout(() => {
                    const state = document.getElementById(`sosState-${contact.id}`);
                    if (state) {
                        state.textContent = '&#9989; Recibido';
                        state.className = 'sos-contact-state received';
                    }
                }, 600 + Math.random() * 800);

                setTimeout(() => {
                    const state = document.getElementById(`sosState-${contact.id}`);
                    if (state) {
                        state.innerHTML = '&#128266; Alerta sonando';
                        state.className = 'sos-contact-state alerting';
                    }
                }, 1500 + Math.random() * 1000);

                // Show "watching stream" state
                setTimeout(() => {
                    const state = document.getElementById(`sosState-${contact.id}`);
                    if (state) {
                        state.innerHTML = '&#128064; Viendo stream';
                        state.className = 'sos-contact-state watching';
                    }
                }, 3000 + Math.random() * 1500);

            }, index * 400);
        });
    },

    // Live camera/mic streaming
    async startLiveStream() {
        const video = document.getElementById('sosVideoElement');
        const fallback = document.getElementById('sosCameraFallback');

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } },
                audio: true
            });
            this.liveStream = stream;

            if (video) {
                video.srcObject = stream;
                video.style.display = 'block';
                if (fallback) fallback.style.display = 'none';
            }

            // Animate audio bars based on real mic input
            const audioCtxStream = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioCtxStream.createMediaStreamSource(stream);
            const analyser = audioCtxStream.createAnalyser();
            analyser.fftSize = 64;
            source.connect(analyser);
            this.streamAnalyser = analyser;
            this.streamAudioCtx = audioCtxStream;
            this.animateAudioBars();

        } catch (e) {
            // Camera not available — show animated fallback
            if (fallback) {
                fallback.innerHTML = `
                    <div class="sos-camera-icon">&#127909;</div>
                    <div>Camara simulada</div>
                    <div class="sos-camera-simulated-feed"></div>
                `;
            }
            // Animate audio bars with random data
            this.animateAudioBars();
        }

        // Simulate viewer count increasing
        this.viewerInterval = setInterval(() => {
            const el = document.getElementById('sosViewerCount');
            if (!el) return;
            const current = parseInt(el.textContent) || 0;
            if (current < this.contacts.length) {
                el.textContent = `${current + 1} viendo`;
            }
        }, 1500);
    },

    stopLiveStream() {
        // Stop camera/mic tracks
        if (this.liveStream) {
            this.liveStream.getTracks().forEach(track => track.stop());
            this.liveStream = null;
        }
        if (this.streamAudioCtx) {
            this.streamAudioCtx.close();
            this.streamAudioCtx = null;
        }
        this.streamAnalyser = null;

        if (this.audioBarsInterval) {
            cancelAnimationFrame(this.audioBarsInterval);
            this.audioBarsInterval = null;
        }
        if (this.viewerInterval) {
            clearInterval(this.viewerInterval);
            this.viewerInterval = null;
        }
    },

    animateAudioBars() {
        const bars = document.querySelectorAll('.sos-audio-bar');
        if (!bars.length) return;

        const analyser = this.streamAnalyser;

        const update = () => {
            if (!this.emergencyActive && !this.viewingSOSStream) return;

            if (analyser) {
                const data = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(data);
                bars.forEach((bar, i) => {
                    const value = data[i * 2] || 0;
                    bar.style.height = Math.max(4, (value / 255) * 28) + 'px';
                });
            } else {
                // Random animation when no real audio
                bars.forEach(bar => {
                    bar.style.height = (4 + Math.random() * 24) + 'px';
                });
            }
            this.audioBarsInterval = requestAnimationFrame(update);
        };
        update();
    },

    // SOS Viewer — what contacts see when they tap the emergency notification
    viewingSOSStream: false,

    openSOSViewer(senderName, senderInitial) {
        this.viewingSOSStream = true;
        const screen = document.getElementById('screen');

        const viewer = document.createElement('div');
        viewer.className = 'sos-viewer-overlay';
        viewer.id = 'sosViewer';
        viewer.innerHTML = `
            <div class="sos-viewer-header">
                <button class="sos-viewer-close" onclick="app.closeSOSViewer()">&#10005;</button>
                <div class="sos-viewer-sender">
                    <div class="sos-viewer-avatar">${senderInitial}</div>
                    <div>
                        <div class="sos-viewer-name">${senderName}</div>
                        <div class="sos-viewer-status">&#9679; Emergencia activa</div>
                    </div>
                </div>
                <div class="sos-viewer-rec">&#9679; EN VIVO</div>
            </div>

            <div class="sos-viewer-video">
                <div class="sos-viewer-simulated-cam">
                    <div class="sos-viewer-cam-text">&#127909;</div>
                    <div class="sos-viewer-cam-label">Transmision en vivo de ${senderName}</div>
                    <div class="sos-viewer-cam-wave"></div>
                    <div class="sos-viewer-cam-wave delay"></div>
                </div>
                <div class="sos-camera-overlay-badge">
                    <span>&#128274; Encriptado E2E</span>
                </div>
            </div>

            <div class="sos-viewer-bottom">
                <div class="sos-viewer-audio-section">
                    <div class="sos-mic-icon">&#127908;</div>
                    <div class="sos-audio-bars" id="sosViewerAudioBars">
                        <div class="sos-audio-bar" style="height:8px"></div>
                        <div class="sos-audio-bar" style="height:14px"></div>
                        <div class="sos-audio-bar" style="height:20px"></div>
                        <div class="sos-audio-bar" style="height:12px"></div>
                        <div class="sos-audio-bar" style="height:18px"></div>
                        <div class="sos-audio-bar" style="height:10px"></div>
                        <div class="sos-audio-bar" style="height:16px"></div>
                        <div class="sos-audio-bar" style="height:8px"></div>
                    </div>
                    <div class="sos-audio-label">Audio en vivo</div>
                </div>

                <div class="sos-viewer-location">
                    <div class="sos-location-icon">&#128205;</div>
                    <div class="sos-viewer-loc-text">
                        <div>Ubicacion en tiempo real</div>
                        <div class="sos-location-coords">19.4326° N, 99.1332° W</div>
                    </div>
                    <div class="sos-location-live">EN VIVO</div>
                </div>

                <div class="sos-viewer-actions">
                    <button class="sos-viewer-action-btn call" onclick="app.showToast('&#128222; Llamando a ${senderName}...')">
                        &#128222; Llamar
                    </button>
                    <button class="sos-viewer-action-btn emergency" onclick="app.showToast('&#128659; Llamando al 911...')">
                        &#128680; 911
                    </button>
                </div>
            </div>
        `;
        screen.appendChild(viewer);

        // Animate viewer audio bars
        this.animateViewerAudioBars();
    },

    animateViewerAudioBars() {
        const bars = document.querySelectorAll('#sosViewerAudioBars .sos-audio-bar');
        if (!bars.length) return;

        const update = () => {
            if (!this.viewingSOSStream) return;
            bars.forEach(bar => {
                bar.style.height = (4 + Math.random() * 24) + 'px';
            });
            requestAnimationFrame(update);
        };
        update();
    },

    closeSOSViewer() {
        this.viewingSOSStream = false;
        const viewer = document.getElementById('sosViewer');
        if (viewer) {
            viewer.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => viewer.remove(), 300);
        }
    },

    playAlarmSound() {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            this.audioCtx = audioCtx;

            const playTone = (freq, startTime, duration) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.frequency.value = freq;
                osc.type = 'square';
                gain.gain.value = 0.15;
                gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
                osc.start(startTime);
                osc.stop(startTime + duration);
            };

            // Siren pattern: alternating high/low tones
            const now = audioCtx.currentTime;
            for (let i = 0; i < 8; i++) {
                playTone(880, now + i * 0.5, 0.25);
                playTone(660, now + i * 0.5 + 0.25, 0.25);
            }
        } catch (e) {
            // Audio not supported, visual only
        }
    },

    stopEmergency() {
        this.emergencyActive = false;

        // Stop live stream
        this.stopLiveStream();

        // Stop timer
        if (this.emergencyTimerInterval) {
            clearInterval(this.emergencyTimerInterval);
            this.emergencyTimerInterval = null;
        }

        // Stop audio
        if (this.audioCtx) {
            this.audioCtx.close();
            this.audioCtx = null;
        }

        // Remove overlay
        const overlay = document.getElementById('sosOverlay');
        if (overlay) {
            overlay.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => overlay.remove(), 300);
        }

        this.showToast('&#9989; Alerta de emergencia desactivada');

        // Add emergency message to all conversations
        const now = new Date();
        const time = now.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', hour12: true });
        this.conversations.forEach(conv => {
            conv.messages.push({
                text: '&#9888;&#65039; ALERTA DE EMERGENCIA finalizada. Todos los contactos fueron notificados.',
                sent: true,
                time: time,
                isSystem: true
            });
        });
    },

    // Toast
    showToast(message) {
        const screen = document.getElementById('screen');
        const existing = screen.querySelector('.toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = message;
        screen.appendChild(toast);

        setTimeout(() => toast.remove(), 3000);
    }
};

// Boot
document.addEventListener('DOMContentLoaded', () => app.init());
