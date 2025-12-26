/**
 * Common JavaScript utilities for all pages
 */

// Initialize WebSocket connection
const socket = io();

// Connection state management
socket.on('connect', () => {
    console.log('Connected to server');
    updateConnectionStatus('Connected', 'success');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateConnectionStatus('Disconnected', 'error');
});

socket.on('error', (data) => {
    console.error('Socket error:', data);
    showNotification('Error: ' + data.message, 'error');
});

// ==========================================
// Utility Functions
// ==========================================

function updateConnectionStatus(text, status = 'success') {
    const indicator = document.getElementById('status-indicator');
    if (!indicator) return;
    
    const statusText = indicator.querySelector('.status-text');
    const statusDot = indicator.querySelector('.status-dot');
    
    if (statusText) statusText.textContent = text;
    
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b'
    };
    
    if (statusDot) {
        statusDot.style.backgroundColor = colors[status] || colors.success;
    }
}

function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-xl);
        z-index: 9999;
        color: var(--text-primary);
        max-width: 400px;
    `;
    
    // Add type-specific styling
    const typeColors = {
        success: 'var(--success)',
        error: 'var(--error)',
        warning: 'var(--warning)',
        info: 'var(--info)'
    };
    
    if (typeColors[type]) {
        notification.style.borderLeftColor = typeColors[type];
        notification.style.borderLeftWidth = '4px';
    }
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function formatMarkdown(text) {
    if (!text) return '';
    
    // Basic markdown formatting
    return text
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
}

function formatDate(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

function formatDateTime(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatTimeAgo(dateString) {
    if (!dateString) return '--';
    
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    const intervals = {
        year: 31536000,
        month: 2592000,
        week: 604800,
        day: 86400,
        hour: 3600,
        minute: 60,
        second: 1
    };
    
    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
        const interval = Math.floor(seconds / secondsInUnit);
        if (interval >= 1) {
            return `${interval} ${unit}${interval !== 1 ? 's' : ''} ago`;
        }
    }
    
    return 'just now';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateTaskCount(count) {
    const badge = document.getElementById('task-count');
    if (badge) {
        badge.textContent = count || '0';
        badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
}

async function runAnalysis() {
    showNotification('Starting analysis...', 'info');
    updateConnectionStatus('Running analysis...', 'warning');
    try {
        const res = await fetch('/api/run', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
            showNotification('Analysis queued (PID: ' + data.pid + ')', 'success');
            setTimeout(() => {
                updateConnectionStatus('Connected', 'success');
            }, 3000);
        } else {
            showNotification('Failed to start analysis: ' + (data.message || 'unknown'), 'error');
            updateConnectionStatus('Error', 'error');
        }
    } catch (error) {
        console.error('Failed to run analysis:', error);
        showNotification('Analysis failed: ' + error.message, 'error');
        updateConnectionStatus('Error', 'error');
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .notification {
        animation: slideIn 0.3s ease-out;
    }
`;
document.head.appendChild(style);
