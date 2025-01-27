class ChatbotWidget {
    constructor() {
        if (!this.isLoggedIn()) return;
        
        this.MAX_HISTORY = 20;
        this.isOpen = false;
        this.hasInitialMessage = false;
        
        this.initializeWidget();
    }

    isLoggedIn() {
        return document.body.classList.contains('user-logged-in');
    }

    initializeWidget() {
        this.createWidget();
        this.loadChatHistory();
    }

    createWidget() {
        const widget = document.createElement('div');
        widget.className = 'chatbot-widget';
        widget.innerHTML = this.getWidgetTemplate();
        document.body.appendChild(widget);
        this.bindEvents();
    }

    getWidgetTemplate() {
        return `
            <div class="chat-toggle">
                <button id="chat-toggle-btn">
                    <img src="/static/images/codeve_icon.png" alt="챗봇">
                </button>
            </div>
            <div class="chat-container" style="display: none;">
                <div class="chat-header">
                    <div class="title">코드이브 챗봇</div>
                    <button class="close-btn">∨</button>
                </div>
                <div class="chat-messages"></div>
                <div class="chat-input">
                    <input type="text" placeholder="메시지를 입력하세요...">
                    <button>전송</button>
                </div>
            </div>
        `;
    }

    bindEvents() {
        this.elements = {
            toggleBtn: document.getElementById('chat-toggle-btn'),
            toggleContainer: document.querySelector('.chat-toggle'),
            container: document.querySelector('.chat-container'),
            closeBtn: document.querySelector('.chat-header .close-btn'),
            sendBtn: document.querySelector('.chat-input button'),
            input: document.querySelector('.chat-input input'),
            messagesContainer: document.querySelector('.chat-messages')
        };

        this.elements.toggleBtn.addEventListener('click', () => this.handleToggle());
        this.elements.closeBtn.addEventListener('click', () => this.handleClose());
        this.elements.sendBtn.addEventListener('click', () => this.handleSend());
        this.elements.input.addEventListener('keypress', (e) => this.handleKeyPress(e));
    }

    handleToggle() {
        this.isOpen = !this.isOpen;
        if (!this.isOpen) return;

        const { toggleContainer, container, input, messagesContainer } = this.elements;
        
        toggleContainer.style.display = 'none';
        container.style.display = 'flex';
        
        if (!this.hasInitialMessage) {
            this.showWelcomeMessage();
            this.hasInitialMessage = true;
        }
        
        this.scrollToBottom(messagesContainer);
        input.focus();
    }

    handleClose() {
        this.isOpen = false;
        const { toggleContainer, container } = this.elements;
        toggleContainer.style.display = 'block';
        container.style.display = 'none';
    }

    handleSend() {
        const { input } = this.elements;
        this.sendMessage(input.value);
    }

    handleKeyPress(event) {
        if (event.key === 'Enter') {
            this.handleSend();
        }
    }

    showWelcomeMessage() {
        this.showChatNotification('코드이브입니다! 무엇이든 물어보세요 😊', 'welcome');
    }

    async sendMessage(message) {
        const messageText = message.trim();
        if (!messageText) return;

        const { messagesContainer, input } = this.elements;

        this.displayMessage(messageText, 'user-message');
        input.value = '';

        try {
            const botMessageDiv = this.createLoadingMessage();
            const response = await this.fetchBotResponse(messageText);
            
            this.updateBotMessage(botMessageDiv, response);
            this.saveChatHistory(response, 'bot-message');
        } catch (error) {
            console.error('Error:', error);
            this.showErrorMessage();
        }
    }

    createLoadingMessage() {
        const { messagesContainer } = this.elements;
        const botMessageDiv = document.createElement('div');
        botMessageDiv.className = 'bot-message';
        botMessageDiv.textContent = '...';
        messagesContainer.appendChild(botMessageDiv);
        this.scrollToBottom(messagesContainer);
        return botMessageDiv;
    }

    updateBotMessage(messageDiv, text) {
        messageDiv.textContent = text;
        this.scrollToBottom(this.elements.messagesContainer);
    }

    async fetchBotResponse(message) {
        const response = await fetch('/api/chatbot/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            },
            body: JSON.stringify({ message })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        return data.response;
    }

    showErrorMessage() {
        const { messagesContainer } = this.elements;
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = '죄송합니다. 오류가 발생했습니다.';
        messagesContainer.appendChild(errorDiv);
        this.scrollToBottom(messagesContainer);
    }

    scrollToBottom(element) {
        if (!element) return;
        requestAnimationFrame(() => {
            element.scrollTop = element.scrollHeight;
        });
    }

    getCookie(name) {
        if (!document.cookie) return null;
        
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [cookieName, cookieValue] = cookie.trim().split('=');
            if (cookieName === name) {
                return decodeURIComponent(cookieValue);
            }
        }
        return null;
    }

    displayMessage(text, className) {
        const { messagesContainer } = this.elements;
        const messageDiv = document.createElement('div');
        messageDiv.className = className;
        messageDiv.textContent = text;
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom(messagesContainer);
        this.saveChatHistory(text, className);
    }

    saveChatHistory(message, type) {
        let chatHistory = this.getChatHistory();
        chatHistory.push({
            message,
            type,
            timestamp: new Date().toISOString()
        });

        if (chatHistory.length > this.MAX_HISTORY) {
            chatHistory = chatHistory.slice(-this.MAX_HISTORY);
        }
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    }

    getChatHistory() {
        const history = localStorage.getItem('chatHistory');
        return history ? JSON.parse(history) : [];
    }

    loadChatHistory() {
        const chatHistory = this.getChatHistory();
        const { messagesContainer } = this.elements;
        
        if (!messagesContainer) return;

        chatHistory.forEach(item => {
            const messageDiv = document.createElement('div');
            messageDiv.className = item.type;
            messageDiv.textContent = item.message;
            messagesContainer.appendChild(messageDiv);
        });

        setTimeout(() => this.scrollToBottom(messagesContainer), 0);
    }

    showChatNotification(message, type = '') {
        const { container } = this.elements;
        const existingNotification = container.querySelector('.chat-notification');
        
        if (existingNotification) {
            existingNotification.remove();
        }

        const notification = document.createElement('div');
        notification.className = `chat-notification ${type}`;
        notification.textContent = message;
        container.appendChild(notification);

        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

function handleLogout(event) {
    event.preventDefault();
    localStorage.removeItem('chatHistory');
    
    const chatbotWidget = document.querySelector('.chatbot-widget');
    if (chatbotWidget) {
        chatbotWidget.remove();
    }
    
    document.getElementById('logout-form').submit();
}