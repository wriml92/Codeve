class ChatbotWidget {
    constructor() {
        this.createWidget();
        this.isOpen = false;
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

        // 새로운 메시지 요소 생성
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'user-message';
        userMessageDiv.textContent = message;
        messagesContainer.appendChild(userMessageDiv);

        // 스크롤 최하단으로 이동
        this.scrollToBottom(messagesContainer);

        input.value = '';

        try {
            const response = await fetch('/api/chatbot/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            
            // 봇 응답 요소 생성
            const botMessageDiv = document.createElement('div');
            botMessageDiv.className = 'bot-message';
            botMessageDiv.textContent = data.response;
            messagesContainer.appendChild(botMessageDiv);

            // 스크롤 최하단으로 이동
            this.scrollToBottom(messagesContainer);
        } catch (error) {
            console.error('Error:', error);
        }
    }

    // 스크롤을 최하단으로 이동시키는 헬퍼 함수
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
} 