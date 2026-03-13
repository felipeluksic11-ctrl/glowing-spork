// SOS Alert v2 - Emergency Button App
const app = {
    currentScreen: 'login',
    isAuthenticated: false,
    currentUser: { name: 'Felipe', username: 'felipesolar', email: 'felipe@email.com' },
    currentTab: 0, // 0=SOS, 1=Contacts, 2=Settings

    contacts: [
        { id: 1, name: 'Maria Garcia', username: 'mariagarcia', initial: 'M', phone: '+52 555 1234' },
        { id: 2, name: 'Carlos Lopez', username: 'carloslopez', initial: 'C', phone: '+52 555 5678' },
        { id: 3, name: 'Ana Martinez', username: 'anamartinez', initial: 'A', phone: '+52 555 9012' },
    ],

    emergencyActive: false,
    holdTimer: null,
    holdProgress: 0,
    holdInterval: null,
    emergencyStartTime: null,
    emergencyTimerInterval: null,
    audioCtx: null,
    liveStream: null,
    streamAnalyser: null,
    streamAudioCtx: null,
    audioBarsInterval: null,
    viewerInterval: null,
    viewingSOSStream: false,

    // Settings
    driveUrl: '',
    autoRecord: true,
    showAddContact: false,
    newContactForm: { name: '', username: '', phone: '', email: '' },
    formError: '',
    confirmDeleteContact: null,

    init() {
        this.render();
    },

    reset() {
        this.stopEmergency();
        this.isAuthenticated = false;
        this.currentScreen = 'login';
        this.currentTab = 0;
        this.emergencyActive = false;
        this.holdProgress = 0;
        this.showAddContact = false;
        this.confirmDeleteContact = null;
        this.driveUrl = '';
        this.contacts = [
            { id: 1, name: 'Maria Garcia', username: 'mariagarcia', initial: 'M', phone: '+52 555 1234' },
            { id: 2, name: 'Carlos Lopez', username: 'carloslopez', initial: 'C', phone: '+52 555 5678' },
            { id: 3, name: 'Ana Martinez', username: 'anamartinez', initial: 'A', phone: '+52 555 9012' },
        ];
        this.render();
    },

    // ==================
    // RENDER
    // ==================
    render() {
        const screen = document.getElementById('screen');
        if (!this.isAuthenticated) {
            if (this.currentScreen === 'signup') {
                screen.innerHTML = this.renderSignUp();
            } else {
                screen.innerHTML = this.renderLogin();
            }
        } else if (this.showAddContact) {
            screen.innerHTML = this.renderAddContactScreen();
        } else {
            screen.innerHTML = this.renderMainTabs();
        }
    },

    renderStatusBar() {
        const now = new Date();
        const time = now.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', hour12: false });
        return `
            <div class="status-bar">
                <span>${time}</span>
                <span>&#9679;&#9679;&#9679;&#9679; WiFi &#128267;</span>
            </div>
        `;
    },

    // ==================
    // AUTH
    // ==================
    renderLogin() {
        return `
            <div class="login-screen">
                ${this.renderStatusBar()}
                <div class="login-logo">&#128680;</div>
                <div class="login-title">SOS Alert</div>
                <div class="login-subtitle">Tu boton de emergencia</div>
                <input class="input-field" type="email" placeholder="Email" value="felipe@email.com">
                <input class="input-field" type="password" placeholder="Contrasena" value="••••••••">
                <button class="btn-primary btn-red" onclick="app.handleLogin()">Iniciar Sesion</button>
                <button class="btn-link" onclick="app.currentScreen='signup'; app.render();">Crear cuenta</button>
            </div>
        `;
    },

    renderSignUp() {
        return `
            <div class="login-screen">
                ${this.renderStatusBar()}
                <div class="login-logo" style="font-size:50px;">&#128680;</div>
                <div class="login-title">Crear Cuenta</div>
                <div class="login-subtitle">Configura tu boton de emergencia</div>
                <input class="input-field" placeholder="Nombre completo" value="Felipe Solar">
                <input class="input-field" placeholder="Nombre de usuario" value="felipesolar">
                <input class="input-field" type="email" placeholder="Email" value="felipe@email.com">
                <input class="input-field" type="password" placeholder="Contrasena (min 6 caracteres)">
                <button class="btn-primary btn-red" onclick="app.handleLogin()">Registrarse</button>
                <button class="btn-link" onclick="app.currentScreen='login'; app.render();">Ya tengo cuenta</button>
            </div>
        `;
    },

    handleLogin() {
        const screen = document.getElementById('screen');
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-icon">&#128680;</div>
            <div class="loading-text">Configurando permisos...</div>
            <div class="loading-bar"><div class="loading-bar-fill"></div></div>
            <div class="loading-detail">Camara, microfono, ubicacion, notificaciones</div>
        `;
        screen.appendChild(overlay);

        setTimeout(() => {
            this.isAuthenticated = true;
            this.currentScreen = 'main';
            this.render();
            this.showToast('&#9989; SOS Alert configurado');
        }, 2000);
    },

    // ==================
    // MAIN TABS
    // ==================
    renderMainTabs() {
        let content = '';
        if (this.currentTab === 0) content = this.renderSOSScreen();
        else if (this.currentTab === 1) content = this.renderContactsList();
        else content = this.renderSettings();

        return `
            ${this.renderStatusBar()}
            ${content}
            <div class="tab-bar">
                <button class="tab-item ${this.currentTab === 0 ? 'active' : ''}" onclick="app.switchTab(0)">
                    <span class="tab-icon">&#128680;</span>
                    <span class="tab-label">SOS</span>
                </button>
                <button class="tab-item ${this.currentTab === 1 ? 'active' : ''}" onclick="app.switchTab(1)">
                    <span class="tab-icon">&#128101;</span>
                    <span class="tab-label">Contactos</span>
                </button>
                <button class="tab-item ${this.currentTab === 2 ? 'active' : ''}" onclick="app.switchTab(2)">
                    <span class="tab-icon">&#9881;</span>
                    <span class="tab-label">Ajustes</span>
                </button>
            </div>
        `;
    },

    switchTab(tab) {
        this.currentTab = tab;
        this.showAddContact = false;
        this.confirmDeleteContact = null;
        this.render();
    },

    // ==================
    // SOS MAIN SCREEN
    // ==================
    renderSOSScreen() {
        return `
            <div class="sos-screen">
                <div class="sos-header-text">Manten presionado para activar</div>

                <div class="sos-button-container">
                    <div class="sos-ring ring-3"></div>
                    <div class="sos-ring ring-2"></div>
                    <div class="sos-ring ring-1"></div>
                    <button class="sos-big-button" id="sosButton"
                        onmousedown="app.startHold()"
                        onmouseup="app.cancelHold()"
                        onmouseleave="app.cancelHold()"
                        ontouchstart="app.startHold(); event.preventDefault();"
                        ontouchend="app.cancelHold()"
                        ontouchcancel="app.cancelHold()">
                        <div class="sos-button-text">SOS</div>
                        <div class="sos-button-sub">Manten 5 seg</div>
                    </button>
                    <svg class="sos-progress-ring" id="sosProgressRing" viewBox="0 0 200 200">
                        <circle cx="100" cy="100" r="90" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="6"/>
                        <circle id="sosProgressCircle" cx="100" cy="100" r="90" fill="none" stroke="#FF3B30" stroke-width="6"
                            stroke-dasharray="565.48" stroke-dashoffset="565.48" stroke-linecap="round"
                            transform="rotate(-90 100 100)"/>
                    </svg>
                </div>

                <div class="sos-info-cards">
                    <div class="sos-info-card">
                        <span class="sos-info-icon">&#128101;</span>
                        <span class="sos-info-text">${this.contacts.length} contactos configurados</span>
                    </div>
                    <div class="sos-info-card">
                        <span class="sos-info-icon">&#127909;</span>
                        <span class="sos-info-text">Video + audio se grabaran</span>
                    </div>
                    <div class="sos-info-card">
                        <span class="sos-info-icon">&#128205;</span>
                        <span class="sos-info-text">Ubicacion en tiempo real</span>
                    </div>
                    ${this.driveUrl ? `
                    <div class="sos-info-card drive-configured">
                        <span class="sos-info-icon">&#9729;&#65039;</span>
                        <span class="sos-info-text">Drive configurado</span>
                    </div>
                    ` : `
                    <div class="sos-info-card drive-warning" onclick="app.switchTab(2)">
                        <span class="sos-info-icon">&#9888;&#65039;</span>
                        <span class="sos-info-text">Configura tu Drive en Ajustes</span>
                    </div>
                    `}
                </div>
            </div>
        `;
    },

    // ==================
    // HOLD TO ACTIVATE
    // ==================
    startHold() {
        if (this.emergencyActive) return;
        this.holdProgress = 0;
        const totalDuration = 5000; // 5 seconds
        const interval = 30; // update every 30ms

        const circle = document.getElementById('sosProgressCircle');
        const button = document.getElementById('sosButton');
        const circumference = 565.48;

        if (button) button.classList.add('holding');

        // Haptic-style visual feedback
        this.holdInterval = setInterval(() => {
            this.holdProgress += interval;
            const progress = Math.min(this.holdProgress / totalDuration, 1);

            if (circle) {
                circle.style.strokeDashoffset = circumference * (1 - progress);
            }

            // Color transition: darker red as progress increases
            if (button) {
                const intensity = Math.floor(progress * 100);
                button.style.boxShadow = `0 0 ${20 + intensity * 0.6}px ${10 + intensity * 0.3}px rgba(255, 59, 48, ${0.3 + progress * 0.5})`;
            }

            // Countdown text
            const remaining = Math.ceil((totalDuration - this.holdProgress) / 1000);
            const subText = button?.querySelector('.sos-button-sub');
            if (subText && remaining > 0) {
                subText.textContent = `${remaining}...`;
            }

            if (this.holdProgress >= totalDuration) {
                clearInterval(this.holdInterval);
                this.holdInterval = null;
                this.executeEmergency();
            }
        }, interval);
    },

    cancelHold() {
        if (this.holdInterval) {
            clearInterval(this.holdInterval);
            this.holdInterval = null;
        }
        this.holdProgress = 0;

        const circle = document.getElementById('sosProgressCircle');
        const button = document.getElementById('sosButton');

        if (circle) circle.style.strokeDashoffset = '565.48';
        if (button) {
            button.classList.remove('holding');
            button.style.boxShadow = '';
            const subText = button.querySelector('.sos-button-sub');
            if (subText) subText.textContent = 'Manten 5 seg';
        }
    },

    // ==================
    // EMERGENCY ACTIVE
    // ==================
    executeEmergency() {
        this.emergencyActive = true;
        this.playAlarmSound();

        const screen = document.getElementById('screen');
        const overlay = document.createElement('div');
        overlay.className = 'emergency-overlay';
        overlay.id = 'emergencyOverlay';
        overlay.innerHTML = `
            <div class="emergency-flash"></div>
            <div class="emergency-content">
                <div class="emergency-top-bar">
                    <div class="emergency-rec-badge">&#9679; REC</div>
                    <div class="emergency-timer" id="emergencyTimer">00:00</div>
                    <div class="emergency-viewers" id="emergencyViewers">0 viendo</div>
                </div>

                <div class="emergency-camera-box" id="emergencyCameraBox">
                    <video id="emergencyVideo" autoplay playsinline muted></video>
                    <div class="emergency-camera-fallback" id="emergencyCameraFallback">
                        <div class="emergency-cam-icon">&#127909;</div>
                        <div>Iniciando camara...</div>
                    </div>
                    <div class="emergency-camera-badge">&#128274; E2E</div>
                    ${this.driveUrl ? '<div class="emergency-drive-badge">&#9729;&#65039; Guardando en Drive</div>' : ''}
                </div>

                <div class="emergency-audio-bar">
                    <div class="emergency-mic-icon">&#127908;</div>
                    <div class="emergency-audio-bars" id="emergencyAudioBars">
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                    </div>
                    <div class="emergency-audio-label">Microfono activo</div>
                </div>

                <div class="emergency-siren">&#128680;</div>
                <div class="emergency-title">EMERGENCIA ACTIVA</div>

                <div class="emergency-status-list" id="emergencyStatusList">
                    <!-- Contact notifications populated here -->
                </div>

                <div class="emergency-location-box">
                    <div class="emergency-loc-icon">&#128205;</div>
                    <div class="emergency-loc-text">
                        <div>Ubicacion compartida</div>
                        <div class="emergency-loc-coords">19.4326° N, 99.1332° W</div>
                    </div>
                    <div class="emergency-loc-live">EN VIVO</div>
                </div>

                <button class="emergency-stop-btn" onclick="app.stopEmergency()">
                    Detener Emergencia
                </button>

                <button class="emergency-viewer-btn" onclick="app.openViewer('${this.currentUser.name}', 'F')">
                    &#128064; Ver como receptor
                </button>
            </div>
        `;
        screen.appendChild(overlay);

        // Start systems
        this.startLiveStream();
        this.animateContactNotifications();
        this.startEmergencyTimer();
    },

    startEmergencyTimer() {
        this.emergencyStartTime = Date.now();
        this.emergencyTimerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.emergencyStartTime) / 1000);
            const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const secs = String(elapsed % 60).padStart(2, '0');
            const timer = document.getElementById('emergencyTimer');
            if (timer) timer.textContent = `${mins}:${secs}`;
        }, 1000);
    },

    animateContactNotifications() {
        const list = document.getElementById('emergencyStatusList');
        if (!list) return;

        this.contacts.forEach((contact, index) => {
            setTimeout(() => {
                const row = document.createElement('div');
                row.className = 'emergency-contact-row';
                row.innerHTML = `
                    <div class="emergency-contact-avatar">${contact.initial}</div>
                    <div class="emergency-contact-info">
                        <div class="emergency-contact-name">${contact.name}</div>
                        <div class="emergency-contact-phone">${contact.phone || ''}</div>
                    </div>
                    <div class="emergency-contact-state sending" id="eState-${contact.id}">Enviando...</div>
                `;
                list.appendChild(row);

                setTimeout(() => {
                    const state = document.getElementById(`eState-${contact.id}`);
                    if (state) { state.textContent = 'Recibido'; state.className = 'emergency-contact-state received'; }
                }, 600 + Math.random() * 800);

                setTimeout(() => {
                    const state = document.getElementById(`eState-${contact.id}`);
                    if (state) { state.innerHTML = '&#128266; Alerta'; state.className = 'emergency-contact-state alerting'; }
                }, 1500 + Math.random() * 1000);

                setTimeout(() => {
                    const state = document.getElementById(`eState-${contact.id}`);
                    if (state) { state.innerHTML = '&#128064; Viendo'; state.className = 'emergency-contact-state watching'; }
                }, 3000 + Math.random() * 1500);

            }, index * 500);
        });
    },

    // ==================
    // LIVE STREAM
    // ==================
    async startLiveStream() {
        const video = document.getElementById('emergencyVideo');
        const fallback = document.getElementById('emergencyCameraFallback');

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

            const audioCtxStream = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioCtxStream.createMediaStreamSource(stream);
            const analyser = audioCtxStream.createAnalyser();
            analyser.fftSize = 64;
            source.connect(analyser);
            this.streamAnalyser = analyser;
            this.streamAudioCtx = audioCtxStream;
            this.animateAudioBars();

        } catch (e) {
            if (fallback) {
                fallback.innerHTML = `
                    <div class="emergency-cam-icon">&#127909;</div>
                    <div>Camara simulada</div>
                    <div class="emergency-simulated-feed"></div>
                `;
            }
            this.animateAudioBars();
        }

        // Simulate viewer count
        this.viewerInterval = setInterval(() => {
            const el = document.getElementById('emergencyViewers');
            if (!el) return;
            const current = parseInt(el.textContent) || 0;
            if (current < this.contacts.length) {
                el.textContent = `${current + 1} viendo`;
            }
        }, 1800);
    },

    stopLiveStream() {
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
        const barsContainer = document.getElementById('emergencyAudioBars') ||
                              document.getElementById('viewerAudioBars');
        if (!barsContainer) return;
        const bars = barsContainer.querySelectorAll('.e-audio-bar');
        if (!bars.length) return;

        const analyser = this.streamAnalyser;

        const update = () => {
            if (!this.emergencyActive && !this.viewingSOSStream) return;

            if (analyser) {
                const data = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(data);
                bars.forEach((bar, i) => {
                    const value = data[i * 2] || 0;
                    bar.style.height = Math.max(3, (value / 255) * 32) + 'px';
                });
            } else {
                bars.forEach(bar => {
                    bar.style.height = (3 + Math.random() * 28) + 'px';
                });
            }
            this.audioBarsInterval = requestAnimationFrame(update);
        };
        update();
    },

    // ==================
    // ALARM SOUND
    // ==================
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
                gain.gain.value = 0.12;
                gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
                osc.start(startTime);
                osc.stop(startTime + duration);
            };

            const now = audioCtx.currentTime;
            for (let i = 0; i < 10; i++) {
                playTone(880, now + i * 0.5, 0.25);
                playTone(660, now + i * 0.5 + 0.25, 0.25);
            }
        } catch (e) {}
    },

    // ==================
    // STOP EMERGENCY
    // ==================
    stopEmergency() {
        if (!this.emergencyActive) return;
        this.emergencyActive = false;

        this.stopLiveStream();

        if (this.emergencyTimerInterval) {
            clearInterval(this.emergencyTimerInterval);
            this.emergencyTimerInterval = null;
        }
        if (this.audioCtx) {
            this.audioCtx.close();
            this.audioCtx = null;
        }

        const overlay = document.getElementById('emergencyOverlay');
        if (overlay) {
            overlay.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => { overlay.remove(); this.render(); }, 300);
        }

        // Also close viewer if open
        this.closeViewer();

        this.showToast('&#9989; Emergencia desactivada');
    },

    // ==================
    // VIEWER (what contacts see)
    // ==================
    openViewer(senderName, senderInitial) {
        this.viewingSOSStream = true;
        const screen = document.getElementById('screen');

        const viewer = document.createElement('div');
        viewer.className = 'viewer-overlay';
        viewer.id = 'viewerOverlay';
        viewer.innerHTML = `
            <div class="viewer-header">
                <button class="viewer-close" onclick="app.closeViewer()">&#10005;</button>
                <div class="viewer-sender-info">
                    <div class="viewer-avatar">${senderInitial}</div>
                    <div>
                        <div class="viewer-name">${senderName}</div>
                        <div class="viewer-status">&#9679; Emergencia activa</div>
                    </div>
                </div>
                <div class="viewer-live-badge">&#9679; EN VIVO</div>
            </div>

            <div class="viewer-video-area">
                <div class="viewer-simulated-video">
                    <div class="viewer-cam-emoji">&#127909;</div>
                    <div class="viewer-cam-label">Transmision en vivo de ${senderName}</div>
                    <div class="viewer-wave"></div>
                    <div class="viewer-wave delay2"></div>
                    <div class="viewer-wave delay3"></div>
                </div>
                <div class="viewer-e2e-badge">&#128274; Encriptado E2E</div>
            </div>

            <div class="viewer-bottom">
                <div class="viewer-audio-section">
                    <div class="viewer-mic">&#127908;</div>
                    <div class="viewer-audio-bars" id="viewerAudioBars">
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                        <div class="e-audio-bar"></div>
                    </div>
                    <div class="viewer-audio-label">Audio en vivo</div>
                </div>

                <div class="viewer-location">
                    <div class="viewer-loc-icon">&#128205;</div>
                    <div class="viewer-loc-text">
                        <div>Ubicacion en tiempo real</div>
                        <div class="viewer-loc-coords">19.4326° N, 99.1332° W</div>
                    </div>
                    <div class="viewer-loc-live">EN VIVO</div>
                </div>

                <div class="viewer-actions">
                    <button class="viewer-action-btn call-btn" onclick="app.showToast('&#128222; Llamando a ${senderName}...')">
                        &#128222; Llamar
                    </button>
                    <button class="viewer-action-btn emergency-btn" onclick="app.showToast('&#128659; Llamando al 911...')">
                        &#128680; 911
                    </button>
                </div>
            </div>
        `;
        screen.appendChild(viewer);
        this.animateViewerAudioBars();
    },

    animateViewerAudioBars() {
        const bars = document.querySelectorAll('#viewerAudioBars .e-audio-bar');
        if (!bars.length) return;
        const update = () => {
            if (!this.viewingSOSStream) return;
            bars.forEach(bar => {
                bar.style.height = (3 + Math.random() * 28) + 'px';
            });
            requestAnimationFrame(update);
        };
        update();
    },

    closeViewer() {
        this.viewingSOSStream = false;
        const viewer = document.getElementById('viewerOverlay');
        if (viewer) {
            viewer.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => viewer.remove(), 300);
        }
    },

    // ==================
    // CONTACTS
    // ==================
    renderContactsList() {
        if (this.showAddContact) return this.renderAddContactScreen();

        const rows = this.contacts.length > 0 ? this.contacts.map(c => `
            <div class="contact-row" id="contact-row-${c.id}">
                <div class="contact-avatar">${c.initial}</div>
                <div class="contact-info">
                    <div class="contact-name">${c.name}</div>
                    <div class="contact-detail">@${c.username}${c.phone ? ' · ' + c.phone : ''}</div>
                </div>
                <button class="contact-delete-btn" onclick="app.confirmDelete(${c.id})">&#128465;</button>
            </div>
            ${this.confirmDeleteContact === c.id ? `
                <div class="delete-bar">
                    <span>Eliminar a ${c.name}?</span>
                    <div class="delete-bar-actions">
                        <button class="delete-cancel" onclick="app.confirmDeleteContact=null; app.render();">Cancelar</button>
                        <button class="delete-yes" onclick="app.deleteContact(${c.id})">Eliminar</button>
                    </div>
                </div>
            ` : ''}
        `).join('') : `
            <div class="empty-state">
                <div class="empty-icon">&#128101;</div>
                <div class="empty-title">Sin contactos</div>
                <div class="empty-text">Agrega contactos que seran notificados en una emergencia</div>
            </div>
        `;

        return `
            <div class="nav-bar">
                <div class="nav-title">Contactos de Emergencia</div>
                <button class="nav-add-btn" onclick="app.openAddContact()">+</button>
            </div>
            <div class="screen-content">
                <div class="contacts-header">
                    <span>${this.contacts.length} contacto${this.contacts.length !== 1 ? 's' : ''}</span>
                    <span class="contacts-header-note">Seran alertados al activar SOS</span>
                </div>
                ${rows}
            </div>
        `;
    },

    openAddContact() {
        this.showAddContact = true;
        this.newContactForm = { name: '', username: '', phone: '', email: '' };
        this.formError = '';
        this.render();
        setTimeout(() => { const el = document.getElementById('formName'); if (el) el.focus(); }, 100);
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
            <div class="form-container">
                ${this.renderStatusBar()}
                <div class="form-nav">
                    <button class="form-nav-btn" onclick="app.closeAddContact()">Cancelar</button>
                    <span class="form-nav-title">Nuevo Contacto</span>
                    <button class="form-nav-btn save" onclick="app.saveContact()">Guardar</button>
                </div>
                <div class="screen-content" style="padding:0;">
                    <div class="form-avatar-section">
                        <div class="form-avatar-big">
                            ${f.name.trim() ? f.name.trim().charAt(0).toUpperCase() : '&#128100;'}
                        </div>
                    </div>

                    <div class="form-section">
                        <div class="form-section-label">INFORMACION</div>
                        <div class="form-group">
                            <div class="form-row">
                                <label class="form-label">Nombre *</label>
                                <input class="form-input" id="formName" placeholder="Nombre completo"
                                    value="${this.escapeHtml(f.name)}"
                                    oninput="app.updateForm('name', this.value)">
                            </div>
                            <div class="form-divider"></div>
                            <div class="form-row">
                                <label class="form-label">Username *</label>
                                <input class="form-input" id="formUsername" placeholder="nombre_usuario"
                                    value="${this.escapeHtml(f.username)}"
                                    oninput="app.updateForm('username', this.value)">
                            </div>
                            <div class="form-divider"></div>
                            <div class="form-row">
                                <label class="form-label">Telefono</label>
                                <input class="form-input" id="formPhone" placeholder="+52 555 123 4567" type="tel"
                                    value="${this.escapeHtml(f.phone)}"
                                    oninput="app.updateForm('phone', this.value)">
                            </div>
                            <div class="form-divider"></div>
                            <div class="form-row">
                                <label class="form-label">Email</label>
                                <input class="form-input" id="formEmail" placeholder="correo@ejemplo.com" type="email"
                                    value="${this.escapeHtml(f.email)}"
                                    oninput="app.updateForm('email', this.value)">
                            </div>
                        </div>
                    </div>

                    ${this.formError ? `<div class="form-error">${this.formError}</div>` : ''}

                    <div class="form-section">
                        <div class="form-section-label">EMERGENCIA</div>
                        <div class="form-group">
                            <div class="form-info-row">
                                <span class="form-info-icon">&#128680;</span>
                                <span class="form-info-text">Este contacto recibira alertas inmediatas con tu ubicacion, video y audio en vivo cuando actives el SOS.</span>
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

    updateForm(field, value) {
        this.newContactForm[field] = value;
        this.formError = '';
        const avatar = document.querySelector('.form-avatar-big');
        if (avatar && field === 'name') {
            avatar.textContent = value.trim() ? value.trim().charAt(0).toUpperCase() : '';
            if (!value.trim()) avatar.innerHTML = '&#128100;';
        }
    },

    saveContact() {
        const f = this.newContactForm;
        const name = f.name.trim();
        const username = f.username.trim().toLowerCase().replace(/\s/g, '_');

        if (!name) { this.formError = 'El nombre es obligatorio'; this.render(); return; }
        if (!username || username.length < 3) { this.formError = 'Username debe tener al menos 3 caracteres'; this.render(); return; }
        if (this.contacts.find(c => c.username === username)) { this.formError = `Ya existe "@${username}"`; this.render(); return; }

        this.contacts.push({
            id: Date.now(),
            name: name,
            username: username,
            initial: name.charAt(0).toUpperCase(),
            phone: f.phone.trim() || null,
            email: f.email.trim() || null,
        });

        this.showAddContact = false;
        this.newContactForm = { name: '', username: '', phone: '', email: '' };
        this.formError = '';
        this.render();
        this.showToast(`&#9989; ${name} agregado`);
    },

    confirmDelete(id) {
        this.confirmDeleteContact = id;
        this.render();
    },

    deleteContact(id) {
        const contact = this.contacts.find(c => c.id === id);
        const name = contact ? contact.name : 'Contacto';
        this.contacts = this.contacts.filter(c => c.id !== id);
        this.confirmDeleteContact = null;
        this.render();
        this.showToast(`&#128465; ${name} eliminado`);
    },

    // ==================
    // SETTINGS
    // ==================
    renderSettings() {
        return `
            <div class="nav-bar">
                <div class="nav-title">Ajustes</div>
            </div>
            <div class="screen-content">
                <div class="settings-profile">
                    <div class="settings-avatar">F</div>
                    <div>
                        <div class="settings-name">${this.currentUser.name}</div>
                        <div class="settings-username">@${this.currentUser.username}</div>
                    </div>
                </div>

                <div class="settings-section">
                    <div class="settings-section-title">ALMACENAMIENTO DE VIDEO</div>
                    <div class="settings-group">
                        <div class="settings-row">
                            <span class="settings-row-icon">&#9729;&#65039;</span>
                            <div class="settings-row-content">
                                <div class="settings-row-label">URL de Google Drive</div>
                                <input class="settings-input" id="driveUrlInput"
                                    placeholder="https://drive.google.com/..."
                                    value="${this.escapeHtml(this.driveUrl)}"
                                    oninput="app.driveUrl = this.value.trim();"
                                    onblur="app.saveDriveUrl()">
                            </div>
                        </div>
                        <div class="settings-divider"></div>
                        <div class="settings-row">
                            <span class="settings-row-icon">&#127909;</span>
                            <span class="settings-row-label" style="flex:1;">Grabar automaticamente</span>
                            <div class="settings-toggle ${this.autoRecord ? 'on' : ''}" onclick="app.autoRecord=!app.autoRecord; app.render();">
                                <div class="settings-toggle-knob"></div>
                            </div>
                        </div>
                    </div>
                    <div class="settings-footer-note">
                        El video y audio de emergencia se guardaran encriptados en tu Google Drive. Configura la URL de la carpeta compartida donde quieres almacenar las grabaciones.
                    </div>
                </div>

                <div class="settings-section">
                    <div class="settings-section-title">PERMISOS</div>
                    <div class="settings-group">
                        <div class="settings-row">
                            <span class="settings-row-icon">&#128247;</span>
                            <span class="settings-row-label" style="flex:1;">Camara</span>
                            <span class="settings-row-status granted">Concedido</span>
                        </div>
                        <div class="settings-divider"></div>
                        <div class="settings-row">
                            <span class="settings-row-icon">&#127908;</span>
                            <span class="settings-row-label" style="flex:1;">Microfono</span>
                            <span class="settings-row-status granted">Concedido</span>
                        </div>
                        <div class="settings-divider"></div>
                        <div class="settings-row">
                            <span class="settings-row-icon">&#128205;</span>
                            <span class="settings-row-label" style="flex:1;">Ubicacion</span>
                            <span class="settings-row-status granted">Siempre</span>
                        </div>
                        <div class="settings-divider"></div>
                        <div class="settings-row">
                            <span class="settings-row-icon">&#128276;</span>
                            <span class="settings-row-label" style="flex:1;">Notificaciones</span>
                            <span class="settings-row-status granted">Criticas</span>
                        </div>
                    </div>
                </div>

                <div class="settings-section">
                    <div class="settings-section-title">CUENTA</div>
                    <div class="settings-group">
                        <div class="settings-row">
                            <span class="settings-row-icon">&#9993;</span>
                            <span class="settings-row-label">${this.currentUser.email}</span>
                        </div>
                        <div class="settings-divider"></div>
                        <div class="settings-row clickable" onclick="app.handleSignOut()">
                            <span class="settings-row-icon">&#10145;</span>
                            <span class="settings-row-label danger">Cerrar sesion</span>
                        </div>
                    </div>
                </div>

                <div class="settings-version">SOS Alert v2.0</div>
            </div>
        `;
    },

    saveDriveUrl() {
        if (this.driveUrl) {
            this.showToast('&#9729;&#65039; Drive configurado');
        }
    },

    handleSignOut() {
        this.isAuthenticated = false;
        this.currentScreen = 'login';
        this.render();
    },

    // ==================
    // TOAST
    // ==================
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

document.addEventListener('DOMContentLoaded', () => app.init());
