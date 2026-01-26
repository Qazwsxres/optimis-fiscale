/**
 * ========================================
 * NUMMA Messages System v3.0
 * ========================================
 * Professional notification system for user feedback
 * MUST BE LOADED FIRST - Required by all other modules
 */

(function() {
    'use strict';

    console.log('📢 Loading NUMMA Messages System...');

    // Global messages array
    window.nummaMessages = [];

    /**
     * Show notification message
     * @param {string} message - Message text
     * @param {string} type - Message type: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duration in ms (0 = permanent)
     */
    window.showMessage = function(message, type = 'info', duration = 5000) {
        const container = getOrCreateContainer();
        
        const messageEl = document.createElement('div');
        messageEl.className = `numma-message numma-message-${type}`;
        
        const icon = getIcon(type);
        
        messageEl.innerHTML = `
            <div class="numma-message-icon">${icon}</div>
            <div class="numma-message-text">${escapeHtml(message)}</div>
            <button class="numma-message-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        container.appendChild(messageEl);
        
        // Add to array
        window.nummaMessages.push({
            message,
            type,
            timestamp: new Date()
        });
        
        // Auto-remove if duration set
        if (duration > 0) {
            setTimeout(() => {
                messageEl.classList.add('numma-message-fade');
                setTimeout(() => messageEl.remove(), 300);
            }, duration);
        }
        
        return messageEl;
    };

    /**
     * Show success message
     */
    window.showSuccess = function(message, duration = 3000) {
        return window.showMessage(message, 'success', duration);
    };

    /**
     * Show error message
     */
    window.showError = function(message, duration = 5000) {
        return window.showMessage(message, 'error', duration);
    };

    /**
     * Show warning message
     */
    window.showWarning = function(message, duration = 4000) {
        return window.showMessage(message, 'warning', duration);
    };

    /**
     * Show info message
     */
    window.showInfo = function(message, duration = 3000) {
        return window.showMessage(message, 'info', duration);
    };

    /**
     * Clear all messages
     */
    window.clearMessages = function() {
        const container = document.getElementById('numma-messages-container');
        if (container) {
            container.innerHTML = '';
        }
        window.nummaMessages = [];
    };

    /**
     * Get or create messages container
     */
    function getOrCreateContainer() {
        let container = document.getElementById('numma-messages-container');
        
        if (!container) {
            container = document.createElement('div');
            container.id = 'numma-messages-container';
            container.className = 'numma-messages-container';
            document.body.appendChild(container);
        }
        
        return container;
    }

    /**
     * Get icon for message type
     */
    function getIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Add CSS styles
    const style = document.createElement('style');
    style.textContent = `
        .numma-messages-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        }

        .numma-message {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px 16px;
            margin-bottom: 10px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            background: white;
            border-left: 4px solid;
            animation: nummaSlideIn 0.3s ease;
            position: relative;
        }

        .numma-message-success {
            border-left-color: #10b981;
            background: #f0fdf4;
        }

        .numma-message-error {
            border-left-color: #ef4444;
            background: #fef2f2;
        }

        .numma-message-warning {
            border-left-color: #f59e0b;
            background: #fffbeb;
        }

        .numma-message-info {
            border-left-color: #3b82f6;
            background: #eff6ff;
        }

        .numma-message-icon {
            font-size: 20px;
            font-weight: bold;
            flex-shrink: 0;
        }

        .numma-message-success .numma-message-icon {
            color: #10b981;
        }

        .numma-message-error .numma-message-icon {
            color: #ef4444;
        }

        .numma-message-warning .numma-message-icon {
            color: #f59e0b;
        }

        .numma-message-info .numma-message-icon {
            color: #3b82f6;
        }

        .numma-message-text {
            flex: 1;
            font-size: 14px;
            color: #374151;
            line-height: 1.5;
        }

        .numma-message-close {
            background: none;
            border: none;
            font-size: 20px;
            color: #9ca3af;
            cursor: pointer;
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            transition: all 0.2s;
            flex-shrink: 0;
        }

        .numma-message-close:hover {
            background: rgba(0,0,0,0.05);
            color: #374151;
        }

        .numma-message-fade {
            animation: nummaSlideOut 0.3s ease forwards;
        }

        @keyframes nummaSlideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes nummaSlideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }

        @media (max-width: 768px) {
            .numma-messages-container {
                left: 10px;
                right: 10px;
                max-width: none;
            }
        }
    `;
    document.head.appendChild(style);

    console.log('✅ NUMMA Messages System loaded');
})();
