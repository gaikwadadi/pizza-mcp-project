// Chat Interface JavaScript
class PizzaChatInterface {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.messagesContainer = document.getElementById('messagesContainer');
        this.connectionStatus = document.getElementById('connectionStatus');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        this.initializeEventListeners();
        this.connect();
        this.setWelcomeTime();
    }

    initializeEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter key press
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Input focus/blur effects
        this.messageInput.addEventListener('focus', () => {
            this.messageInput.parentElement.style.borderColor = '#007bff';
        });

        this.messageInput.addEventListener('blur', () => {
            this.messageInput.parentElement.style.borderColor = '#e9ecef';
        });
    }

    connect() {
        try {
            this.ws = new WebSocket('ws://localhost:8001/ws');
            
            this.ws.onopen = () => {
                this.isConnected = true;
                this.updateConnectionStatus('Connected', 'connected');
                this.enableInput();
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleIncomingMessage(data);
            };

            this.ws.onclose = () => {
                this.isConnected = false;
                this.updateConnectionStatus('Disconnected', 'disconnected');
                this.disableInput();
                
                // Attempt to reconnect after 3 seconds
                setTimeout(() => {
                    if (!this.isConnected) {
                        this.updateConnectionStatus('Reconnecting...', 'disconnected');
                        this.connect();
                    }
                }, 3000);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus('Connection Error', 'disconnected');
            };

        } catch (error) {
            console.error('Failed to connect:', error);
            this.updateConnectionStatus('Failed to Connect', 'disconnected');
        }
    }

    updateConnectionStatus(text, className) {
        this.connectionStatus.textContent = text;
        this.connectionStatus.className = `status ${className}`;
    }

    enableInput() {
        this.messageInput.disabled = false;
        this.sendButton.disabled = false;
        this.messageInput.placeholder = 'Type your message here...';
    }

    disableInput() {
        this.messageInput.disabled = true;
        this.sendButton.disabled = true;
        this.messageInput.placeholder = 'Connecting...';
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || !this.isConnected) return;

        // Display user message
        this.displayMessage(message, 'user');
        
        // Clear input
        this.messageInput.value = '';
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Send to server
        this.ws.send(JSON.stringify({
            type: 'user_message',
            content: message,
            timestamp: new Date().toISOString()
        }));
    }

    handleIncomingMessage(data) {
        this.hideTypingIndicator();
        
        switch (data.type) {
            case 'bot_message':
                this.displayMessage(data.content, 'bot');
                break;
            case 'order_confirmation':
                this.displayOrderConfirmation(data.content);
                break;
            case 'menu_data':
                this.displayMenu(data.content);
                break;
            case 'error':
                this.displayMessage(`Sorry, there was an error: ${data.content}`, 'bot');
                break;
            default:
                this.displayMessage(data.content || 'Unknown message type', 'bot');
        }
    }

    displayMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messageText = document.createElement('p');
        messageText.textContent = content;
        
        const messageTime = document.createElement('span');
        messageTime.className = 'message-time';
        messageTime.textContent = this.formatTime(new Date());
        
        messageContent.appendChild(messageText);
        messageContent.appendChild(messageTime);
        messageDiv.appendChild(messageContent);
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    displayOrderConfirmation(orderData) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Order confirmation card
        const confirmationCard = document.createElement('div');
        confirmationCard.className = 'order-confirmation';
        confirmationCard.innerHTML = `
            <h4>🎉 Order Confirmed!</h4>
            <div class="order-details">
                <div class="order-detail">
                    <div class="order-detail-label">Order ID</div>
                    <div class="order-detail-value">#${orderData.order_id}</div>
                </div>
                <div class="order-detail">
                    <div class="order-detail-label">Total</div>
                    <div class="order-detail-value">₹${orderData.total_price}</div>
                </div>
                <div class="order-detail">
                    <div class="order-detail-label">Delivery Time</div>
                    <div class="order-detail-value">${orderData.delivery_time}</div>
                </div>
                <div class="order-detail">
                    <div class="order-detail-label">Status</div>
                    <div class="order-detail-value">Preparing</div>
                </div>
            </div>
        `;
        
        const messageTime = document.createElement('span');
        messageTime.className = 'message-time';
        messageTime.textContent = this.formatTime(new Date());
        
        messageContent.appendChild(confirmationCard);
        messageContent.appendChild(messageTime);
        messageDiv.appendChild(messageContent);
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    formatTime(date) {
        return date.toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
            timeZone: 'Asia/Kolkata'
        });
    }

    setWelcomeTime() {
        const welcomeTimeElement = document.getElementById('welcomeTime');
        if (welcomeTimeElement) {
            welcomeTimeElement.textContent = this.formatTime(new Date());
        }
    }
}

// Initialize chat interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PizzaChatInterface();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Reconnect if needed when page becomes visible
        setTimeout(() => {
            if (window.chatInterface && !window.chatInterface.isConnected) {
                window.chatInterface.connect();
            }
        }, 1000);
    }
});

// Store chat interface globally for debugging
window.addEventListener('load', () => {
    if (window.chatInterface) {
        window.chatInterface = chatInterface;
    }
});
