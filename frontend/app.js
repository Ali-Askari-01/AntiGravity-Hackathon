/**
 * Antigravity Frontend Router & Logic
 * This mimics a Single Page Application (SPA) for Capacitor.js
 */

const app = {
    // Current active screen
    currentScreen: 'splash-screen',

    // Initialize the app
    init() {
        console.log("Antigravity App Initialized");
        
        // Auto-hide splash screen after 3 seconds for demo purposes
        // In reality, this would happen after loading initial data/auth checks
        setTimeout(() => {
            // Check if user is logged in (mock)
            // this.navigate('home-screen'); // If logged in
        }, 3000);

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
        
        // Transfer text to chat just in case
        document.getElementById('chat-input').value = input.value;
        this.runTrace();
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

    // Mock Login Function
    login() {
        const phone = document.getElementById('phone').value;
        const password = document.getElementById('password').value;

        if (phone && password) {
            // Add a quick button animation/loading state here if desired
            setTimeout(() => {
                this.navigate('home-screen');
            }, 500);
        } else {
            alert("Please enter phone and password.");
        }
    },

    // Send Message in Chat
    sendMessage() {
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

        // 3. Simulate Agent Response (Mock)
        setTimeout(() => {
            typingIndicator.style.display = 'none';
            
            // Check if it's a service request (demo heuristic)
            if (messageText.toLowerCase().includes('ac') || messageText.toLowerCase().includes('urgent')) {
                this.runTrace();
            } else {
                const agentBubble = document.createElement('div');
                agentBubble.className = 'chat-bubble agent-bubble fade-up-anim';
                agentBubble.innerHTML = `
                    <div class="intent-card">
                        <p><strong>Intent:</strong> General Query</p>
                        <p><strong>Status:</strong> Detected</p>
                    </div>
                    Mai aapki kya madad kar sakta hoon? Aap koi service book karna chahtay hain?
                `;
                chatContainer.insertBefore(agentBubble, typingIndicator);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }, 1500);
    },

    // Agent Trace Simulation (F6)
    runTrace() {
        this.navigate('trace-screen');
        const traceLogs = document.getElementById('trace-logs');
        const traceStatus = document.getElementById('trace-status');
        traceLogs.innerHTML = ''; // Clear previous
        
        const steps = [
            { agent: 'Zuban', icon: '🔍', msg: 'Parsing your request...', time: '400ms', type: 'in-progress' },
            { agent: 'Zuban', icon: '✅', msg: 'Service: AC Technician | Location: G-13<br>Time: Tomorrow 10:00 AM', time: '800ms', type: 'success' },
            { agent: 'Khoji', icon: '📡', msg: 'Searching providers in G-13...', time: '600ms', type: 'in-progress' },
            { agent: 'Khoji', icon: '📊', msg: 'Found 4 providers. Applying 6-factor ranking...', time: '800ms', type: 'success' },
            { agent: 'Khoji', icon: '🏆', msg: 'Selected: Ali AC Services — 2.1km | ⭐4.8', time: '600ms', type: 'success' },
            { agent: 'Jadwal', icon: '🗓️', msg: 'Checking schedule for 10:00 AM slot...', time: '500ms', type: 'in-progress' },
            { agent: 'Jadwal', icon: '✅', msg: 'Slot available. No conflicts.', time: '400ms', type: 'success' },
            { agent: 'Qeemat', icon: '💰', msg: 'Calculating price... Final: PKR 1,438', time: '500ms', type: 'success' },
            { agent: 'Meezan', icon: '📋', msg: 'Creating booking...', time: '400ms', type: 'in-progress' },
            { agent: 'Meezan', icon: '✅', msg: 'Booking confirmed — XIDMAT-2847', time: '400ms', type: 'success' },
            { agent: 'Meezan', icon: '🔔', msg: 'Reminder set for 09:00 AM (1 hour before)', time: '300ms', type: 'success' }
        ];

        let currentStep = 0;

        const renderStep = () => {
            if (currentStep >= steps.length) {
                traceStatus.innerHTML = `<span>✅ All processes complete.</span>`;
                const doneBtn = document.createElement('button');
                doneBtn.className = 'trace-done-btn fade-up-anim';
                doneBtn.style.display = 'block';
                doneBtn.textContent = 'View Booking Confirmation';
                doneBtn.onclick = () => {
                    this.navigate('confirmation-screen');
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
            const delay = parseInt(step.time) || 500;
            setTimeout(renderStep, delay + 200);
        };

        setTimeout(renderStep, 500);
    },

    // Service Lifecycle Simulation (F7)
    startTrackingSimulation() {
        this.navigate('tracking-screen');
        
        // Simulating the 30-second demo status cycle
        console.log("Starting en-route simulation...");
        
        setTimeout(() => {
            document.querySelector('.arrival-est h2').textContent = "5 Minutes";
            document.querySelector('.status-msg').textContent = "Ustad is turning onto your street.";
        }, 5000);

        setTimeout(() => {
            document.querySelector('.arrival-est h2').textContent = "Arrived";
            document.querySelector('.status-msg').textContent = "Provider is outside. Please meet them.";
            
            // Add a button to simulate completion
            const finishBtn = document.createElement('button');
            finishBtn.className = 'btn-primary mt-4 fade-up-anim';
            finishBtn.textContent = 'Simulate Work Completion';
            finishBtn.onclick = () => this.navigate('feedback-screen');
            document.querySelector('.tracking-info-card').appendChild(finishBtn);
        }, 10000);
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

    submitFeedback() {
        const rating = this.currentRating || 5;
        const comment = document.getElementById('feedback-comment').value;
        
        console.log(`Feedback submitted: ${rating} stars. Comment: ${comment}`);
        
        this.navigate('home-screen');
        alert("Shukriya! Aapka feedback record kar liya gaya hai.");
    },

    // Dispute Resolution (F8)
    showDisputeModal() {
        document.getElementById('dispute-modal').style.display = 'flex';
    },

    hideDisputeModal() {
        document.getElementById('dispute-modal').style.display = 'none';
    },

    submitDispute() {
        const type = document.getElementById('dispute-type').value;
        const desc = document.getElementById('dispute-desc').value;
        
        this.hideDisputeModal();
        this.navigate('trace-screen');
        
        const traceLogs = document.getElementById('trace-logs');
        const traceStatus = document.getElementById('trace-status');
        traceLogs.innerHTML = '';
        traceStatus.innerHTML = `<span>⚖️ Insaf Agent is reviewing...</span>`;

        const steps = [
            { agent: 'Insaf', icon: '⚖️', msg: `Dispute received: ${type}`, time: '500ms', type: 'in-progress' },
            { agent: 'Insaf', icon: '🔍', msg: 'Confirmed price: PKR 1,438 | Claimed charge: PKR 2,000', time: '800ms', type: 'warning' },
            { agent: 'Insaf', icon: '📋', msg: `Classification: ${type} — difference = PKR 562`, time: '600ms', type: 'success' },
            { agent: 'Insaf', icon: '✅', msg: 'Resolution: Partial refund of PKR 562 recommended', time: '700ms', type: 'success' },
            { agent: 'Insaf', icon: '⚠️', msg: 'Provider penalty: -0.20 rating impact applied', time: '400ms', type: 'warning' }
        ];

        let currentStep = 0;
        const renderStep = () => {
            if (currentStep >= steps.length) {
                traceStatus.innerHTML = `<span>✅ Dispute Resolved.</span>`;
                const homeBtn = document.createElement('button');
                homeBtn.className = 'trace-done-btn fade-up-anim';
                homeBtn.style.display = 'block';
                homeBtn.textContent = 'Back to Home';
                homeBtn.onclick = () => this.navigate('home-screen');
                traceLogs.appendChild(homeBtn);
                return;
            }

            const step = steps[currentStep];
            const stepEl = document.createElement('div');
            stepEl.className = `trace-step ${step.type}`;
            stepEl.innerHTML = `
                <div class="trace-icon">${step.icon}</div>
                <div class="trace-agent">[${step.agent}]</div>
                <div class="trace-msg">${step.msg}</div>
            `;
            traceLogs.appendChild(stepEl);
            currentStep++;
            setTimeout(renderStep, 800);
        };
        renderStep();
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
