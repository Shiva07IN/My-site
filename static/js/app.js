// Initialize AOS
AOS.init({
    duration: 800,
    easing: 'ease-out-cubic',
    once: true,
    offset: 100
});

// Enhanced Custom Cursor - Desktop Only
class CustomCursor {
    constructor() {
        // Only initialize on desktop devices
        if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
            this.cursor = document.querySelector('.cursor');
            this.cursorFollower = document.querySelector('.cursor-follower');
            this.init();
        }
    }
    
    init() {
        if (!this.cursor || !this.cursorFollower) return;
        
        document.addEventListener('mousemove', this.handleMouseMove.bind(this));
        document.addEventListener('mouseenter', this.handleMouseEnter.bind(this));
        document.addEventListener('mouseleave', this.handleMouseLeave.bind(this));
        
        const interactiveElements = document.querySelectorAll('a, button, .btn, .doc-card, .feature-card, .send-btn');
        
        interactiveElements.forEach(element => {
            element.addEventListener('mouseenter', () => {
                this.cursor.style.transform = 'scale(1.5)';
                this.cursorFollower.style.transform = 'scale(0.5)';
            });
            
            element.addEventListener('mouseleave', () => {
                this.cursor.style.transform = 'scale(1)';
                this.cursorFollower.style.transform = 'scale(1)';
            });
        });
    }
    
    handleMouseMove(e) {
        this.cursor.style.left = e.clientX + 'px';
        this.cursor.style.top = e.clientY + 'px';
        
        setTimeout(() => {
            this.cursorFollower.style.left = e.clientX + 'px';
            this.cursorFollower.style.top = e.clientY + 'px';
        }, 100);
    }
    
    handleMouseEnter() {
        this.cursor.style.opacity = '1';
        this.cursorFollower.style.opacity = '1';
    }
    
    handleMouseLeave() {
        this.cursor.style.opacity = '0';
        this.cursorFollower.style.opacity = '0';
    }
}

// Enhanced Navbar
class EnhancedNavbar {
    constructor() {
        this.navbar = document.querySelector('.navbar');
        this.init();
    }
    
    init() {
        this.setupScrollEffect();
        this.setupActiveLink();
        this.setupSmoothScroll();
    }
    
    setupScrollEffect() {
        let lastScrollY = window.scrollY;
        
        window.addEventListener('scroll', () => {
            const currentScrollY = window.scrollY;
            
            if (currentScrollY > 100) {
                this.navbar.classList.add('scrolled');
            } else {
                this.navbar.classList.remove('scrolled');
            }
            
            if (currentScrollY > lastScrollY && currentScrollY > 200) {
                this.navbar.style.transform = 'translateY(-100%)';
            } else {
                this.navbar.style.transform = 'translateY(0)';
            }
            
            lastScrollY = currentScrollY;
        });
    }
    
