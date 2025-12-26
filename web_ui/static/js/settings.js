/**
 * Settings Page JavaScript
 * Feature toggles and configuration
 */

let togglesState = {};
let settingsRefreshInterval = null;

// ==========================================
// Data Loading Functions
// ==========================================

async function loadToggles() {
    try {
        const response = await fetch('/api/toggles');
        const data = await response.json();
        
        if (data.status === 'ok') {
            togglesState = data.toggles || {};
            displayToggles();
        } else {
            showNotification('Failed to load toggles: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Failed to load toggles:', error);
        showNotification('Failed to load toggles: ' + error.message, 'error');
        document.getElementById('toggles-list').innerHTML = `
            <div class="empty-state">
                <p class="text-error">Failed to load feature toggles</p>
            </div>
        `;
    }
}

async function loadSystemInfo() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.status === 'ok') {
            updateSystemInfo(data);
        }
    } catch (error) {
        console.error('Failed to load system info:', error);
    }
}

// ==========================================
// Display Functions
// ==========================================

function displayToggles() {
    const container = document.getElementById('toggles-list');
    
    const toggleNames = {
        'notion_publishing': {
            name: 'Notion Publishing',
            description: 'Automatically publish reports to Notion',
            icon: '📝'
        },
        'task_execution': {
            name: 'Task Execution',
            description: 'Enable autonomous task execution',
            icon: '⚡'
        },
        'insights_extraction': {
            name: 'Insights Extraction',
            description: 'Extract and save insights from analysis',
            icon: '💡'
        }
    };
    
    if (Object.keys(togglesState).length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No feature toggles available</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = Object.entries(togglesState).map(([key, enabled]) => {
        const info = toggleNames[key] || { name: key, description: '', icon: '⚙️' };
        
        return `
            <div class="toggle-card">
                <div class="toggle-icon">${info.icon}</div>
                <div class="toggle-info">
                    <div class="toggle-name">${info.name}</div>
                    <div class="toggle-description">${info.description}</div>
                </div>
                <div class="toggle-control">
                    <label class="toggle-switch">
                        <input type="checkbox" 
                               id="toggle-${key}" 
                               ${enabled ? 'checked' : ''} 
                               onchange="toggleFeature('${key}', this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                    <span class="toggle-label">${enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateSystemInfo(data) {
    // Database status
    const dbStatus = document.getElementById('db-status');
    if (dbStatus) {
        dbStatus.textContent = data.status === 'ok' ? 'Connected' : 'Error';
        dbStatus.className = 'info-value ' + (data.status === 'ok' ? 'status-success' : 'status-error');
    }
    
    // Total reports
    const totalReports = document.getElementById('total-reports');
    if (totalReports && data.health && data.health.reports) {
        totalReports.textContent = data.health.reports.total || '0';
    }
    
    // Total tasks
    const totalTasks = document.getElementById('total-tasks');
    if (totalTasks && data.health && data.health.tasks) {
        const tasks = data.health.tasks;
        const total = (tasks.ready_now || 0) + (tasks.scheduled_future || 0);
        totalTasks.textContent = total;
    }
    
    // Last update
    const lastUpdate = document.getElementById('last-update');
    if (lastUpdate && data.timestamp) {
        lastUpdate.textContent = formatTimeAgo(data.timestamp);
    }
}

// ==========================================
// User Actions
// ==========================================

async function toggleFeature(feature, enabled) {
    try {
        // Map feature key to API endpoint
        const featureMap = {
            'notion_publishing': 'notion',
            'task_execution': 'tasks',
            'insights_extraction': 'insights'
        };
        
        const apiFeature = featureMap[feature] || feature;
        
        const response = await fetch(`/api/toggles/${apiFeature}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enabled: enabled })
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            showNotification(
                `Feature ${enabled ? 'enabled' : 'disabled'}: ${feature}`,
                'success'
            );
            
            // Update local state
            togglesState[feature] = enabled;
            displayToggles();
        } else {
            showNotification('Failed to toggle feature: ' + data.message, 'error');
            
            // Revert checkbox state
            const checkbox = document.getElementById(`toggle-${feature}`);
            if (checkbox) {
                checkbox.checked = !enabled;
            }
        }
    } catch (error) {
        console.error('Failed to toggle feature:', error);
        showNotification('Failed to toggle feature: ' + error.message, 'error');
        
        // Revert checkbox state
        const checkbox = document.getElementById(`toggle-${feature}`);
        if (checkbox) {
            checkbox.checked = !enabled;
        }
    }
}

function refreshToggles() {
    loadToggles();
    loadSystemInfo();
    showNotification('Settings refreshed', 'success');
}

// ==========================================
// Initialization
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // Load initial data
    loadToggles();
    loadSystemInfo();
    
    // Set up auto-refresh every 30 seconds
    settingsRefreshInterval = setInterval(() => {
        loadToggles();
        loadSystemInfo();
    }, 30000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (settingsRefreshInterval) {
        clearInterval(settingsRefreshInterval);
    }
});
