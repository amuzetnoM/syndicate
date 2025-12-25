# Syndicate Web UI

Modern, responsive web interface for the Syndicate precious metals intelligence system.

## Features

- **Real-time Dashboard** - Live market data and system status updates
- **Interactive Charts** - View and analyze gold, silver, DXY, and VIX charts
- **AI Journal Viewer** - Read today's AI-generated market analysis
- **Task Management** - Monitor and manage autonomous tasks
- **System Health** - Track performance metrics and system health
- **WebSocket Integration** - Real-time updates without page refresh
- **Responsive Design** - Works beautifully on desktop, tablet, and mobile
- **Dark Theme** - Easy on the eyes with professional gold accents

## Screenshots

### Dashboard
![Dashboard](../../docs/screenshots/dashboard.png)

### Charts & Analysis
![Analysis](../../docs/screenshots/analysis.png)

## Quick Start

### Prerequisites

- Python 3.10 or higher
- All Syndicate dependencies installed
- Database initialized (`python db_manager.py`)

### Installation

1. Install web UI dependencies:
```bash
pip install Flask Flask-SocketIO python-socketio eventlet
```

2. Start the web server:
```bash
python web_ui/start.py
```

3. Open your browser to:
```
http://localhost:5000
```

## Configuration

Environment variables:

```bash
# Web UI Settings
export WEB_UI_HOST=0.0.0.0        # Listen address (0.0.0.0 for all interfaces)
export WEB_UI_PORT=5000           # Port number
export FLASK_DEBUG=false          # Debug mode (set to true for development)
export SECRET_KEY=your-secret     # Flask secret key (change in production)
```

## Architecture

```
web_ui/
├── app.py              # Main Flask application
├── start.py            # Quick start launcher
├── templates/          # HTML templates
│   ├── index.html     # Dashboard page
│   ├── analysis.html  # Analysis & charts page
│   ├── tasks.html     # Task management page
│   └── settings.html  # Settings page
└── static/
    ├── css/
    │   └── style.css  # Main stylesheet
    ├── js/
    │   └── dashboard.js  # Dashboard JavaScript
    └── images/         # Static images
```

## API Endpoints

### Data Endpoints

- `GET /api/status` - System status and health
- `GET /api/journal` - Today's journal entry
- `GET /api/tasks` - Pending and ready tasks
- `GET /api/metrics` - Market metrics and prices
- `GET /api/charts` - Available chart list
- `GET /api/memory` - Cortex memory state
- `GET /api/toggles` - Feature toggle states

### Control Endpoints

- `POST /api/toggles/<feature>` - Toggle feature on/off

### Static Files

- `/charts/<filename>` - Chart images
- `/reports/<filename>` - Report files

## WebSocket Events

### Client → Server

- `connect` - Client connection established
- `disconnect` - Client disconnected
- `request_update` - Request data update

### Server → Client

- `status` - Connection status
- `health_update` - System health data
- `error` - Error message

## Development

### Running in Debug Mode

```bash
export FLASK_DEBUG=true
python web_ui/start.py
```

### Adding New Features

1. Add API endpoint in `app.py`
2. Create/update HTML template
3. Add JavaScript functionality
4. Update CSS styling

### Testing

```bash
# Test API endpoints
curl http://localhost:5000/api/status

# Test with the system running
python run.py --once &
python web_ui/start.py
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 web_ui.app:app
```

### Using systemd

Create `/etc/systemd/system/syndicate-web.service`:

```ini
[Unit]
Description=Syndicate Web UI
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/syndicate
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python web_ui/start.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable syndicate-web
sudo systemctl start syndicate-web
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name gold.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Security

- Change `SECRET_KEY` in production
- Use HTTPS for external access
- Implement authentication if exposing publicly
- Restrict access with firewall rules
- Keep dependencies updated

## Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :5000

# Use a different port
export WEB_UI_PORT=5001
python web_ui/start.py
```

### WebSocket Connection Fails

- Check firewall settings
- Ensure `eventlet` is installed
- Verify proxy configuration for WebSocket upgrade headers

### Charts Not Loading

- Verify charts exist in `output/charts/` directory
- Run analysis to generate charts: `python run.py --once`
- Check file permissions

### Database Errors

- Initialize database: `python db_manager.py`
- Check database file permissions
- Verify SQLite version (3.35.0+)

## Support

For issues, feature requests, or contributions:
- GitHub Issues: https://github.com/amuzetnoM/syndicate/issues
- Documentation: https://github.com/amuzetnoM/syndicate#readme

## License

MIT License - See LICENSE file for details