    setupActiveLink() {
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-link');
        
        window.addEventListener('scroll', () => {
            let current = '';
            
            sections.forEach(section => {
                const sectionTop = section.offsetTop - 100;
                if (window.pageYOffset >= sectionTop) {
                    current = section.getAttribute('id');
                }
            });
            
            navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${current}`) {
                    link.classList.add('active');
                }
            });
        });
    }
    
    setupSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    const offsetTop = target.offsetTop - 80;
                    window.scrollTo({
                        top: offsetTop,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }
}

// Chat System
class ChatSystem {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.documentType = document.getElementById('documentType');
        this.init();
    }
    
    init() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        const docType = this.documentType.value;
        
        if (!message) return;
        
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.showTypingIndicator();
        this.sendButton.disabled = true;
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    document_type: docType
                })
            });
            
            const data = await response.json();
            
            this.hideTypingIndicator();
            
            if (response.ok) {
                this.addAIMessage(data.response, docType, message);
            } else {
                this.addMessage(`Error: ${data.error}`, 'ai');
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage(`Error: ${error.message}`, 'ai');
        } finally {
            this.sendButton.disabled = false;
        }
    }
    
    addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (typeof content === 'string') {
            messageContent.innerHTML = `<p>${content}</p>`;
        } else {
            messageContent.appendChild(content);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    addAIMessage(response, docType, originalMessage) {
        const responseContent = document.createElement('div');
        responseContent.innerHTML = `
            <p>${response}</p>
            <div class="response-actions" style="margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <button class="btn-small btn-primary" onclick="generateDocument('${docType}', '${originalMessage}')">
                    <i class="fas fa-download"></i> Generate PDF
                </button>
            </div>
        `;
        
        this.addMessage(responseContent, 'ai');
        this.addButtonStyles();
    }
    
    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message ai-message typing-indicator';
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(typingDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        
        const style = document.createElement('style');
        style.textContent = `
            .typing-dots {
                display: flex;
                gap: 4px;
                padding: 1rem;
            }
            .typing-dots span {
                width: 8px;
                height: 8px;
                background: var(--primary);
                border-radius: 50%;
                animation: typing 1.4s infinite ease-in-out;
            }
            .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
            .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
            @keyframes typing {
                0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
                40% { transform: scale(1); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    addButtonStyles() {
        if (document.getElementById('chat-button-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'chat-button-styles';
        style.textContent = `
            .btn-small {
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 6px;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
            }
            .btn-small.btn-primary {
                background: var(--primary);
                color: white;
            }
            .btn-small:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }
        `;
        document.head.appendChild(style);
    }
}

// Document Generation Functions
async function generateDocument(docType, message) {
    try {
        showNotification('Generating document...', 'info');
        
        const response = await fetch('/api/generate-document', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                document_type: docType
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.pdf_path) {
            try {
                // Properly encode the PDF path for URL
                const encodedPath = encodeURIComponent(data.pdf_path);
                const downloadUrl = `/api/download/${encodedPath}`;
                console.log('Downloading from:', downloadUrl);
                console.log('Original path:', data.pdf_path);
                
                const downloadResponse = await fetch(downloadUrl);
                
                if (!downloadResponse.ok) {
                    const errorText = await downloadResponse.text();
                    console.error('Download response error:', errorText);
                    throw new Error(`Download failed: ${downloadResponse.status} - ${errorText}`);
                }
                
                const contentType = downloadResponse.headers.get('content-type');
                console.log('Content type:', contentType);
                
                if (!contentType || !contentType.includes('application/pdf')) {
                    const errorText = await downloadResponse.text();
                    console.error('Invalid content type:', contentType, errorText);
                    throw new Error('Invalid file type received');
                }
                
                const blob = await downloadResponse.blob();
                console.log('Blob size:', blob.size);
                
                if (blob.size === 0) {
                    throw new Error('Downloaded file is empty');
                }
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = data.filename || `document_${Date.now()}.pdf`;
                a.style.display = 'none';
                
                // Trigger download
                document.body.appendChild(a);
                a.click();
                
                // Clean up
                setTimeout(() => {
                    if (document.body.contains(a)) {
                        document.body.removeChild(a);
                    }
                    window.URL.revokeObjectURL(url);
                }, 1000);
                
                showNotification('Document generated and downloaded successfully!', 'success');
                
            } catch (downloadError) {
                console.error('Download error details:', downloadError);
                showNotification(`Download failed: ${downloadError.message}`, 'error');
            }
        } else {
            console.error('Generation error:', data);
            showNotification(`Error: ${data.error || 'Unknown error occurred'}`, 'error');
        }
    } catch (error) {
        console.error('Request error:', error);
        showNotification(`Error: ${error.message}`, 'error');
    }
}

function selectDocumentType(docType) {
    document.getElementById('documentType').value = docType;
    document.getElementById('chat').scrollIntoView({ behavior: 'smooth' });
    // Only focus on desktop to prevent keyboard popup on mobile
    if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
        document.getElementById('messageInput').focus();
    }
}

function startChat() {
    document.getElementById('chat').scrollIntoView({ behavior: 'smooth' });
    // Only focus on desktop to prevent keyboard popup on mobile
    if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
        document.getElementById('messageInput').focus();
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    if (!document.getElementById('notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification {
                position: fixed;
                top: 100px;
                right: 20px;
                background: white;
                padding: 1rem 1.5rem;
                border-radius: var(--radius);
                box-shadow: var(--shadow-lg);
                z-index: 10001;
                animation: slideInRight 0.3s ease;
                border-left: 4px solid var(--primary);
            }
            .notification-success { border-left-color: var(--success); }
            .notification-error { border-left-color: var(--error); }
            .notification-info { border-left-color: var(--accent); }
            .notification-content {
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Initialize all systems
document.addEventListener('DOMContentLoaded', () => {
    new CustomCursor();
    new EnhancedNavbar();
    new ChatSystem();
    
    // Add scroll progress bar
    const progressBar = document.createElement('div');
    progressBar.className = 'scroll-progress';
    progressBar.innerHTML = '<div class="scroll-progress-bar"></div>';
    document.body.appendChild(progressBar);
    
    const progressBarFill = progressBar.querySelector('.scroll-progress-bar');
    
    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset;
        const docHeight = document.body.scrollHeight - window.innerHeight;
        const scrollPercent = (scrollTop / docHeight) * 100;
        
        progressBarFill.style.width = scrollPercent + '%';
    });
    
    // Add progress bar styles
    const style = document.createElement('style');
    style.textContent = `
        .scroll-progress {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: rgba(255, 255, 255, 0.1);
            z-index: 9999;
        }
        
        .scroll-progress-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary), var(--accent));
            width: 0%;
            transition: width 0.1s ease;
        }
        
        .nav-link.active {
            color: var(--primary);
        }
        
        .nav-link.active::after {
            width: 100%;
        }
    `;
    document.head.appendChild(style);
    
    // Parallax effects - Desktop only for performance
    if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const parallaxElements = document.querySelectorAll('.gradient-orb');
            
            parallaxElements.forEach((element, index) => {
                const speed = 0.2 + (index * 0.1);
                element.style.transform = `translate3d(0, ${scrolled * speed}px, 0)`;
            });
        });
    }
    
    // Prevent zoom on double tap for iOS
    let lastTouchEnd = 0;
    document.addEventListener('touchend', function (event) {
        const now = (new Date()).getTime();
        if (now - lastTouchEnd <= 300) {
            event.preventDefault();
        }
        lastTouchEnd = now;
    }, false);
    
    // Prevent context menu on long press
    document.addEventListener('contextmenu', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        e.preventDefault();
    });
});