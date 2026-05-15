document.addEventListener('DOMContentLoaded', () => {
    // Views
    const inputView = document.getElementById('input-view');
    const traceView = document.getElementById('trace-view');
    const proposalView = document.getElementById('proposal-view');
    const confirmationView = document.getElementById('confirmation-view');

    // Buttons
    const analyzeBtn = document.getElementById('analyze-btn');
    const bookBtn = document.getElementById('book-btn');
    const homeBtn = document.getElementById('home-btn');

    // Data elements
    const providersContainer = document.getElementById('providers-container');
    const totalPriceEl = document.getElementById('total-price');
    const confCodeEl = document.getElementById('conf-code');
    const confProviderEl = document.getElementById('conf-provider');

    // State
    let selectedProvider = null;

    // Mock Data
    const mockProviders = [
        { id: 1, name: 'Ali Raza', rating: '4.9 ★', match: '98% Match', price: 2500 },
        { id: 2, name: 'Usman Khan', rating: '4.7 ★', match: '92% Match', price: 2200 },
        { id: 3, name: 'Bilal Ahmed', rating: '4.5 ★', match: '85% Match', price: 2000 }
    ];

    function switchView(hideView, showView) {
        hideView.classList.remove('active');
        showView.classList.add('active');
    }

    // Step 1: Analyze Request
    analyzeBtn.addEventListener('click', () => {
        const text = document.getElementById('user-request').value.trim();
        if (!text) return;

        switchView(inputView, traceView);
        runTraceSimulation();
    });

    function runTraceSimulation() {
        const steps = ['zuban', 'khoji', 'jadwal', 'qeemat'];
        let currentStep = 0;

        function advanceStep() {
            if (currentStep > 0) {
                // Mark previous as done
                const prevStepEl = document.getElementById(`step-${steps[currentStep-1]}`);
                prevStepEl.classList.remove('pending');
                prevStepEl.classList.add('done');
                // The spinner in CSS becomes a checkmark when .done is added
            }

            if (currentStep < steps.length) {
                // Activate current
                const currStepEl = document.getElementById(`step-${steps[currentStep]}`);
                currStepEl.classList.remove('pending');
                
                setTimeout(advanceStep, 1000); // Wait 1 second per step
                currentStep++;
            } else {
                // All steps done, go to proposal
                setTimeout(() => {
                    populateProviders();
                    switchView(traceView, proposalView);
                    
                    // Reset trace view for next time
                    steps.forEach(s => {
                        const el = document.getElementById(`step-${s}`);
                        el.className = 'step pending';
                    });
                    document.getElementById('step-zuban').classList.remove('pending');
                }, 500);
            }
        }

        advanceStep();
    }

    // Step 2: Show Proposals
    function populateProviders() {
        providersContainer.innerHTML = '';
        mockProviders.forEach((provider, index) => {
            const card = document.createElement('div');
            card.className = `provider-card ${index === 0 ? 'selected' : ''}`;
            card.innerHTML = `
                <div class="provider-header">
                    <span class="provider-name">${provider.name}</span>
                    <span class="provider-rating">${provider.rating}</span>
                </div>
                <div class="provider-match">${provider.match}</div>
            `;
            
            if (index === 0) {
                selectedProvider = provider;
                totalPriceEl.textContent = `₨ ${provider.price.toLocaleString()}`;
            }

            card.addEventListener('click', () => {
                document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                selectedProvider = provider;
                totalPriceEl.textContent = `₨ ${provider.price.toLocaleString()}`;
            });

            providersContainer.appendChild(card);
        });
    }

    // Step 3: Book
    bookBtn.addEventListener('click', () => {
        switchView(proposalView, confirmationView);
        
        // Generate random code
        const code = 'BKG-' + Math.random().toString(36).substr(2, 6).toUpperCase();
        confCodeEl.textContent = code;
        confProviderEl.textContent = selectedProvider.name;
    });

    // Step 4: Back to Home
    homeBtn.addEventListener('click', () => {
        document.getElementById('user-request').value = '';
        switchView(confirmationView, inputView);
    });
});
