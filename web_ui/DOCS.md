# Syndicate - Modern Web UI

## Overview

A beautiful, modern web interface for the Syndicate precious metals intelligence system. Built with Flask, featuring real-time updates, responsive design, and an intuitive user experience.

## Key Features

### 🎨 Beautiful Design
- **Modern Dark Theme** - Professional appearance with gold accents
- **Responsive Layout** - Works perfectly on desktop, tablet, and mobile
- **Smooth Animations** - Polished interactions and transitions
- **Clean Typography** - Inter font family for excellent readability

### ⚡ Real-Time Updates
- **WebSocket Integration** - Live data updates without page refresh
- **Auto-Refresh** - Automatic data updates every 30 seconds
- **Connection Status** - Visual indicator of server connection

### 📊 Dashboard Features
- **Live Market Metrics** - Gold, Silver, GSR, and market bias
- **Interactive Charts** - Switch between different asset charts
- **Today's Journal** - AI-generated market analysis and insights
- **System Health** - Monitor reports, tasks, and performance
- **Recent Tasks** - Track autonomous system operations

### 🎯 Core Pages

1. **Dashboard (/)** - Main overview with metrics and status
2. **Analysis (/analysis)** - Detailed charts and technical analysis
3. **Tasks (/tasks)** - Task management and execution monitoring
4. **Settings (/settings)** - System configuration and toggles

## Quick Start

### 1. Install Dependencies

```bash
pip install Flask Flask-SocketIO python-socketio eventlet
```

### 2. Start the Web Server

```bash
python web_ui/start.py
```

### 3. Open in Browser

Navigate to: **http://localhost:5000**

## Architecture

```
┌─────────────────────────────────────────────┐
│           Flask Web Application             │
│  ┌───────────┐  ┌────────────┐  ┌────────┐ │
│  │  Routes   │  │ WebSocket  │  │  API   │ │
│  │ (HTML)    │  │  (Socket   │  │ (JSON) │ │
│  │           │  │   IO)      │  │        │ │
│  └───────────┘  └────────────┘  └────────┘ │
└─────────────────────────────────────────────┘
              │                │
              ▼                ▼
┌─────────────────────┐  ┌─────────────────┐
│   Database (SQLite) │  │  File System    │
│   - Journals        │  │  - Charts       │
│   - Tasks           │  │  - Reports      │
│   - Metrics         │  │  - Memory       │
└─────────────────────┘  └─────────────────┘
```

## API Reference

### Status Endpoints

```
GET /api/status
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00",
  "period": {...},
  "health": {...}
}
```

### Metrics Endpoints

```
GET /api/metrics
{
  "status": "ok",
  "metrics": {
    "GOLD": 2050.50,
    "SILVER": 23.45,
    "GSR": 87.42,
    "bias": "BULLISH"
  }
}
```

### Charts Endpoints

```
GET /api/charts
{
  "status": "ok",
  "charts": [
    {
      "name": "GOLD",
      "filename": "GOLD.png",
      "url": "/charts/GOLD.png",
      "modified": "2024-01-15T10:00:00"
    }
  ]
}
```

## Customization

### Theme Colors

Edit `/web_ui/static/css/style.css`:

```css
:root {
    --gold: #f59e0b;           /* Primary gold accent */
    --bg-primary: #0a0e1a;     /* Main background */
    --text-primary: #f9fafb;   /* Primary text color */
}
```

### Update Interval

Edit `/web_ui/static/js/dashboard.js`:

```javascript
// Auto-refresh every 30 seconds
updateInterval = setInterval(() => {
    loadMetrics();
    loadTasks();
    loadStatus();
}, 30000);  // Change this value (in milliseconds)
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 web_ui.app:app
```

### Using systemd Service

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
Environment="WEB_UI_HOST=0.0.0.0"
Environment="WEB_UI_PORT=5000"
ExecStart=/path/to/venv/bin/python web_ui/start.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable syndicate-web
sudo systemctl start syndicate-web
sudo systemctl status syndicate-web
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name gold.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name gold.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Security Considerations

1. **Change Secret Key** - Set a strong `SECRET_KEY` environment variable
2. **Use HTTPS** - Always use SSL/TLS in production
3. **Authentication** - Add authentication for public deployments
4. **Rate Limiting** - Implement rate limiting for API endpoints
5. **Firewall** - Restrict access with proper firewall rules
6. **Updates** - Keep all dependencies up to date

## Troubleshooting

### Port Already in Use

```bash
# Find what's using port 5000
lsof -i :5000

# Use a different port
export WEB_UI_PORT=5001
python web_ui/start.py
```

### WebSocket Connection Issues

Check browser console for errors. Ensure:
- `eventlet` is installed
- No firewall blocking WebSocket connections
- Proxy properly configured for WebSocket upgrade

### Charts Not Displaying

```bash
# Generate charts
python run.py --once

# Check charts directory
ls -la output/charts/

# Verify permissions
chmod 644 output/charts/*.png
```

### Database Errors

```bash
# Initialize database
python db_manager.py

# Check permissions
ls -la data/syndicate.db

# Reset if needed (WARNING: deletes data)
rm data/syndicate.db
python db_manager.py
```

## Development

### Running in Debug Mode

```bash
export FLASK_DEBUG=true
export WEB_UI_HOST=127.0.0.1
export WEB_UI_PORT=5000
python web_ui/start.py
```

### Adding New Features

1. **Add API Endpoint** - Update `app.py` with new route
2. **Update Frontend** - Add HTML, CSS, and JavaScript
3. **Test Thoroughly** - Test all functionality
4. **Update Documentation** - Document new features

### Code Style

- Follow PEP 8 for Python code
- Use ESLint for JavaScript (optional)
- Keep CSS organized and commented
- Write descriptive commit messages

## Performance Optimization

### Caching

Add Redis caching for frequently accessed data:

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'redis'})

@app.route('/api/metrics')
@cache.cached(timeout=30)
def api_metrics():
    # ...
```

### Database Connection Pooling

Use SQLAlchemy for better database performance:

```python
from flask_sqlalchemy import SQLAlchemy

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/syndicate.db'
db = SQLAlchemy(app)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

- **GitHub Issues**: https://github.com/amuzetnoM/syndicate/issues
- **Documentation**: https://github.com/amuzetnoM/syndicate
- **License**: MIT

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial release
- Dashboard with real-time metrics
- Interactive chart viewer
- Journal display
- Task management
- System health monitoring
- WebSocket integration
- Responsive design
- Dark theme with gold accents

---

Built with ❤️ for the Syndicate project
