#!/usr/bin/env python3
"""
Syndicate Web UI - Main Application
Modern Flask-based web interface with real-time updates
"""
import json
import logging
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db_manager import get_db

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'syndicate-secret-key-change-in-production')
app.config['JSON_SORT_KEYS'] = False

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Paths
OUTPUT_DIR = PROJECT_ROOT / "output"
CHARTS_DIR = OUTPUT_DIR / "charts"
REPORTS_DIR = OUTPUT_DIR / "reports"
DATA_DIR = PROJECT_ROOT / "data"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


# ==========================================
# ROUTES - Main Pages
# ==========================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/analysis')
def analysis():
    """Analysis and charts page"""
    return render_template('analysis.html')


@app.route('/tasks')
def tasks():
    """Task management page"""
    return render_template('tasks.html')


@app.route('/settings')
def settings():
    """Settings and configuration page"""
    return render_template('settings.html')


# ==========================================
# API ENDPOINTS - Data
# ==========================================

@app.route('/api/status')
def api_status():
    """Get current system status"""
    try:
        db = get_db()
        info = db.get_current_period_info()
        missing = db.get_missing_reports()
        stats = db.get_statistics()
        health = db.get_system_health()
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'period': info,
            'missing_reports': missing,
            'statistics': stats,
            'health': health
        })
    except Exception as e:
        logger.error(f"Status API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/journal')
def api_journal():
    """Get today's journal"""
    try:
        db = get_db()
        today = date.today().isoformat()
        
        # Try file first
        journal_file = OUTPUT_DIR / f"Journal_{today}.md"
        if journal_file.exists():
            content = journal_file.read_text(encoding='utf-8')
            return jsonify({
                'status': 'ok',
                'date': today,
                'content': content,
                'source': 'file'
            })
        
        # Try database
        journal = db.get_latest_journal()
        if journal:
            return jsonify({
                'status': 'ok',
                'date': journal.get('date', today),
                'content': journal.get('content', ''),
                'bias': journal.get('bias', 'NEUTRAL'),
                'gold_price': journal.get('gold_price', 0),
                'source': 'database'
            })
        
        return jsonify({
            'status': 'not_found',
            'message': 'No journal entry for today'
        }), 404
        
    except Exception as e:
        logger.error(f"Journal API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/tasks')
def api_tasks():
    """Get pending tasks"""
    try:
        db = get_db()
        limit = request.args.get('limit', 10, type=int)
        
        pending = db.get_pending_actions(limit=limit)
        ready = db.get_ready_actions(limit=limit)
        scheduled = db.get_scheduled_actions()
        
        return jsonify({
            'status': 'ok',
            'pending': pending,
            'ready': ready,
            'scheduled': scheduled,
            'count': {
                'pending': len(pending),
                'ready': len(ready),
                'scheduled': len(scheduled)
            }
        })
    except Exception as e:
        logger.error(f"Tasks API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/metrics')
def api_metrics():
    """Get market metrics and latest prices"""
    try:
        db = get_db()
        
        # Get latest prices
        metrics = {
            'GOLD': db.get_latest_price('GOLD'),
            'SILVER': db.get_latest_price('SILVER'),
            'DXY': db.get_latest_price('DXY'),
            'VIX': db.get_latest_price('VIX'),
        }
        
        # Calculate GSR
        gold = metrics.get('GOLD', 0)
        silver = metrics.get('SILVER', 0)
        if gold and silver:
            metrics['GSR'] = round(gold / silver, 2)
        
        # Get latest journal for bias
        journal = db.get_latest_journal()
        if journal:
            metrics['bias'] = journal.get('bias', 'NEUTRAL')
            metrics['last_update'] = journal.get('date', '')
        
        return jsonify({
            'status': 'ok',
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Metrics API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/charts')
def api_charts():
    """List available charts"""
    try:
        charts = []
        if CHARTS_DIR.exists():
            for chart_file in CHARTS_DIR.glob('*.png'):
                charts.append({
                    'name': chart_file.stem,
                    'filename': chart_file.name,
                    'url': f'/charts/{chart_file.name}',
                    'modified': datetime.fromtimestamp(chart_file.stat().st_mtime).isoformat()
                })
        
        return jsonify({
            'status': 'ok',
            'charts': charts,
            'count': len(charts)
        })
    except Exception as e:
        logger.error(f"Charts API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/reports')
def api_reports():
    """List available report markdown files"""
    try:
        reports = []
        if REPORTS_DIR.exists():
            for rpt in sorted(REPORTS_DIR.glob('**/*.md'), key=lambda p: p.stat().st_mtime, reverse=True):
                reports.append({
                    'name': rpt.name,
                    'path': str(rpt),
                    'url': f'/reports/{rpt.name}',
                    'modified': datetime.fromtimestamp(rpt.stat().st_mtime).isoformat(),
                    'size': rpt.stat().st_size,
                })
        return jsonify({'status': 'ok', 'reports': reports})
    except Exception as e:
        logger.error(f"Reports API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/run', methods=['POST'])
def api_run():
    """Trigger a single analysis run (background). Returns PID or error."""
    try:
        # Spawn a detached child process to run the analysis once.
        # Use env GOLD_STANDARD_DB if already configured by server
        python_exe = sys.executable or 'python3'
        cmd = [python_exe, os.path.join(PROJECT_ROOT, 'run.py'), '--once']
        # Start as background process
        proc = subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Spawned analysis run (PID: {proc.pid})")
        return jsonify({'status': 'ok', 'pid': proc.pid})
    except Exception as e:
        logger.error(f"Run API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/toggles')
def api_toggles():
    """Get feature toggle states"""
    try:
        db = get_db()
        return jsonify({
            'status': 'ok',
            'toggles': {
                'notion_publishing': db.is_notion_publishing_enabled(),
                'task_execution': db.is_task_execution_enabled(),
                'insights_extraction': db.is_insights_extraction_enabled()
            }
        })
    except Exception as e:
        logger.error(f"Toggles API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/toggles/<feature>', methods=['POST'])
def api_toggle_feature(feature):
    """Toggle a feature on/off"""
    try:
        db = get_db()
        data = request.get_json() or {}
        enabled = data.get('enabled', True)
        
        if feature == 'notion':
            db.set_notion_publishing_enabled(enabled)
        elif feature == 'tasks':
            db.set_task_execution_enabled(enabled)
        elif feature == 'insights':
            db.set_insights_extraction_enabled(enabled)
        else:
            return jsonify({'status': 'error', 'message': 'Unknown feature'}), 400
        
        return jsonify({
            'status': 'ok',
            'feature': feature,
            'enabled': enabled
        })
    except Exception as e:
        logger.error(f"Toggle API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/execution_history')
def api_execution_history():
    """Get task execution history"""
    try:
        db = get_db()
        days = request.args.get('days', 7, type=int)
        action_id = request.args.get('action_id', None)
        
        history = db.get_execution_history(action_id=action_id, days=days)
        
        return jsonify({
            'status': 'ok',
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        logger.error(f"Execution history API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==========================================
# STATIC FILE SERVING
# ==========================================

@app.route('/charts/<path:filename>')
def serve_chart(filename):
    """Serve chart images"""
    return send_from_directory(CHARTS_DIR, filename)


@app.route('/reports/<path:filename>')
def serve_report(filename):
    """Serve report files"""
    return send_from_directory(REPORTS_DIR, filename)


# ==========================================
# WEBSOCKET EVENTS
# ==========================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('status', {'connected': True, 'timestamp': datetime.now().isoformat()})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')


@socketio.on('request_update')
def handle_update_request():
    """Handle update request from client"""
    try:
        # Send current status
        db = get_db()
        health = db.get_system_health()
        emit('health_update', health)
    except Exception as e:
        logger.error(f"Update request error: {e}")
        emit('error', {'message': str(e)})


def broadcast_update(event_type, data):
    """Broadcast update to all connected clients"""
    socketio.emit(event_type, data)


# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': 'Not found'}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal error: {e}")
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
    return render_template('500.html'), 500


# ==========================================
# MAIN
# ==========================================

def main():
    """Run the web UI server"""
    host = os.environ.get('WEB_UI_HOST', '0.0.0.0')
    port = int(os.environ.get('WEB_UI_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Syndicate Web UI on {host}:{port}")
    logger.info(f"Dashboard: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
