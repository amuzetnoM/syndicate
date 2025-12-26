/**
 * Tasks Page JavaScript
 * Full task management and monitoring
 */

let taskRefreshInterval = null;

// ==========================================
// Data Loading Functions
// ==========================================

async function loadAllTasks() {
    try {
        const response = await fetch('/api/tasks?limit=100');
        const data = await response.json();
        
        if (data.status === 'ok') {
            updateTaskStats(data.count);
            displayReadyTasks(data.ready || []);
            displayPendingTasks(data.pending || []);
            displayScheduledTasks(data.scheduled || []);
        } else {
            showNotification('Failed to load tasks: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Failed to load tasks:', error);
        showNotification('Failed to load tasks: ' + error.message, 'error');
    }
}

async function loadExecutionHistory() {
    try {
        const response = await fetch('/api/execution_history?days=7');
        const data = await response.json();
        
        if (data.status === 'ok') {
            displayExecutionHistory(data.history || []);
        }
    } catch (error) {
        console.error('Failed to load execution history:', error);
    }
}

async function loadSystemHealth() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.status === 'ok' && data.health) {
            updateCompletedCount(data.health.tasks?.completed_today || 0);
        }
    } catch (error) {
        console.error('Failed to load system health:', error);
    }
}

// ==========================================
// Display Functions
// ==========================================

function updateTaskStats(counts) {
    document.getElementById('stat-ready').textContent = counts.ready || 0;
    document.getElementById('stat-pending').textContent = counts.pending || 0;
    document.getElementById('stat-scheduled').textContent = counts.scheduled || 0;
    
    document.getElementById('ready-count').textContent = counts.ready || 0;
    document.getElementById('pending-count').textContent = counts.pending || 0;
    document.getElementById('scheduled-count').textContent = counts.scheduled || 0;
    
    // Update navigation badge
    updateTaskCount((counts.ready || 0) + (counts.pending || 0));
}

function updateCompletedCount(count) {
    document.getElementById('stat-completed').textContent = count || 0;
}

function displayReadyTasks(tasks) {
    const container = document.getElementById('ready-tasks-list');
    
    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No tasks ready for execution</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tasks.map(task => createTaskCard(task, 'ready')).join('');
}

function displayPendingTasks(tasks) {
    const container = document.getElementById('pending-tasks-list');
    
    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No pending tasks</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tasks.map(task => createTaskCard(task, 'pending')).join('');
}

function displayScheduledTasks(tasks) {
    const container = document.getElementById('scheduled-tasks-list');
    
    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No scheduled tasks</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tasks.map(task => createTaskCard(task, 'scheduled')).join('');
}

function displayExecutionHistory(history) {
    const container = document.getElementById('execution-history');
    
    if (history.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No recent execution history</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = history.slice(0, 20).map(entry => `
        <div class="history-entry ${entry.status || 'unknown'}">
            <div class="history-header">
                <span class="history-action">${escapeHtml(entry.action_type || 'Task')}</span>
                <span class="history-status status-${entry.status || 'unknown'}">${entry.status || 'unknown'}</span>
            </div>
            <div class="history-details">
                <span class="history-time">${formatDateTime(entry.executed_at || entry.timestamp)}</span>
                ${entry.result ? `<span class="history-result">${escapeHtml(entry.result)}</span>` : ''}
            </div>
            ${entry.error ? `<div class="history-error">${escapeHtml(entry.error)}</div>` : ''}
        </div>
    `).join('');
}

function createTaskCard(task, category) {
    const actionType = escapeHtml(task.action_type || task.title || 'Task');
    const description = escapeHtml(task.description || task.result || 'No description');
    const status = task.status || category;
    const priority = task.priority || 'normal';
    
    let scheduledInfo = '';
    if (task.scheduled_for) {
        scheduledInfo = `<div class="task-scheduled">Scheduled: ${formatDateTime(task.scheduled_for)}</div>`;
    }
    
    let retryInfo = '';
    if (task.retry_count && task.retry_count > 0) {
        retryInfo = `<div class="task-retry">Retries: ${task.retry_count}</div>`;
    }
    
    return `
        <div class="task-card priority-${priority}">
            <div class="task-card-header">
                <span class="task-type">${actionType}</span>
                <span class="task-status status-${status}">${status}</span>
            </div>
            <div class="task-card-body">
                <p class="task-description">${description}</p>
                ${scheduledInfo}
                ${retryInfo}
                ${task.created_at ? `<div class="task-meta">Created: ${formatTimeAgo(task.created_at)}</div>` : ''}
            </div>
        </div>
    `;
}

// ==========================================
// User Actions
// ==========================================

function refreshTasks() {
    loadAllTasks();
    loadExecutionHistory();
    loadSystemHealth();
    showNotification('Tasks refreshed', 'success');
}

// ==========================================
// Initialization
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // Load initial data
    loadAllTasks();
    loadExecutionHistory();
    loadSystemHealth();
    
    // Set up auto-refresh every 15 seconds
    taskRefreshInterval = setInterval(() => {
        loadAllTasks();
        loadSystemHealth();
    }, 15000);
    
    // Also refresh execution history every 30 seconds
    setInterval(() => {
        loadExecutionHistory();
    }, 30000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (taskRefreshInterval) {
        clearInterval(taskRefreshInterval);
    }
});
