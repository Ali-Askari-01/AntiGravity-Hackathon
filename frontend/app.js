/**
 * Antigravity Frontend Router & Logic
 * This mimics a Single Page Application (SPA) for Capacitor.js
 */

const app = {
    // Current active screen
    currentScreen: 'splash-screen',
    
    // API Configuration
    apiBase: 'http://127.0.0.1:8000',
    sessionId: null,
    authToken: null,
    currentUser: null,
    selectedProvider: null,
    currentIntent: null,
    currentBooking: null,
    currentRating: 5,
    map: null,
    providerMarker: null,
    userMarker: null,
    routeLine: null,
    ws: null,

    // Helper for API calls with auth token
    async callAPI(endpoint, method = 'POST', data = null) {
        try {
            const options = {
                method: method,
                headers: { 'Content-Type': 'application/json' },
            };
            if (this.authToken) {
                options.headers['Authorization'] = `Bearer ${this.authToken}`;
            }
            if (data) options.body = JSON.stringify(data);
            
            const response = await fetch(`${this.apiBase}${endpoint}`, options);
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || 'API request failed');
            }
            return result;
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    },

    // Initialize the app
    init() {
        console.log("Antigravity App Initialized");
        
        // Check for stored auth token
        const storedToken = localStorage.getItem('authToken');
        const storedUser = localStorage.getItem('currentUser');
        if (storedToken && storedUser) {
            this.authToken = storedToken;
            this.currentUser = JSON.parse(storedUser);
            this.updateUserGreeting();
        }
        
        // Auto-hide splash screen after 2.5 seconds
        setTimeout(() => {
            if (this.authToken) {
                this.navigate('home-screen');
                this.loadRecentBookings();
                this.loadAnalytics();
                this.loadNotifications();
            } else {
                this.navigate('auth-screen');
            }
        }, 2500);

        // Bind Enter key on chat input
        const chatInput = document.getElementById('chat-input');
        if(chatInput) {
            chatInput.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') {
                    app.sendMessage();
                }
            });
        }
    },

    // Toggle between login and register forms
    toggleAuthForm(form) {
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        
        if (form === 'register') {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
        } else {
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
        }
    },

    // Login with email and password
    async login() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        const loginBtn = document.querySelector('#login-form .btn-primary');

        if (!email || !password) {
            alert("Please enter email and password.");
            return;
        }

        // Disable button and show loading
        loginBtn.disabled = true;
        loginBtn.textContent = 'Logging in...';

        try {
            const result = await this.callAPI('/auth/login', 'POST', {
                phone: email,
                password: password
            });
            
            this.authToken = result.token;
            this.currentUser = result.user;
            
            // Store in localStorage
            localStorage.setItem('authToken', result.token);
            localStorage.setItem('currentUser', JSON.stringify(result.user));
            
            this.updateUserGreeting();
            this.navigate('home-screen');
            this.loadRecentBookings();
            this.loadAnalytics();
            this.loadNotifications();
        } catch (error) {
            alert("Login failed: " + error.message);
        } finally {
            loginBtn.disabled = false;
            loginBtn.textContent = 'Login';
        }
    },

    // Register with email and password
    async register() {
        const name = document.getElementById('register-name').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const registerBtn = document.querySelector('#register-form .btn-primary');

        if (!name || !email || !password) {
            alert("Please fill all fields.");
            return;
        }

        // Disable button and show loading
        registerBtn.disabled = true;
        registerBtn.textContent = 'Creating Account...';

        try {
            const result = await this.callAPI('/auth/register', 'POST', {
                name: name,
                phone: email,
                email: email,
                password: password,
                role: 'user'
            });
            
            this.authToken = result.token;
            this.currentUser = result.user;
            
            // Store in localStorage
            localStorage.setItem('authToken', result.token);
            localStorage.setItem('currentUser', JSON.stringify(result.user));
            
            this.updateUserGreeting();
            this.navigate('home-screen');
            this.loadRecentBookings();
            this.loadAnalytics();
            this.loadNotifications();
        } catch (error) {
            alert("Registration failed: " + error.message);
        } finally {
            registerBtn.disabled = false;
            registerBtn.textContent = 'Create Account';
        }
    },

    // Logout
    async logout() {
        try {
            await this.callAPI('/auth/logout', 'POST');
        } catch (e) {
            console.warn('Logout API call failed:', e);
        }
        
        // Clear local storage
        localStorage.removeItem('authToken');
        localStorage.removeItem('currentUser');
        this.authToken = null;
        this.currentUser = null;
        
        this.navigate('auth-screen');
    },

    // Update user greeting
    updateUserGreeting() {
        const greetingEl = document.getElementById('user-greeting');
        if (greetingEl && this.currentUser) {
            greetingEl.textContent = `Hello, ${this.currentUser.name || 'User'}`;
        }
    },

    // Load analytics
    async loadAnalytics() {
        try {
            const stats = await this.callAPI('/analytics/stats', 'GET');
            const summaryEl = document.getElementById('analytics-summary');
            if (summaryEl) {
                summaryEl.style.display = 'block';
                document.getElementById('stat-bookings').textContent = stats.total_bookings || 0;
                document.getElementById('stat-completed').textContent = stats.completed_bookings || 0;
                document.getElementById('stat-rating').textContent = stats.average_rating || '0.0';
            }
        } catch (e) {
            console.warn('Could not load analytics:', e);
        }
    },

    // Load notifications
    async loadNotifications() {
        try {
            const result = await this.callAPI('/notifications', 'GET');
            const badgeEl = document.getElementById('notif-badge');
            if (badgeEl) {
                if (result.unread > 0) {
                    badgeEl.textContent = result.unread;
                    badgeEl.style.display = 'block';
                } else {
                    badgeEl.style.display = 'none';
                }
            }
        } catch (e) {
            console.warn('Could not load notifications:', e);
        }
    },

    // Show notifications modal
    async showNotifications() {
        try {
            const result = await this.callAPI('/notifications', 'GET');
            const listEl = document.getElementById('notification-list');
            listEl.innerHTML = '';
            
            if (!result.notifications || result.notifications.length === 0) {
                listEl.innerHTML = '<p class="text-muted" style="text-align:center;padding:16px;">No notifications yet.</p>';
            } else {
                result.notifications.forEach(n => {
                    const item = document.createElement('div');
                    item.className = `notification-item ${!n.is_read ? 'unread' : ''}`;
                    item.innerHTML = `
                        <div class="notif-icon"><i class="ph-fill ph-bell"></i></div>
                        <div class="notif-content">
                            <p>${n.message}</p>
                            <small>${new Date(n.created_at).toLocaleString()}</small>
                        </div>
                    `;
                    listEl.appendChild(item);
                });
            }
            
            document.getElementById('notification-modal').style.display = 'flex';
        } catch (e) {
            console.warn('Could not load notifications:', e);
        }
    },

    // Hide notifications modal
    hideNotifications() {
        document.getElementById('notification-modal').style.display = 'none';
    },

    // Mark all notifications as read
    async markAllNotificationsRead() {
        try {
            await this.callAPI('/notifications/mark-all-read', 'POST');
            this.hideNotifications();
            this.loadNotifications();
        } catch (e) {
            console.warn('Could not mark notifications as read:', e);
        }
    },

    // Load recent bookings on home screen
    async loadRecentBookings() {
        try {
            const result = await this.callAPI('/bookings', 'GET');
            const bookings = result.bookings || [];
            const list = document.querySelector('.booking-list');
            if (!list) return;
            list.innerHTML = '';
            if (!bookings || bookings.length === 0) {
                list.innerHTML = '<p class="text-muted" style="text-align:center;padding:16px;">No recent bookings.</p>';
                return;
            }
            bookings.slice(0, 3).forEach(b => {
                const item = document.createElement('div');
                item.className = 'booking-list-item glass-card mb-2';
                item.innerHTML = `
                    <div class="booking-item-row">
                        <div class="booking-item-icon">
                            <i class="ph-fill ph-calendar-check"></i>
                        </div>
                        <div class="booking-item-info">
                            <strong>${b.service_type ? b.service_type.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()) : 'Service'}</strong>
                            <p>${b.confirmation_code || ''} • <span class="status-badge status-${(b.status||'').toLowerCase()}">${b.status || 'N/A'}</span></p>
                        </div>
                        <div class="booking-item-price">PKR ${b.price ? Math.round(b.price).toLocaleString() : 'N/A'}</div>
                    </div>
                `;
                list.appendChild(item);
            });
        } catch (e) {
            console.warn('Could not load bookings:', e);
        }
    },

    // Poll live trace from GET /trace/{session_id}
    async pollLiveTrace(session_id, onComplete) {
        this.navigate('trace-screen');
        const traceLogs = document.getElementById('trace-logs');
        const traceStatus = document.getElementById('trace-status');
        traceLogs.innerHTML = '';

        const agentMeta = {
            'Munsif': { icon: '🧠' }, 'Zuban': { icon: '🔍' }, 'Khoji': { icon: '📡' },
            'Jadwal': { icon: '🗓️' }, 'Qeemat': { icon: '💰' }, 'Meezan': { icon: '📋' },
            'Insaf': { icon: '⚖️' }, 'Hukum': { icon: '📝' }, 'System': { icon: '⚙️' }
        };

        let lastStepCount = 0;
        let tries = 0;
        const maxTries = 20;

        const poll = async () => {
            tries++;
            try {
                const res = await this.callAPI(`/trace/${session_id}`, 'GET');
                const steps = res.steps || [];

                // Render new steps
                for (let i = lastStepCount; i < steps.length; i++) {
                    const step = steps[i];
                    const icon = agentMeta[step.agent]?.icon || '🤖';
                    const stepEl = document.createElement('div');
                    stepEl.className = `trace-step ${step.stage === 'error' ? 'warning' : 'success'} fade-up-anim`;
                    stepEl.innerHTML = `
                        <div class="trace-icon">${icon}</div>
                        <div class="trace-agent">[${step.agent}]</div>
                        <div class="trace-msg">${step.message}</div>
                        <div class="trace-time">#${step.step_number}</div>
                    `;
                    traceLogs.appendChild(stepEl);
                    traceLogs.scrollTop = traceLogs.scrollHeight;
                }
                lastStepCount = steps.length;
            } catch (e) {
                console.warn('Trace poll error:', e);
            }

            if (tries < maxTries) {
                setTimeout(poll, 600);
            } else {
                traceStatus.innerHTML = `<span>✅ Processing complete.</span>`;
                const doneBtn = document.createElement('button');
                doneBtn.className = 'trace-done-btn fade-up-anim';
                doneBtn.style.display = 'block';
                doneBtn.textContent = onComplete ? 'Continue' : 'Back to Home';
                doneBtn.onclick = () => { if (onComplete) onComplete(); else this.navigate('home-screen'); };
                traceLogs.appendChild(doneBtn);
                traceLogs.scrollTop = traceLogs.scrollHeight;
            }
        };

        setTimeout(poll, 500);
    },

    // Home Screen Logic
    onInput(textarea) {
        const text = textarea.value.toLowerCase();
        const badge = document.getElementById('lang-badge');
        
        // Simple Urdu detection mock
        const urduKeywords = ['hai', 'kar', 'nahi', 'kya', 'mere', 'tapak', 'raha'];
        const isUrdu = urduKeywords.some(kw => text.includes(kw));
        
        if (isUrdu) {
            badge.textContent = 'اردو';
            badge.style.background = 'rgba(14, 159, 110, 0.1)';
            badge.style.color = '#0E9F6E';
        } else {
            badge.textContent = 'English';
            badge.style.background = 'rgba(26, 86, 219, 0.1)';
            badge.style.color = '#1A56DB';
        }
    },

    fillInput(text) {
        const input = document.getElementById('home-request-input');
        input.value = text;
        this.onInput(input);
    },

    processRequest() {
        const input = document.getElementById('home-request-input');
        if (input.value.trim() === '') return;
        
        const messageText = input.value;
        this.navigate('chat-screen');
        
        // Clear home input and fill chat input
        document.getElementById('chat-input').value = messageText;
        input.value = '';
        
        // Trigger send
        this.sendMessage();
    },

    // Navigate between screens
    navigate(screenId, navElement = null) {
        // Hide all screens
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });

        // Show target screen
        const targetScreen = document.getElementById(screenId);
        if (targetScreen) {
            targetScreen.classList.add('active');
            this.currentScreen = screenId;
            
            // Clear chat mock data when entering chat screen
            if (screenId === 'chat-screen') {
                const chatContainer = document.getElementById('chat-container');
                const typingIndicator = document.getElementById('typing-indicator');
                // Remove any existing chat bubbles but keep typing indicator
                Array.from(chatContainer.children).forEach(child => {
                    if (child !== typingIndicator && child.classList.contains('chat-bubble')) {
                        child.remove();
                    }
                });
                // Add welcome message if no bubbles exist
                if (!chatContainer.querySelector('.chat-bubble')) {
                    const welcomeBubble = document.createElement('div');
                    welcomeBubble.className = 'chat-bubble agent-bubble fade-up-anim';
                    welcomeBubble.textContent = 'Assalam o Alaikum! Mai Munsif hoon. Aapko aaj kis service ki zaroorat hai?';
                    chatContainer.insertBefore(welcomeBubble, typingIndicator);
                }
                typingIndicator.style.display = 'none';
            }
            
            // Load bookings when entering bookings screen
            if (screenId === 'bookings-screen') {
                this.loadBookingsList();
            }
            
            // Load profile when entering profile screen
            if (screenId === 'profile-screen') {
                this.loadProfile();
            }
        }

        // Handle Bottom Nav Bar visibility
        const bottomNav = document.getElementById('bottom-nav');
        if (targetScreen.classList.contains('has-bottom-nav')) {
            bottomNav.style.display = 'flex';
        } else {
            bottomNav.style.display = 'none';
        }

        // Handle Nav Bar Active States
        if (navElement) {
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            navElement.classList.add('active');
        } else {
            // Auto update nav if navigating programmatically (e.g. from splash to home)
            if(screenId === 'home-screen') {
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                document.querySelectorAll('.nav-item')[0].classList.add('active');
            }
        }
    },

    // Search for providers via Khoji
    async searchProviders(intent) {
        this.addAgentResponse("Theek hai! Mai behtareen providers dhoond raha hoon...");
        
        try {
            const res = await this.callAPI('/search', 'POST', {
                session_id: this.sessionId,
                service_type: intent.service_type,
                location: intent.location,
                urgency: intent.urgency
            });

            if (res.status === 'success') {
                const providers = res.top_providers;
                const agentBubble = document.createElement('div');
                agentBubble.className = 'chat-bubble agent-bubble fade-up-anim';
                
                let content = `<p>${res.message}</p><div class="provider-list mt-2">`;
                providers.forEach((p, index) => {
                    const verifiedBadge = p.is_verified ? '<i class="ph-fill ph-seal-check text-primary" title="Verified Provider"></i>' : '';
                    content += `
                        <div class="provider-option-card glass-card mb-2" data-provider-index="${index}">
                            <div class="provider-row">
                                <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(p.name)}&background=1A56DB&color=fff" class="avatar-sm">
                                <div class="provider-info">
                                    <strong>${this.escapeHtml(p.name)} ${verifiedBadge}</strong>
                                    <p>⭐ ${p.rating} • ${p.distance_km}km • ${this.escapeHtml(p.rationale || 'Recommended')}</p>
                                </div>
                                <div class="price-tag">PKR ${p.base_price}</div>
                            </div>
                        </div>
                    `;
                });
                content += `</div>`;
                agentBubble.innerHTML = content;
                
                // Add event listeners to provider cards
                const chatContainer = document.getElementById('chat-container');
                const typingIndicator = document.getElementById('typing-indicator');
                chatContainer.insertBefore(agentBubble, typingIndicator);
                
                agentBubble.querySelectorAll('.provider-option-card').forEach(card => {
                    const index = parseInt(card.dataset.providerIndex);
                    card.onclick = () => this.selectProvider(providers[index], intent);
                });
                
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } else {
                this.addAgentResponse(res.message);
            }
        } catch (error) {
            this.addAgentResponse("Khoji se rabta nahi ho saka. (Search failed)");
        }
    },

    // Escape HTML to prevent XSS
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    async selectProvider(provider, intent) {
        this.selectedProvider = provider;
        this.currentIntent = intent;
        
        // Show availability check
        this.addAgentResponse(`Aap ne **${provider.name}** ko muntakhib kiya hai. Mai unka schedule check kar raha hoon...`);
        
        try {
            // We'll use the normalized time from intent for the check
            const res = await this.callAPI('/check_schedule', 'POST', {
                session_id: this.sessionId,
                provider_id: provider.provider_id,
                requested_start: intent.time_normalized
            });

            if (res.status === 'available') {
                const agentBubble = document.createElement('div');
                agentBubble.className = 'chat-bubble agent-bubble fade-up-anim';
                agentBubble.innerHTML = `
                    <p>✅ Ye slot available hai! Kya mai aapki booking confirm kar doon?</p>
                    <button class="btn-primary mt-2" onclick="app.confirmBooking()">Confirm Booking</button>
                `;
                const chatContainer = document.getElementById('chat-container');
                const typingIndicator = document.getElementById('typing-indicator');
                chatContainer.insertBefore(agentBubble, typingIndicator);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } else {
                this.addAgentResponse("Maazrat! Ye provider is waqt masroof hain. (Slot unavailable)");
            }
        } catch (error) {
            this.addAgentResponse("Jadwal se rabta nahi ho saka. (Schedule check failed)");
        }
    },

    async confirmBooking() {
        const confirmBtn = document.querySelector('#chat-container .btn-primary');
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.textContent = 'Confirming...';
        }
        
        this.addAgentResponse("Booking confirm ho rahi hai... Qeemat aur Meezan agents kaam kar rahe hain.");
        
        try {
            const res = await this.callAPI('/book', 'POST', {
                session_id: this.sessionId,
                provider_id: this.selectedProvider.provider_id,
                service_type: this.currentIntent.service_type,
                location: this.currentIntent.location,
                distance_km: this.selectedProvider.distance_km,
                urgency: this.currentIntent.urgency,
                confirmed_slot: (this.currentIntent.time_raw || 'Today') + " — " + (this.currentIntent.time_normalized || 'ASAP')
            });

            // Show Confirmation Screen
            document.getElementById('conf-code').textContent = res.confirmation_code;

            // Update provider name
            const provNameEl = document.querySelector('#confirmation-screen h4');
            if (provNameEl) provNameEl.textContent = res.provider_name;

            // Update avatar in confirmation
            const provAvatarEl = document.querySelector('#confirmation-screen .provider-row img');
            if (provAvatarEl) provAvatarEl.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(res.provider_name)}&background=1A56DB&color=fff`;

            // Update meta
            const metaPs = document.querySelectorAll('#confirmation-screen .booking-meta p');
            if (metaPs[0]) metaPs[0].innerHTML = `<i class="ph ph-calendar"></i> ${res.confirmed_slot}`;
            if (metaPs[1]) metaPs[1].innerHTML = `<i class="ph ph-map-pin"></i> ${res.location}`;

            // Update rating in confirmation
            const ratingEl = document.querySelector('#confirmation-screen .provider-details p');
            if (ratingEl) ratingEl.innerHTML = `<i class="ph-fill ph-star text-yellow"></i> ${res.provider_rating} • ${res.distance_km}km away`;
            
            // Price breakdown from structured breakdown object
            const breakdownList = document.querySelector('.breakdown-list');
            breakdownList.innerHTML = '';

            if (res.price_breakdown) {
                // Parse newline-separated trace log
                const lines = res.price_breakdown.split('\n');
                const labelMap = {
                    'Base rate': 'Base Rate',
                    'Urgency': 'Urgency Premium',
                    'Distance': 'Distance Charge',
                    'Peak hour': 'Peak Hour Factor',
                    'Quality premium': 'Quality Premium',
                    'Experience bonus': 'Experience Factor',
                };
                lines.forEach(line => {
                    const match = line.match(/([^:]+):\s+([\+\-]?PKR[\d,\.]+|[\+\-]?x[\d\.]+)/i);
                    if (match) {
                        const row = document.createElement('div');
                        row.className = 'breakdown-row';
                        const key = match[1].trim().replace('💰 Calculating price...', '').trim();
                        if (key) {
                            row.innerHTML = `<span>${key}</span><span>${match[2].trim()}</span>`;
                            breakdownList.appendChild(row);
                        }
                    }
                });
            }
            
            const totalRow = document.createElement('div');
            totalRow.className = 'breakdown-row border-top';
            totalRow.innerHTML = `<span><strong>Total Price</strong></span><span><strong>PKR ${res.final_price.toLocaleString()}</strong></span>`;
            breakdownList.appendChild(totalRow);

            this.currentBooking = res;

            // Update tracking screen with real provider info
            const trackAvatar = document.querySelector('#tracking-screen .provider-strip img');
            if (trackAvatar) trackAvatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(res.provider_name)}&background=0A5C36&color=fff`;
            const trackName = document.querySelector('#tracking-screen .provider-meta h4');
            if (trackName) trackName.textContent = res.provider_name;
            const trackRating = document.querySelector('#tracking-screen .provider-meta p');
            if (trackRating) trackRating.innerHTML = `<i class="ph-fill ph-star text-yellow"></i> ${res.provider_rating} • Service Provider`;

            // Update feedback screen price
            const feedbackPrice = document.querySelector('.final-invoice strong');
            if (feedbackPrice) feedbackPrice.textContent = `PKR ${res.final_price.toLocaleString()}`;

            this.navigate('confirmation-screen');
            
            // Refresh analytics and bookings
            this.loadAnalytics();
            this.loadRecentBookings();
        } catch (error) {
            console.error(error);
            this.addAgentResponse("Booking fail ho gayi. (Booking failed)");
        } finally {
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.textContent = 'Confirm Booking';
            }
        }
    },

    // Send Message in Chat
    async sendMessage() {
        const input = document.getElementById('chat-input');
        const sendBtn = document.querySelector('.send-btn');
        const messageText = input.value.trim();

        if (messageText === '') return;

        const chatContainer = document.getElementById('chat-container');
        const typingIndicator = document.getElementById('typing-indicator');

        // Disable input and button during request
        input.disabled = true;
        if (sendBtn) sendBtn.style.opacity = '0.5';

        // 1. Create and append User Bubble
        const userBubble = document.createElement('div');
        userBubble.className = 'chat-bubble user-bubble fade-up-anim';
        userBubble.textContent = messageText;
        
        chatContainer.insertBefore(userBubble, typingIndicator);
        input.value = '';
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // 2. Show Typing Indicator
        typingIndicator.style.display = 'flex';
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            // 3. Call Backend
            const res = await this.callAPI('/chat', 'POST', {
                session_id: this.sessionId,
                text: messageText
            });

            this.sessionId = res.session_id;
            typingIndicator.style.display = 'none';

            // 4. Add Agent Response
            const agentBubble = document.createElement('div');
            agentBubble.className = 'chat-bubble agent-bubble fade-up-anim';
            
            let content = '';
            if (res.intent) {
                content += `
                    <div class="intent-card">
                        <p><strong>Intent:</strong> ${res.intent.service_label}</p>
                        <p><strong>Urgency:</strong> <span class="badge ${res.intent.urgency === 'normal' ? '' : 'badge-error'}">${res.intent.urgency}</span></p>
                    </div>
                `;
            }
            content += res.message;
            agentBubble.innerHTML = content;
            
            chatContainer.insertBefore(agentBubble, typingIndicator);
            chatContainer.scrollTop = chatContainer.scrollHeight;

            // 5. Handle Next Steps
            if (res.next_step === 'khoji_search') {
                setTimeout(() => {
                    // Use live trace polling if session_id available
                    if (this.sessionId) {
                        this.pollLiveTrace(this.sessionId, () => {
                            this.navigate('chat-screen');
                            this.searchProviders(res.intent);
                        });
                    } else {
                        this.runTrace(res.session_state?.workplan || [], () => {
                            this.searchProviders(res.intent);
                        });
                    }
                }, 1000);
            }
        } catch (error) {
            typingIndicator.style.display = 'none';
            this.addAgentResponse("Maazrat! System mein koi masla aa gaya hai. (Error connecting to backend)");
        } finally {
            // Re-enable input and button
            input.disabled = false;
            if (sendBtn) sendBtn.style.opacity = '1';
            input.focus();
        }
    },

    // Agent Trace Simulation (F6)
    runTrace(workplan = [], onComplete = null) {
        this.navigate('trace-screen');
        const traceLogs = document.getElementById('trace-logs');
        const traceStatus = document.getElementById('trace-status');
        traceLogs.innerHTML = ''; // Clear previous
        
        // Define standard icons/labels for agents
        const agentMeta = {
            'Munsif': { icon: '🧠', label: 'Munsif' },
            'Zuban': { icon: '🔍', label: 'Zuban' },
            'Khoji': { icon: '📡', label: 'Khoji' },
            'Jadwal': { icon: '🗓️', label: 'Jadwal' },
            'Qeemat': { icon: '💰', label: 'Qeemat' },
            'Meezan': { icon: '📋', label: 'Meezan' },
            'Insaf': { icon: '⚖️', label: 'Insaf' }
        };

        const steps = workplan.map(step => ({
            agent: step.agent,
            icon: agentMeta[step.agent]?.icon || '🤖',
            msg: step.action + (step.error ? `: <span style="color:red">${step.error}</span>` : ''),
            time: '300ms',
            type: step.error ? 'warning' : 'success'
        }));

        let currentStep = 0;

        const renderStep = () => {
            if (currentStep >= steps.length) {
                traceStatus.innerHTML = `<span>✅ Processing complete.</span>`;
                const doneBtn = document.createElement('button');
                doneBtn.className = 'trace-done-btn fade-up-anim';
                doneBtn.style.display = 'block';
                doneBtn.textContent = onComplete ? 'Continue' : 'Back to Home';
                doneBtn.onclick = () => {
                    if (onComplete) onComplete();
                    else this.navigate('home-screen');
                };
                traceLogs.appendChild(doneBtn);
                traceLogs.scrollTop = traceLogs.scrollHeight;
                return;
            }

            const step = steps[currentStep];
            const stepEl = document.createElement('div');
            stepEl.className = `trace-step ${step.type}`;
            stepEl.innerHTML = `
                <div class="trace-icon">${step.icon}</div>
                <div class="trace-agent">[${step.agent}]</div>
                <div class="trace-msg">${step.msg}</div>
                <div class="trace-time">${step.time}</div>
            `;
            traceLogs.appendChild(stepEl);
            traceLogs.scrollTop = traceLogs.scrollHeight;

            currentStep++;
            setTimeout(renderStep, 400);
        };

        setTimeout(renderStep, 500);
    },

    // Service Lifecycle Simulation (F7)
    startTrackingSimulation() {
        this.navigate('tracking-screen');
        this.initMap();

        // Update booking status to en-route in backend
        if (this.currentBooking?.booking_id) {
            this.callAPI('/track', 'POST', {
                booking_id: this.currentBooking.booking_id,
                status: 'EN_ROUTE'
            }).catch(e => console.warn('Track update failed:', e));
        }
        
        console.log("Starting en-route simulation...");
        
        // Remove old finish-btn if exists
        const oldBtn = document.getElementById('finish-btn');
        if (oldBtn) oldBtn.remove();

        // Connect to WebSocket for real-time updates
        this.connectTrackingWebSocket();

        // Update arrival est progressively
        const arrivalEst = document.querySelector('.arrival-est h2');
        const statusMsg = document.querySelector('.status-msg');
        
        setTimeout(() => {
            if (arrivalEst) arrivalEst.textContent = "7 Minutes";
            if (statusMsg) statusMsg.textContent = "Ustad is on the way to your location.";
        }, 2000);

        setTimeout(() => {
            if (arrivalEst) arrivalEst.textContent = "5 Minutes";
            if (statusMsg) statusMsg.textContent = "Ustad is turning onto your street.";
        }, 5000);

        setTimeout(() => {
            if (arrivalEst) arrivalEst.textContent = "Arrived";
            if (statusMsg) statusMsg.textContent = "Provider is outside. Please meet them.";
            
            // Update backend status to arrived
            if (this.currentBooking?.booking_id) {
                this.callAPI('/track', 'POST', {
                    booking_id: this.currentBooking.booking_id,
                    status: 'ARRIVED'
                }).catch(e => console.warn('Track update failed:', e));
            }

            // Add a button to simulate completion
            const infoCard = document.querySelector('.tracking-info-card');
            if (!document.getElementById('finish-btn')) {
                const finishBtn = document.createElement('button');
                finishBtn.id = 'finish-btn';
                finishBtn.className = 'btn-primary mt-4 fade-up-anim';
                finishBtn.textContent = 'Simulate Work Completion';
                finishBtn.onclick = () => {
                    // Update backend status to completed
                    if (this.currentBooking?.booking_id) {
                        this.callAPI('/track', 'POST', {
                            booking_id: this.currentBooking.booking_id,
                            status: 'COMPLETED'
                        }).catch(e => console.warn('Track update failed:', e));
                    }
                    // Close WebSocket
                    if (this.ws) {
                        this.ws.close();
                    }
                    this.navigate('feedback-screen');
                    // Ensure correct price on feedback screen
                    const priceEl = document.querySelector('.final-invoice strong');
                    if (priceEl && this.currentBooking?.final_price) {
                        priceEl.textContent = `PKR ${this.currentBooking.final_price.toLocaleString()}`;
                    }
                };
                infoCard.appendChild(finishBtn);
            }
        }, 10000);
    },

    // Connect to WebSocket for real-time tracking
    connectTrackingWebSocket() {
        if (!this.currentBooking?.booking_id) return;
        
        const wsUrl = `ws://127.0.0.1:8000/ws/tracking/${this.currentBooking.booking_id}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected for tracking');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Tracking update:', data);
            // Update map with provider location
            if (data.provider_location && this.providerMarker) {
                this.providerMarker.setPosition(data.provider_location);
            }
        };
        
        this.ws.onerror = (error) => {
            console.warn('WebSocket error:', error);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
        };
    },

    initMap() {
        // Default to Karachi coords (city center)
        const defaultLocation = { lat: 24.8607, lng: 67.0011 };
        let userLocation = defaultLocation;
        
        this.map = new google.maps.Map(document.getElementById("map"), {
            zoom: 12,
            center: defaultLocation,
            disableDefaultUI: false,
            zoomControl: true,
            mapTypeControl: false,
            scaleControl: true,
            streetViewControl: false,
            rotateControl: false,
            fullscreenControl: true,
        });

        // Try to get user's actual location
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    userLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    this.userMarker.setPosition(userLocation);
                    this.map.setCenter(userLocation);
                    this.map.setZoom(14);
                    this.updateProviderMarkerAndRoute(userLocation);
                },
                (error) => {
                    console.warn("Geolocation error:", error);
                    // Use default location if geolocation fails
                    this.updateProviderMarkerAndRoute(userLocation);
                },
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
        } else {
            console.warn("Geolocation not supported");
            this.updateProviderMarkerAndRoute(userLocation);
        }

        // Add User Marker with custom icon
        const userIcon = {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: '#0E9F6E',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 2,
            scale: 12
        };
        
        this.userMarker = new google.maps.Marker({
            position: userLocation,
            map: this.map,
            title: "You are here",
            icon: userIcon,
            label: {
                text: "You",
                color: "#ffffff",
                fontSize: "10px",
                fontWeight: "bold"
            }
        });

        // Initialize provider marker and route
        this.updateProviderMarkerAndRoute(userLocation);
    },

    updateProviderMarkerAndRoute(userLocation) {
        // Get provider location from selected provider
        let providerLocation = { 
            lat: userLocation.lat + 0.02, 
            lng: userLocation.lng + 0.02 
        };
        
        if (this.selectedProvider) {
            // Use provider's actual coordinates if available
            providerLocation = {
                lat: this.selectedProvider.lat || userLocation.lat + 0.02,
                lng: this.selectedProvider.lng || userLocation.lng + 0.02
            };
        }
        
        // Add Provider Marker with custom icon
        const providerIcon = {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: '#1A56DB',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 2,
            scale: 12
        };
        
        this.providerMarker = new google.maps.Marker({
            position: providerLocation,
            map: this.map,
            title: this.selectedProvider?.name || "Provider",
            icon: providerIcon,
            label: {
                text: "P",
                color: "#ffffff",
                fontSize: "12px",
                fontWeight: "bold"
            }
        });

        // Draw route line between user and provider
        this.routeLine = new google.maps.Polyline({
            path: [userLocation, providerLocation],
            geodesic: true,
            strokeColor: '#1A56DB',
            strokeOpacity: 0.8,
            strokeWeight: 4,
            icons: [{
                icon: {
                    path: 'M 0,-1 0,1',
                    strokeOpacity: 1,
                    scale: 4
                },
                offset: '0',
                repeat: '20px'
            }]
        });
        this.routeLine.setMap(this.map);

        // Fit map to show both markers
        const bounds = new google.maps.LatLngBounds();
        bounds.extend(userLocation);
        bounds.extend(providerLocation);
        this.map.fitBounds(bounds, { top: 50, bottom: 50, left: 50, right: 50 });
            
        // Animate provider marker towards user (simulating movement)
        this.animateProviderMovement(userLocation, providerLocation);
    },

    animateProviderMovement(userLocation, providerLocation) {
        let step = 0;
        const totalSteps = 100;
        const startLat = providerLocation.lat;
        const startLng = providerLocation.lng;
        
        const interval = setInterval(() => {
            if (step >= totalSteps || this.currentScreen !== 'tracking-screen') {
                clearInterval(interval);
                return;
            }
            const progress = step / totalSteps;
            const currentLat = startLat - (startLat - userLocation.lat) * progress;
            const currentLng = startLng - (startLng - userLocation.lng) * progress;
            this.providerMarker.setPosition({ lat: currentLat, lng: currentLng });
            
            // Update route line
            if (this.routeLine) {
                this.routeLine.setPath([userLocation, { lat: currentLat, lng: currentLng }]);
            }
            
            step++;
        }, 300);
    },

    // Feedback Logic (F7-C)
    initFeedback() {
        const stars = document.querySelectorAll('.star-rating i');
        stars.forEach(star => {
            star.onclick = () => {
                const val = star.getAttribute('data-value');
                stars.forEach(s => {
                    if (s.getAttribute('data-value') <= val) {
                        s.classList.add('active', 'ph-fill');
                        s.classList.remove('ph');
                    } else {
                        s.classList.remove('active', 'ph-fill');
                        s.classList.add('ph');
                    }
                });
                this.currentRating = val;
            };
        });
    },

    async submitFeedback() {
        if (!this.currentBooking?.booking_id) {
            alert("No booking found to submit feedback for.");
            return;
        }
        
        const rating = this.currentRating || 5;
        const comment = document.getElementById('feedback-comment').value;
        const onTime = document.getElementById('check-time').checked;
        const quality = document.getElementById('check-quality').checked;
        const clean = document.getElementById('check-clean').checked;
        
        try {
            await this.callAPI('/feedback', 'POST', {
                booking_id: this.currentBooking.booking_id,
                rating: parseFloat(rating),
                on_time: onTime,
                quality: quality,
                cleanliness: clean,
                comment: comment
            });
            
            this.navigate('home-screen');
            alert("Shukriya! Aapka feedback record kar liya gaya hai.");
        } catch (error) {
            alert("Feedback submit karne mein masla hua.");
        }
    },

    // Dispute Resolution (F8)
    showDisputeModal() {
        document.getElementById('dispute-modal').style.display = 'flex';
    },

    hideDisputeModal() {
        document.getElementById('dispute-modal').style.display = 'none';
    },

    async submitDispute() {
        if (!this.currentBooking?.booking_id) {
            alert("No booking found to dispute.");
            this.hideDisputeModal();
            return;
        }
        
        const type = document.getElementById('dispute-type').value;
        const desc = document.getElementById('dispute-desc').value;
        
        try {
            const res = await this.callAPI('/dispute', 'POST', {
                booking_id: this.currentBooking.booking_id,
                issue_type: type,
                description: desc
            });

            this.hideDisputeModal();
            // Use runTrace with correct workplan format
            const disputeWorkplan = [
                { agent: 'Insaf', action: `Dispute received: ${type.replace(/_/g,' ')}` },
                { agent: 'Insaf', action: `Classification: ${type}` },
                { agent: 'Insaf', action: `Resolution: ${res.resolution || res.message || 'Processing'}` },
                { agent: 'Insaf', action: `Status: ${res.status || 'resolved'}` }
            ];
            this.runTrace(disputeWorkplan, () => this.navigate('home-screen'));
        } catch (error) {
            alert("Dispute submit karne mein masla hua.");
        }
    },

    addAgentResponse(text) {
        const chatContainer = document.getElementById('chat-container');
        const typingIndicator = document.getElementById('typing-indicator');
        const agentBubble = document.createElement('div');
        agentBubble.className = 'chat-bubble agent-bubble fade-up-anim';
        agentBubble.textContent = text;
        chatContainer.insertBefore(agentBubble, typingIndicator);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    },

    // Load full bookings list
    async loadBookingsList() {
        try {
            const result = await this.callAPI('/bookings', 'GET');
            const bookings = result.bookings || [];
            const list = document.getElementById('bookings-list-full');
            if (!list) return;
            list.innerHTML = '';
            if (!bookings || bookings.length === 0) {
                list.innerHTML = '<p class="text-muted" style="text-align:center;padding:32px;">No bookings yet.</p>';
                return;
            }
            bookings.forEach(b => {
                const item = document.createElement('div');
                item.className = 'booking-list-item glass-card mb-2';
                item.innerHTML = `
                    <div class="booking-item-row">
                        <div class="booking-item-icon">
                            <i class="ph-fill ph-calendar-check"></i>
                        </div>
                        <div class="booking-item-info">
                            <strong>${b.service_type ? b.service_type.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()) : 'Service'}</strong>
                            <p>${b.confirmation_code || ''} • <span class="status-badge status-${(b.status||'').toLowerCase()}">${b.status || 'N/A'}</span></p>
                        </div>
                        <div class="booking-item-price">PKR ${b.price ? Math.round(b.price).toLocaleString() : 'N/A'}</div>
                    </div>
                `;
                list.appendChild(item);
            });
        } catch (e) {
            console.warn('Could not load bookings:', e);
        }
    },

    // Load profile screen
    async loadProfile() {
        if (!this.currentUser) return;
        
        const nameEl = document.getElementById('profile-name');
        const emailEl = document.getElementById('profile-email');
        const avatarEl = document.getElementById('profile-avatar');
        
        if (nameEl) nameEl.textContent = this.currentUser.name || 'User';
        if (emailEl) emailEl.textContent = this.currentUser.email || this.currentUser.phone || '';
        if (avatarEl) avatarEl.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(this.currentUser.name || 'User')}&background=1A56DB&color=fff`;
        
        // Load stats
        try {
            const stats = await this.callAPI('/analytics/stats', 'GET');
            const bookingsCount = document.getElementById('profile-bookings-count');
            const completedCount = document.getElementById('profile-completed-count');
            const rating = document.getElementById('profile-rating');
            
            if (bookingsCount) bookingsCount.textContent = stats.total_bookings || 0;
            if (completedCount) completedCount.textContent = stats.completed_bookings || 0;
            if (rating) rating.textContent = stats.average_rating || '0.0';
        } catch (e) {
            console.warn('Could not load profile stats:', e);
        }
    }
};

// Start the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    app.init();
    app.initFeedback();
});
