/**
 * Analysis Page JavaScript
 * Charts, reports, and analysis viewing
 */

let currentChart = 'GOLD';
let analysisRefreshInterval = null;

// ==========================================
// Data Loading Functions
// ==========================================

async function loadAllAnalysisData() {
    loadChart(currentChart);
    loadChartsList();
    loadReports();
    loadJournal();
}

async function loadChart(chartName) {
    try {
        const chartImage = document.getElementById('chart-image');
        const chartContainer = document.getElementById('chart-container-large');
        
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
            chartImage.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><text x="50%" y="50%" text-anchor="middle" fill="%23666">Chart not available</text></svg>';
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

async function loadChartsList() {
    try {
        const response = await fetch('/api/charts');
        const data = await response.json();
        
        const container = document.getElementById('charts-list');
        
        if (data.status === 'ok' && data.charts && data.charts.length > 0) {
            container.innerHTML = data.charts.map(chart => `
                <div class="chart-list-item" onclick="loadChart('${chart.name}')">
                    <div class="chart-list-name">${escapeHtml(chart.name)}</div>
                    <div class="chart-list-meta">
                        <span class="chart-date">${formatTimeAgo(chart.modified)}</span>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No charts available</p>
                    <p class="text-muted">Run analysis to generate charts</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Failed to load charts list:', error);
        document.getElementById('charts-list').innerHTML = `
            <div class="empty-state">
                <p class="text-error">Failed to load charts</p>
            </div>
        `;
    }
}

async function loadReports() {
    try {
        const response = await fetch('/api/reports');
        const data = await response.json();
        
        const container = document.getElementById('reports-list');
        
        if (data.status === 'ok' && data.reports && data.reports.length > 0) {
            container.innerHTML = data.reports.slice(0, 10).map(report => `
                <div class="report-item">
                    <a href="${report.url}" target="_blank" class="report-link">
                        <div class="report-name">${escapeHtml(report.name)}</div>
                        <div class="report-meta">
                            <span class="report-date">${formatTimeAgo(report.modified)}</span>
                            <span class="report-size">${formatFileSize(report.size)}</span>
                        </div>
                    </a>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No reports available</p>
                    <p class="text-muted">Run analysis to generate reports</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Failed to load reports:', error);
        document.getElementById('reports-list').innerHTML = `
            <div class="empty-state">
                <p class="text-error">Failed to load reports</p>
            </div>
        `;
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
                <div class="empty-state">
                    <p>No journal entry available for today</p>
                    <p class="text-muted">Run analysis to generate</p>
                </div>
            `;
            journalDate.textContent = '';
        }
    } catch (error) {
        console.error('Failed to load journal:', error);
        document.getElementById('journal-content').innerHTML = `
            <div class="empty-state">
                <p class="text-error">Failed to load journal</p>
            </div>
        `;
    }
}

// ==========================================
// Utility Functions
// ==========================================

function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

// ==========================================
// User Actions
// ==========================================

function refreshAnalysis() {
    loadAllAnalysisData();
    showNotification('Analysis data refreshed', 'success');
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

// ==========================================
// Initialization
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // Load initial data
    loadAllAnalysisData();
    
    // Set up auto-refresh every 30 seconds
    analysisRefreshInterval = setInterval(() => {
        loadChartsList();
        loadReports();
    }, 30000);
    
    // Refresh journal less frequently (every 2 minutes)
    setInterval(() => {
        loadJournal();
    }, 120000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (analysisRefreshInterval) {
        clearInterval(analysisRefreshInterval);
    }
});
