class ChatbotWidget {
    constructor() {
        if (!this.isLoggedIn()) {
            return;
        }
        this.createWidget();
        this.isOpen = false;
        this.loadChatHistory();
        this.MAX_HISTORY = 10;
    }

    isLoggedIn() {
        return document.body.classList.contains('user-logged-in');
    }

    createWidget() {
        const widget = document.createElement('div');
        widget.className = 'chatbot-widget';
        widget.innerHTML = `
            <div class="chat-toggle">
                <button id="chat-toggle-btn">챗봇</button>
            </div>
            <div class="chat-container" style="display: none;">
                <div class="chat-messages"></div>
                <div class="chat-input">
                    <input type="text" placeholder="메시지를 입력하세요...">
                    <button>전송</button>
                </div>
            </div>
        `;
        document.body.appendChild(widget);
        
        this.bindEvents();
    }

    bindEvents() {
        const toggleBtn = document.getElementById('chat-toggle-btn');
        const container = document.querySelector('.chat-container');
        const sendBtn = document.querySelector('.chat-input button');
        const input = document.querySelector('.chat-input input');

        toggleBtn.addEventListener('click', () => {
            this.isOpen = !this.isOpen;
            if (this.isOpen) {
                container.style.display = 'flex';
                container.offsetHeight;
            } else {
                container.style.display = 'none';
            }
        });

        sendBtn.addEventListener('click', () => this.sendMessage(input.value));
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage(input.value);
        });
    }

    async sendMessage(message) {
        if (!message.trim()) return;

        const messagesContainer = document.querySelector('.chat-messages');
        const input = document.querySelector('.chat-input input');

        try {
            this.displayMessage(message, 'user-message');
            
            const botMessageDiv = document.createElement('div');
            botMessageDiv.className = 'bot-message';
            messagesContainer.appendChild(botMessageDiv);
            
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
            
            botMessageDiv.textContent = data.response;
            this.scrollToBottom(messagesContainer);
            
            input.value = '';
            this.saveChatHistory(data.response, 'bot-message');
            
        } catch (error) {
            console.error('Error:', error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = '죄송합니다. 오류가 발생했습니다.';
            messagesContainer.appendChild(errorDiv);
        }
    }

    scrollToBottom(element) {
        setTimeout(() => {
            element.scrollTop = element.scrollHeight;
        }, 100);
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    displayMessage(text, className) {
        const messagesContainer = document.querySelector('.chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = className;
        messageDiv.textContent = text;
        messagesContainer.appendChild(messageDiv);
        
        this.saveChatHistory(text, className);
    }

    saveChatHistory(message, type) {
        let chatHistory = this.getChatHistory();
        
        chatHistory.push({
            message: message,
            type: type,
            timestamp: new Date().toISOString()
        });

        if (chatHistory.length > this.MAX_HISTORY) {
            chatHistory = chatHistory.slice(-this.MAX_HISTORY);
        }

        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    }

    loadChatHistory() {
        const chatHistory = this.getChatHistory();
        const messagesContainer = document.querySelector('.chat-messages');
        
        if (messagesContainer) {
            chatHistory.forEach(item => {
                const messageDiv = document.createElement('div');
                messageDiv.className = item.type;
                messageDiv.textContent = item.message;
                messagesContainer.appendChild(messageDiv);
            });
            this.scrollToBottom(messagesContainer);
        }
    }

    getChatHistory() {
        const history = localStorage.getItem('chatHistory');
        return history ? JSON.parse(history) : [];
    }

    clearChatHistory() {
        localStorage.removeItem('chatHistory');
        const messagesContainer = document.querySelector('.chat-messages');
        if (messagesContainer) {
            messagesContainer.innerHTML = '';
        }
        console.log('Chat history cleared');
    }

    static clearOnLogout() {
        localStorage.removeItem('chatHistory');
        console.log('Chat history cleared on logout');
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