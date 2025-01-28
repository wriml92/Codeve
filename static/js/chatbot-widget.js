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
// <img src="{% static 'images/codeve_icon.png' alt="챗봇" %} 기존 icon img 로딩방식
    getWidgetTemplate() {
        return `
            <div class="chat-toggle">
                <button id="chat-toggle-btn">
		    <img id="chatbot-icon" src="https://s3.ap-northeast-2.amazonaws.com/codeve.site/static/images/codeve_icon.png" alt="챗봇">
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

    displayMessage(text, type, isLoading = false) {
        const { messagesContainer } = this.elements;
        const messageDiv = document.createElement('div');
        messageDiv.className = type;
        messageDiv.textContent = isLoading ? '...' : text;
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom(messagesContainer);
        
        if (!isLoading) {
            this.saveChatHistory(text, type);
        }
        
        return messageDiv;
    }

    async sendMessage(message) {
        const messageText = message.trim();
        if (!messageText) return;

        const { input, messagesContainer } = this.elements;
        input.value = '';

        this.displayMessage(messageText, 'user-message');

        try {
            const botMessageDiv = this.displayMessage('', 'bot-message', true);
            const response = await this.fetchBotResponse(messageText);
            botMessageDiv.textContent = response;
            this.saveChatHistory(response, 'bot-message');
            
            this.scrollToBottom(messagesContainer);
        } catch (error) {
            console.error('Error:', error);
            this.displayMessage('죄송합니다. 오류가 발생했습니다.', 'error-message');
        }
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

    showChatNotification(message, type = '') {
        const { container } = this.elements;
        const existingNotification = container.querySelector('.chat-notification');
        existingNotification?.remove();

        const notification = document.createElement('div');
        notification.className = `chat-notification ${type}`;
        notification.textContent = message;
        container.appendChild(notification);

        setTimeout(() => notification.remove(), 5000);
    }

    scrollToBottom(element) {
        if (!element) return;
        
        element.scrollTop = element.scrollHeight;
        
        setTimeout(() => {
            element.scrollTop = element.scrollHeight;
        }, 100);
        
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

    handleStorage(action, data = null) {
        const STORAGE_KEY = 'chatHistory';
        
        if (action === 'save') {
            let chatHistory = this.handleStorage('get');
            chatHistory.push({
                message: data.message,
                type: data.type,
                timestamp: new Date().toISOString()
            });

            if (chatHistory.length > this.MAX_HISTORY) {
                chatHistory = chatHistory.slice(-this.MAX_HISTORY);
            }
            localStorage.setItem(STORAGE_KEY, JSON.stringify(chatHistory));
        } else if (action === 'get') {
            const history = localStorage.getItem(STORAGE_KEY);
            return history ? JSON.parse(history) : [];
        } else if (action === 'clear') {
            localStorage.removeItem(STORAGE_KEY);
        }
    }

    saveChatHistory(message, type) {
        this.handleStorage('save', { message, type });
    }

    getChatHistory() {
        return this.handleStorage('get');
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
}

function handleLogout(event) {
    event.preventDefault();
    const widget = document.querySelector('.chatbot-widget');
    
    if (widget) {
        widget.remove();
        localStorage.removeItem('chatHistory');
    }
    
    document.getElementById('logout-form').submit();
}
