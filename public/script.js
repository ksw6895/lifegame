document.addEventListener('DOMContentLoaded', () => {
    // 1. DOM Element References
    const playerInputEl = document.getElementById('player-input');
    const sendButtonEl = document.getElementById('send-button');
    const chatDisplayEl = document.getElementById('chat-display');
    
    // Player Info Elements
    const playerLevelEl = document.getElementById('player-level');
    const playerXpEl = document.getElementById('player-xp');
    const playerGoldEl = document.getElementById('player-gold');
    const playerStatPointsEl = document.getElementById('player-stat-points');
    const playerStatsListEl = document.getElementById('player-stats-list'); // Parent for individual stats
    // Individual stat span elements (assuming they exist based on HTML structure)
    const statStrEl = document.getElementById('stat-힘');
    const statIntEl = document.getElementById('stat-지능');
    const statWilEl = document.getElementById('stat-의지력');
    const statVitEl = document.getElementById('stat-체력');
    const statChaEl = document.getElementById('stat-매력');

    const inventoryListEl = document.getElementById('inventory-list');
    const questsListEl = document.getElementById('quests-list');
    
    const itemImageEl = document.getElementById('item-image');
    const itemImagePlaceholderEl = document.getElementById('item-image-placeholder');

    // Action Buttons (for future tasks, but good to have references)
    const characterCreationButtonEl = document.getElementById('character-creation-button');
    const helpButtonEl = document.getElementById('help-button');
    const resetGameButtonEl = document.getElementById('reset-game-button');

    // 2. API Base URL
    const API_BASE_URL = '/api'; // Adjust if your dev server runs on a different port

    // 5. UI Update Functions (Part 1: addMessageToChat - needed early)
    function addMessageToChat(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', type); // Assumes 'message' is a base class from style.css
        // Sanitize message text to prevent XSS if it's not already handled by backend/GM.
        // For now, textContent is safer than innerHTML.
        messageDiv.textContent = message; 
        chatDisplayEl.appendChild(messageDiv);
        chatDisplayEl.scrollTop = chatDisplayEl.scrollHeight; // Auto-scroll to bottom
    }

    // 5. UI Update Functions (Part 2: displayHistory)
    function displayHistory(historyArray) {
        if (!historyArray) return;
        historyArray.forEach(entry => {
            // Assuming parts is an array of text strings or objects with a text property
            const messageText = Array.isArray(entry.parts) ? entry.parts.map(part => (typeof part === 'string' ? part : part.text)).join('\n') : entry.parts;
            if (entry.role === 'user') {
                addMessageToChat(`You: ${messageText}`, 'player-message');
            } else if (entry.role === 'model') {
                addMessageToChat(`GM: ${messageText}`, 'gm-message');
            } else {
                addMessageToChat(messageText, 'system-message'); // Fallback for other roles
            }
        });
    }
    
    // 5. UI Update Functions (Part 3: Player Stats)
    function updatePlayerStatsUI(playerData) {
        if (!playerData) return;
        playerLevelEl.textContent = `Level: ${playerData.level || 1}`;
        playerXpEl.textContent = `XP: ${playerData.xp || 0} / ${playerData.xp_to_next_level || 100}`;
        playerGoldEl.textContent = `Gold: ${playerData.gold || 0}G`;
        playerStatPointsEl.textContent = `Stat Points: ${playerData.stat_points || 0}`;

        if (playerData.stats) {
            statStrEl.textContent = playerData.stats["힘"] || 5;
            statIntEl.textContent = playerData.stats["지능"] || 5;
            statWilEl.textContent = playerData.stats["의지력"] || 5;
            statVitEl.textContent = playerData.stats["체력"] || 5;
            statChaEl.textContent = playerData.stats["매력"] || 5;
        }
    }

    // 5. UI Update Functions (Part 4: Inventory)
    function updateInventoryUI(inventoryArray) {
        inventoryListEl.innerHTML = ''; // Clear existing items
        if (inventoryArray && inventoryArray.length > 0) {
            inventoryArray.forEach(item => {
                const li = document.createElement('li');
                // Assuming item is a string or an object with a 'name' property
                li.textContent = typeof item === 'string' ? item : `${item.name} (${item.effect || 'no effect'})`;
                inventoryListEl.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'Your inventory is empty.';
            inventoryListEl.appendChild(li);
        }
    }

    // 5. UI Update Functions (Part 5: Quests)
    function updateQuestsUI(activeQuestsArray) {
        questsListEl.innerHTML = ''; // Clear existing quests
        if (activeQuestsArray && activeQuestsArray.length > 0) {
            activeQuestsArray.forEach(quest => {
                const questDiv = document.createElement('div');
                questDiv.classList.add('quest-item'); // For potential specific styling
                
                const questName = document.createElement('h5');
                questName.textContent = quest.name || 'Unnamed Quest';
                
                const questDesc = document.createElement('p');
                questDesc.textContent = quest.description || 'No description.';
                
                const questStatus = document.createElement('small');
                questStatus.textContent = `Status: ${quest.status || 'N/A'}`;
                
                questDiv.appendChild(questName);
                questDiv.appendChild(questDesc);
                questDiv.appendChild(questStatus);
                questsListEl.appendChild(questDiv);
            });
        } else {
            const p = document.createElement('p');
            p.textContent = 'No active quests.';
            questsListEl.appendChild(p);
        }
    }

    // 5. UI Update Functions (Part 6: Item Image)
    function updateItemImage(imageUrl) {
        if (imageUrl) {
            itemImageEl.src = imageUrl;
            itemImageEl.style.display = 'block';
            itemImagePlaceholderEl.style.display = 'none';
        } else {
            itemImageEl.src = '#'; // Clear src
            itemImageEl.style.display = 'none';
            itemImagePlaceholderEl.style.display = 'block';
        }
    }

    // 3. initializeGame() Function
    async function initializeGame() {
        addMessageToChat("Initializing game...", "system-message");
        try {
            const response = await fetch(`${API_BASE_URL}/game/initialize`, { method: 'POST' });
            if (!response.ok) {
                const errorData = await response.json().catch(() => null); // Try to parse error, default to null
                throw new Error(`Initialization failed: ${response.status} ${response.statusText}. ${errorData ? errorData.detail : ''}`);
            }
            const gameState = await response.json();

            // Assuming gameState has player_data, history, npcs, shop_items
            updatePlayerStatsUI(gameState.player_data);
            updateInventoryUI(gameState.player_data.inventory); // inventory is part of player_data
            updateQuestsUI(gameState.player_data.active_quests); // active_quests is part of player_data
            
            // Initialize image display (likely no image at start)
            updateItemImage(null); 

            // Display history after other UI elements are set up
            if (gameState.history) {
                displayHistory(gameState.history);
            }
            addMessageToChat("Game initialized. Welcome to Life RPG!", "system-message");

        } catch (error) {
            console.error("Initialization Error:", error);
            addMessageToChat(`Error initializing game: ${error.message}`, 'error-message');
        }
    }

    // 4. sendMessage() Function
    async function sendMessage() {
        const messageText = playerInputEl.value.trim();
        if (!messageText) return;

        addMessageToChat(`${messageText}`, 'player-message'); // Displayed as "You: messageText" by style
        playerInputEl.value = ''; // Clear input field

        try {
            const response = await fetch(`${API_BASE_URL}/game/send_message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageText })
            });

            if (!response.ok) {
                 const errorData = await response.json().catch(() => null); // Try to parse JSON error response
                 throw new Error(errorData ? errorData.detail : `Message send failed: ${response.status} ${response.statusText}`);
            }
            const data = await response.json();

            if(data.command_response) {
                 addMessageToChat(data.command_response, 'system-message');
            }
            
            if (data.gm_response) { // GM response might be empty for some commands
                addMessageToChat(`${data.gm_response}`, 'gm-message');
            }

            if (data.quest_updates && data.quest_updates.length > 0) {
                data.quest_updates.forEach(update => addMessageToChat(update, 'system-message'));
            }
            if (data.new_achievements && data.new_achievements.length > 0) {
                data.new_achievements.forEach(ach => addMessageToChat(`Achievement unlocked: ${ach.name || ach}!`, 'system-message'));
            }
            
            updatePlayerStatsUI(data.player_data);
            updateInventoryUI(data.player_data.inventory);
            updateQuestsUI(data.player_data.active_quests);
            updateItemImage(data.image_url);

        } catch (error) {
            console.error("Send Message Error:", error);
            addMessageToChat(`Error: ${error.message}`, 'error-message');
        }
    }

    // Event Listeners
    sendButtonEl.addEventListener('click', sendMessage);
    playerInputEl.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    // Initial game load
    initializeGame();

    // --- Character Creation Modal Logic ---
    const characterCreationModalEl = document.getElementById('character-creation-modal');
    const closeModalButtonEl = document.getElementById('close-modal-button');
    const confirmCreationButtonEl = document.getElementById('confirm-creation-button');
    const remainingPointsEl = document.getElementById('remaining-points');
    const modalErrorMessageEl = document.getElementById('modal-error-message');

    const statInputs = {
        "힘": document.getElementById('stat-힘-input'),
        "지능": document.getElementById('stat-지능-input'),
        "의지력": document.getElementById('stat-의지력-input'),
        "체력": document.getElementById('stat-체력-input'),
        "매력": document.getElementById('stat-매력-input')
    };
    const statValueSpans = {
        "힘": document.getElementById('stat-힘-value'),
        "지능": document.getElementById('stat-지능-value'),
        "의지력": document.getElementById('stat-의지력-value'),
        "체력": document.getElementById('stat-체력-value'),
        "매력": document.getElementById('stat-매력-value')
    };

    const TOTAL_ALLOCATABLE_POINTS = 25; // As per backend validation

    function openCharacterCreationModal() {
        // Reset to default or load current stats if viewing
        // For now, always reset to a default valid state for creation
        Object.values(statInputs).forEach(input => input.value = 5);
        updateRemainingPoints(); // This will also update value spans
        modalErrorMessageEl.textContent = '';
        modalErrorMessageEl.style.display = 'none';
        characterCreationModalEl.classList.remove('hidden');
        characterCreationModalEl.style.display = 'block'; // Ensure visible
    }

    function closeCharacterCreationModal() {
        characterCreationModalEl.classList.add('hidden');
        characterCreationModalEl.style.display = 'none'; // Ensure hidden
    }

    function updateRemainingPoints() {
        let pointsUsed = 0;
        Object.values(statInputs).forEach(input => {
            let value = parseInt(input.value, 10);
            if (isNaN(value)) value = 0;
            // Enforce min/max at input level
            if (value < 1) { input.value = 1; value = 1;}
            if (value > 15) { input.value = 15; value = 15;}
            pointsUsed += value;
            // Update individual stat value display
            const statName = input.dataset.statName;
            if (statValueSpans[statName]) {
                statValueSpans[statName].textContent = input.value;
            }
        });

        const remaining = TOTAL_ALLOCATABLE_POINTS - pointsUsed;
        remainingPointsEl.textContent = remaining;

        if (remaining === 0) {
            confirmCreationButtonEl.disabled = false;
            modalErrorMessageEl.textContent = '';
            modalErrorMessageEl.style.display = 'none';
        } else {
            confirmCreationButtonEl.disabled = true;
            modalErrorMessageEl.textContent = `You must use all ${TOTAL_ALLOCATABLE_POINTS} points. Remaining: ${remaining}`;
            modalErrorMessageEl.style.display = 'block';
        }
    }

    characterCreationButtonEl.addEventListener('click', openCharacterCreationModal);
    closeModalButtonEl.addEventListener('click', closeCharacterCreationModal);

    Object.values(statInputs).forEach(input => {
        input.addEventListener('input', updateRemainingPoints);
    });

    confirmCreationButtonEl.addEventListener('click', async () => {
        const statsPayload = {};
        let currentTotal = 0;
        for (const [name, inputEl] of Object.entries(statInputs)) {
            const value = parseInt(inputEl.value, 10);
            if (value < 1 || value > 15) {
                modalErrorMessageEl.textContent = `Stat ${name} must be between 1 and 15.`;
                modalErrorMessageEl.style.display = 'block';
                return;
            }
            statsPayload[name] = value;
            currentTotal += value;
        }

        if (currentTotal !== TOTAL_ALLOCATABLE_POINTS) {
            modalErrorMessageEl.textContent = `Total points must be exactly ${TOTAL_ALLOCATABLE_POINTS}. Current: ${currentTotal}`;
            modalErrorMessageEl.style.display = 'block';
            return;
        }
        modalErrorMessageEl.textContent = '';
        modalErrorMessageEl.style.display = 'none';

        try {
            const response = await fetch(`${API_BASE_URL}/game/character_creation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ stats: statsPayload })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Unknown error during character creation." }));
                throw new Error(errorData.detail || `Character creation failed: ${response.status}`);
            }

            const updatedPlayerData = await response.json();
            updatePlayerStatsUI(updatedPlayerData); // Update main UI
            // If initializeGame also updates global state, ensure consistency or reload full state
            // For now, just update the stats shown.
            addMessageToChat("Character stats successfully set!", "system-message");
            closeCharacterCreationModal();

        } catch (error) {
            console.error("Character Creation Error:", error);
            modalErrorMessageEl.textContent = error.message;
            modalErrorMessageEl.style.display = 'block';
            // Optionally, also show in main chat if modal might be closed by user
            // addMessageToChat(`Character creation error: ${error.message}`, 'error-message');
        }
    });
    
    // Hide modal on outside click (optional)
    window.addEventListener('click', (event) => {
        if (event.target === characterCreationModalEl) {
            closeCharacterCreationModal();
        }
    });

    // --- Help Button Logic ---
    helpButtonEl.addEventListener('click', () => {
        const helpText = `
=== Life RPG Help ===

[Gameplay]
- Interact with the Game Master (GM) by typing messages.
- The GM will give you quests, rewards, and tell a story.
- Complete quests to earn XP, Gold, and Items.
- Level up to get stronger and allocate stat points.

[Stats]
- Strength (힘): Affects physical tasks.
- Intelligence (지능): Affects knowledge-based tasks and learning.
- Willpower (의지력): Affects mental fortitude and magic.
- Health (체력): Affects your hit points and endurance.
- Charisma (매력): Affects social interactions and persuasion.

[Core Actions]
- Character Creation: Click 'Character Creation' to set your initial stats.
- Send Message: Type your message and click 'Send' or press Enter.
- Reset Game: Click 'Reset Game' to start over (requires confirmation).

[Slash Commands (Type in input field)]
  (Note: The backend currently supports /능력치분배, /능력치설정, /스탯, /인벤토리.
   The frontend doesn't explicitly parse these, but the backend will respond if you send them.)
- /스탯 : Shows your current stats (GM will respond).
- /인벤토리 : Shows your inventory (GM will respond).
        `;
        alert(helpText);
    });

    // --- Reset Game Button Logic ---
    resetGameButtonEl.addEventListener('click', async () => {
        if (confirm("Are you sure you want to reset all game progress? This cannot be undone.")) {
            try {
                const response = await fetch(`${API_BASE_URL}/game/reset`, { method: 'POST' });
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: "Unknown error during game reset." }));
                    throw new Error(errorData.detail || `Game reset failed: ${response.status}`);
                }
                // Backend should return a success message or the reset state.
                // Forcing a full re-initialization from frontend.
                addMessageToChat("Game has been reset.", "system-message");
                
                // Clear current chat display before initializing
                chatDisplayEl.innerHTML = ''; 
                
                // Re-initialize the game, which will fetch new state and update UI
                await initializeGame(); 
                // initializeGame adds its own "Initializing..." and "Game initialized" messages.
                // Consider if we want to avoid duplicate messages or if it's fine.

            } catch (error) {
                console.error("Reset Game Error:", error);
                addMessageToChat(`Error resetting game: ${error.message}`, 'error-message');
            }
        }
    });

    // Review and Refine UI Update Functions (already implemented with clearing and empty states)
    // updatePlayerStatsUI: Updates textContent, so implicitly clears old. Handles nullish values for defaults.
    // updateInventoryUI: Sets inventoryListEl.innerHTML = ''; Clears old. Handles empty array.
    // updateQuestsUI: Sets questsListEl.innerHTML = ''; Clears old. Handles empty array.
    // These functions seem robust enough for reset scenarios.
    // One addition to initializeGame: clear chat before loading history.
    // This will be handled in the reset logic by clearing chat then calling initializeGame.

});
```
