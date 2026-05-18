/**
 * Antigravity Frontend Router & Logic
 * This mimics a Single Page Application (SPA) for Capacitor.js
 */

const app = {
    // Current active screen
    currentScreen: 'splash-screen',
    
    // API Configuration
    apiBase: 'http://127.0.0.1:8008',
    sessionId: null,

    // Helper for API calls
    async callAPI(endpoint, method = 'POST', data = null) {
        try {
            const options = {
                method: method,
                headers: { 'Content-Type': 'application/json' },
            };
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
        
        // Auto-hide splash screen after 2.5 seconds
        setTimeout(() => {
            this.navigate('auth-screen');
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

    // Load recent bookings on home screen
    async loadRecentBookings() {
        try {
            const bookings = await this.callAPI('/bookings', 'GET');
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
                providers.forEach(p => {
                    content += `
                        <div class="provider-option-card glass-card mb-2" onclick="app.selectProvider(${JSON.stringify(p).replace(/"/g, '&quot;')}, ${JSON.stringify(intent).replace(/"/g, '&quot;')})">
                            <div class="provider-row">
                                <img src="https://ui-avatars.com/api/?name=${p.name.replace(/ /g, '+')}&background=1A56DB&color=fff" class="avatar-sm">
                                <div class="provider-info">
                                    <strong>${p.name}</strong>
                                    <p>⭐ ${p.rating} • ${p.distance_km}km • ${p.rationale}</p>
                                </div>
                                <div class="price-tag">PKR ${p.base_price}</div>
                            </div>
                        </div>
                    `;
                });
                content += `</div>`;
                agentBubble.innerHTML = content;
                
                const chatContainer = document.getElementById('chat-container');
                const typingIndicator = document.getElementById('typing-indicator');
                chatContainer.insertBefore(agentBubble, typingIndicator);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } else {
                this.addAgentResponse(res.message);
            }
        } catch (error) {
            this.addAgentResponse("Khoji se rabta nahi ho saka. (Search failed)");
        }
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
        } catch (error) {
            console.error(error);
            this.addAgentResponse("Booking fail ho gayi. (Booking failed)");
        }
    },

    // Mock Login Function
    login() {
        const phone = document.getElementById('phone').value;
        const password = document.getElementById('password').value;

        if (phone && password) {
            setTimeout(() => {
                this.navigate('home-screen');
                this.loadRecentBookings();
            }, 500);
        } else {
            alert("Please enter phone and password.");
        }
    },

    // Send Message in Chat
    async sendMessage() {
        const input = document.getElementById('chat-input');
        const messageText = input.value.trim();

        if (messageText === '') return;

        const chatContainer = document.getElementById('chat-container');
        const typingIndicator = document.getElementById('typing-indicator');

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

    initMap() {
        // Default to Islamabad coords
        const userLocation = { lat: 33.6844, lng: 73.0479 };
        
        this.map = new google.maps.Map(document.getElementById("map"), {
            zoom: 13,
            center: userLocation,
            disableDefaultUI: true,
        });

        // Add User Marker
        new google.maps.Marker({
            position: userLocation,
            map: this.map,
            title: "You are here"
        });

        // Add Provider Marker (offset slightly for demo)
        let currentLat = userLocation.lat + 0.01;
        let currentLng = userLocation.lng + 0.01;
        
        this.providerMarker = new google.maps.Marker({
            position: { lat: currentLat, lng: currentLng },
            map: this.map,
            title: this.selectedProvider?.name || "Provider",
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                fillColor: '#1A56DB',
                fillOpacity: 1,
                strokeWeight: 0,
                scale: 10
            }
        });
            
        // Animate provider marker towards user
        let step = 0;
        const interval = setInterval(() => {
            if (step >= 100 || this.currentScreen !== 'tracking-screen') {
                clearInterval(interval);
                return;
            }
            currentLat = (userLocation.lat + 0.01) - (0.01 * step / 100);
            currentLng = (userLocation.lng + 0.01) - (0.01 * step / 100);
            this.providerMarker.setPosition({ lat: currentLat, lng: currentLng });
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
        const type = document.getElementById('dispute-type').value;
        const desc = document.getElementById('dispute-desc').value;
        
        try {
            const res = await this.callAPI('/dispute', 'POST', {
                booking_id: this.currentBooking?.booking_id || 1,
                issue_type: type,
                description: desc
            });

            this.hideDisputeModal();
            // Use runTrace with correct workplan format
            const disputeWorkplan = [
                { agent: 'Insaf', action: `Dispute received: ${type.replace(/_/g,' ')}` },
                { agent: 'Insaf', action: `Classification: ${type}` },
                { agent: 'Insaf', action: `Resolution: ${res.resolution}` },
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
    }
};

// Start the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    app.init();
    app.initFeedback();
});
