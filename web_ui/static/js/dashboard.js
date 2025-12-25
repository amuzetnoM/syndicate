/**
 * Gold Standard Web UI - Dashboard JavaScript
 * Real-time data updates and interactions
 */

// Initialize WebSocket connection
const socket = io();

// State management
let currentChart = 'GOLD';
let updateInterval = null;

// ==========================================
// Socket Event Handlers
// ==========================================

socket.on('connect', () => {
    console.log('Connected to server');
    updateStatus('Connected', 'success');
    loadAllData();
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateStatus('Disconnected', 'error');
});

socket.on('health_update', (data) => {
    updateHealthDisplay(data);
});

socket.on('error', (data) => {
    console.error('Socket error:', data);
    showNotification('Error: ' + data.message, 'error');
});

// ==========================================
// Data Loading Functions
// ==========================================

function loadAllData() {
    loadMetrics();
    loadJournal();
    loadTasks();
    loadStatus();
    loadChart(currentChart);
}

async function loadMetrics() {
    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();
        
        if (data.status === 'ok') {
            updateMetricsDisplay(data.metrics);
        }
    } catch (error) {
        console.error('Failed to load metrics:', error);
    }
}

async function loadJournal() {
    try {
        const response = await fetch('/api/journal');
        const data = await response.json();
        
        const journalContent = document.getElementById('journal-content');
        const journalDate = document.getElementById('journal-date');
        
        if (data.status === 'ok') {
            journalContent.innerHTML = formatMarkdown(data.content);
            journalDate.textContent = formatDate(data.date);
        } else {
            journalContent.innerHTML = `
                <div class="loading">
                    <p>No journal entry available for today.</p>
                    <p class="text-muted">Run analysis to generate.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Failed to load journal:', error);
        document.getElementById('journal-content').innerHTML = `
            <div class="loading">
                <p class="text-error">Failed to load journal</p>
            </div>
        `;
    }
}

async function loadTasks() {
    try {
        const response = await fetch('/api/tasks?limit=5');
        const data = await response.json();
        
        if (data.status === 'ok') {
            updateTasksDisplay(data);
            updateTaskCount(data.count.pending + data.count.ready);
        }
    } catch (error) {
        console.error('Failed to load tasks:', error);
    }
}

async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.status === 'ok') {
            updateHealthDisplay(data.health);
            updateRefreshTimer();
        }
    } catch (error) {
        console.error('Failed to load status:', error);
    }
}

async function loadChart(chartName) {
    try {
        const chartImage = document.getElementById('chart-image');
        const chartContainer = document.getElementById('chart-container');
        
        // Show loading
        chartContainer.classList.add('loading');
        
        // Update chart
        chartImage.src = `/charts/${chartName}.png?t=${Date.now()}`;
        chartImage.onload = () => {
            chartContainer.classList.remove('loading');
        };
        
        chartImage.onerror = () => {
            chartContainer.classList.remove('loading');
            chartImage.alt = 'Chart not available';
        };
        
        currentChart = chartName;
        
        // Update active tab
        document.querySelectorAll('.chart-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.chart === chartName);
        });
    } catch (error) {
        console.error('Failed to load chart:', error);
    }
}

// ==========================================
// Display Update Functions
// ==========================================

function updateMetricsDisplay(metrics) {
    // Gold Price
    const goldPrice = document.getElementById('gold-price');
    const goldChange = document.getElementById('gold-change');
    if (metrics.GOLD) {
        goldPrice.textContent = `$${metrics.GOLD.toFixed(2)}`;
    }
    
    // Silver Price
    const silverPrice = document.getElementById('silver-price');
    const silverChange = document.getElementById('silver-change');
    if (metrics.SILVER) {
        silverPrice.textContent = `$${metrics.SILVER.toFixed(2)}`;
    }
    
    // GSR
    const gsrValue = document.getElementById('gsr-value');
    if (metrics.GSR) {
        gsrValue.textContent = metrics.GSR.toFixed(2);
    }
    
    // Market Bias
    const marketBias = document.getElementById('market-bias');
    const biasUpdated = document.getElementById('bias-updated');
    if (metrics.bias) {
        marketBias.textContent = metrics.bias;
        marketBias.className = 'metric-value bias ' + metrics.bias.toLowerCase();
    }
    if (metrics.last_update) {
        biasUpdated.textContent = `Last updated: ${formatDate(metrics.last_update)}`;
    }
}

function updateTasksDisplay(data) {
    const tasksList = document.getElementById('tasks-list');
    
    const allTasks = [...(data.ready || []), ...(data.pending || [])].slice(0, 5);
    
    if (allTasks.length === 0) {
        tasksList.innerHTML = `
            <div class="loading">
                <p>No tasks pending</p>
            </div>
        `;
        return;
    }
    
    tasksList.innerHTML = allTasks.map(task => `
        <div class="task-item">
            <div class="task-header">
                <span class="task-type">${task.action_type || 'Task'}</span>
                <span class="task-status ${task.status || 'pending'}">${task.status || 'pending'}</span>
            </div>
            <div class="task-description">${escapeHtml(task.description || task.title || 'No description')}</div>
        </div>
    `).join('');
}

function updateHealthDisplay(health) {
    if (!health) return;
    
    // Reports count
    const reportsCount = document.getElementById('reports-count');
    if (health.reports) {
        reportsCount.textContent = health.reports.total || '0';
    }
    
    // Tasks
    const tasksPending = document.getElementById('tasks-pending');
    const tasksCompleted = document.getElementById('tasks-completed');
    if (health.tasks) {
        tasksPending.textContent = (health.tasks.ready_now || 0) + (health.tasks.scheduled_future || 0);
        tasksCompleted.textContent = health.tasks.completed_today || '0';
    }
    
    // Win rate
    const winRate = document.getElementById('win-rate');
    if (health.performance && health.performance.win_rate !== undefined) {
        winRate.textContent = `${health.performance.win_rate.toFixed(1)}%`;
    }
}

function updateTaskCount(count) {
    const badge = document.getElementById('task-count');
    badge.textContent = count || '0';
    badge.style.display = count > 0 ? 'inline-block' : 'none';
}

function updateStatus(text, status = 'success') {
    const indicator = document.getElementById('status-indicator');
    const statusText = indicator.querySelector('.status-text');
    const statusDot = indicator.querySelector('.status-dot');
    
    statusText.textContent = text;
    
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b'
    };
    
    statusDot.style.backgroundColor = colors[status] || colors.success;
}

function updateRefreshTimer() {
    const timer = document.getElementById('refresh-timer');
    if (timer) {
        timer.textContent = 'Updated: now';
    }
}

// ==========================================
// User Actions
// ==========================================

function refreshData() {
    loadAllData();
    showNotification('Data refreshed', 'success');
}

async function runAnalysis() {
    showNotification('Starting analysis...', 'info');
    updateStatus('Running analysis...', 'warning');
    
    try {
        // In a real implementation, this would trigger the analysis
        // For now, we'll simulate it
        setTimeout(() => {
            showNotification('Analysis completed', 'success');
            updateStatus('Connected', 'success');
            loadAllData();
        }, 2000);
    } catch (error) {
        console.error('Failed to run analysis:', error);
        showNotification('Analysis failed: ' + error.message, 'error');
        updateStatus('Error', 'error');
    }
}

// ==========================================
// Utility Functions
// ==========================================

function formatMarkdown(text) {
    if (!text) return '';
    
    // Basic markdown formatting
    return text
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Simple notification - could be enhanced with a toast library
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
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ==========================================
// Event Listeners
// ==========================================

// Chart tab switching
document.querySelectorAll('.chart-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const chartName = tab.dataset.chart;
        loadChart(chartName);
    });
});

// Auto-refresh every 30 seconds
updateInterval = setInterval(() => {
    loadMetrics();
    loadTasks();
    loadStatus();
}, 30000);

// Load initial data when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});
