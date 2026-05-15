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
        
        // Insert before typing indicator
        chatContainer.insertBefore(userBubble, typingIndicator);
        
        // Clear input
        input.value = '';
        
        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // 2. Show Typing Indicator
        typingIndicator.style.display = 'flex';
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // 3. Simulate Agent Response (Mock)
        setTimeout(() => {
            typingIndicator.style.display = 'none';
            
            const agentBubble = document.createElement('div');
            agentBubble.className = 'chat-bubble agent-bubble fade-up-anim';
            
            // Mocking a response
            agentBubble.innerHTML = `
                <div class="intent-card">
                    <p><strong>Intent:</strong> General Query</p>
                    <p><strong>Confidence:</strong> 0.85</p>
                </div>
                Ji zaroor, mai aapki madad kar sakta hoon. Tafseel batayen.
            `;
            
            chatContainer.insertBefore(agentBubble, typingIndicator);
            chatContainer.scrollTop = chatContainer.scrollHeight;

        }, 1500); // Simulate network delay
    }
};

// Start the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
