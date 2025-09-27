# 🚀 Deployment Guide - Emergency Response USSD System

This guide covers deploying the Emergency Response USSD System to production with proper security configurations.

## 📋 Prerequisites

### System Requirements
- **Server**: Ubuntu 20.04+ or CentOS 8+
- **Python**: 3.8 or higher
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Storage**: 20GB+ available space
- **Network**: HTTPS-capable domain with SSL certificate

### External Services
- **Africa's Talking Account**: For USSD and SMS services
- **Database**: PostgreSQL 12+ (production) or SQLite (development)
- **Reverse Proxy**: Nginx (recommended)
- **Process Manager**: Systemd or Supervisor

## 🔧 Production Setup

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib

# Create application user
sudo useradd -m -s /bin/bash emergency-app
sudo usermod -aG sudo emergency-app
```

### 2. Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE emergency_response;
CREATE USER emergency_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE emergency_response TO emergency_user;
\q
```

### 3. Application Deployment

```bash
# Switch to application user
sudo su - emergency-app

# Clone repository
git clone https://github.com/your-org/emergency-response-ussd.git
cd emergency-response-ussd

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Create production environment file
cp .env.example .env.production
```

### 4. Environment Configuration

Edit `.env.production`:

```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secure-secret-key-here-change-this
DATABASE_URL=postgresql://emergency_user:secure_password_here@localhost/emergency_response

# Africa's Talking Configuration
AT_USERNAME=your_at_username
AT_API_KEY=your_at_api_key_here
USSD_SERVICE_CODE=*384#
USSD_CHANNEL=17925
SMS_SENDER_ID=EMERGENCY

# Security Configuration
ENCRYPTION_KEY=your-32-character-encryption-key-here
DATA_RETENTION_DAYS=365
AUDIT_LOG_RETENTION_DAYS=90

# Rate Limiting
USSD_RATE_LIMIT=3 per hour
SMS_RATE_LIMIT=5 per hour

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/emergency-response/app.log
```

### 5. Database Migration

```bash
# Initialize database
python app.py --init-db

# Verify setup
python -c "from app import create_app, db; app = create_app('production'); print('Database connection successful')"
```

## 🔒 Security Configuration

### 1. SSL/TLS Setup

```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com
```

### 2. Nginx Configuration

Create `/etc/nginx/sites-available/emergency-response`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/m;
    limit_req_zone $binary_remote_addr zone=ussd:10m rate=30r/m;
    
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ussd/ {
        limit_req zone=ussd burst=50 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Admin panel - additional security
    location /admin/ {
        limit_req zone=api burst=5 nodelay;
        # Optional: IP whitelist
        # allow 192.168.1.0/24;
        # deny all;
        
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/emergency-response /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Optional: Restrict SSH access
sudo ufw limit ssh
```

## 🔄 Process Management

### 1. Systemd Service

Create `/etc/systemd/system/emergency-response.service`:

```ini
[Unit]
Description=Emergency Response USSD System
After=network.target postgresql.service

[Service]
Type=exec
User=emergency-app
Group=emergency-app
WorkingDirectory=/home/emergency-app/emergency-response-ussd
Environment=PATH=/home/emergency-app/emergency-response-ussd/venv/bin
EnvironmentFile=/home/emergency-app/emergency-response-ussd/.env.production
ExecStart=/home/emergency-app/emergency-response-ussd/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:8080 --timeout 120 --keep-alive 2 --max-requests 1000 --max-requests-jitter 100 app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable emergency-response
sudo systemctl start emergency-response
sudo systemctl status emergency-response
```

### 2. Logging Configuration

```bash
# Create log directory
sudo mkdir -p /var/log/emergency-response
sudo chown emergency-app:emergency-app /var/log/emergency-response

# Configure log rotation
sudo tee /etc/logrotate.d/emergency-response << EOF
/var/log/emergency-response/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 emergency-app emergency-app
    postrotate
        systemctl reload emergency-response
    endscript
}
EOF
```

## 🌍 Africa's Talking Integration

### 1. USSD Configuration

1. **Login** to Africa's Talking dashboard
2. **Navigate** to USSD → Channels
3. **Create Channel**:
   - Service Code: `*384#`
   - Callback URL: `https://your-domain.com/ussd/callback`
   - Channel: Use provided channel number

### 2. SMS Configuration

1. **Navigate** to SMS → Settings
2. **Configure**:
   - Sender ID: `EMERGENCY`
   - Callback URL: `https://your-domain.com/sms/callback` (optional)

### 3. Testing Integration

```bash
# Test USSD callback
curl -X POST https://your-domain.com/ussd/callback \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "sessionId=test123&serviceCode=*384*&phoneNumber=%2B2348012345678&text="

# Expected response: CON 🚨 Emergency Response System...
```

## 📊 Monitoring & Maintenance

### 1. Health Checks

Create `/home/emergency-app/health-check.sh`:

```bash
#!/bin/bash
# Health check script

# Check application status
if ! systemctl is-active --quiet emergency-response; then
    echo "CRITICAL: Emergency Response service is down"
    exit 2
fi

# Check database connectivity
if ! python3 -c "from app import create_app, db; app = create_app('production'); app.app_context().push(); db.engine.execute('SELECT 1')" 2>/dev/null; then
    echo "CRITICAL: Database connection failed"
    exit 2
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "WARNING: Disk usage is ${DISK_USAGE}%"
    exit 1
fi

echo "OK: All systems operational"
exit 0
```

### 2. Backup Strategy

Create `/home/emergency-app/backup.sh`:

```bash
#!/bin/bash
# Database backup script

BACKUP_DIR="/home/emergency-app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="emergency_response_${DATE}.sql"

mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h localhost -U emergency_user emergency_response > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_FILE"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * /home/emergency-app/backup.sh >> /var/log/emergency-response/backup.log 2>&1
```

### 3. Performance Monitoring

Install monitoring tools:
```bash
# Install htop for system monitoring
sudo apt install htop

# Install PostgreSQL monitoring
sudo apt install postgresql-contrib
```

## 🔄 Updates & Maintenance

### 1. Application Updates

```bash
# Switch to application user
sudo su - emergency-app
cd emergency-response-ussd

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Run database migrations (if any)
python manage.py db upgrade

# Restart service
sudo systemctl restart emergency-response
```

### 2. Security Updates

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# SSL certificate renewal (automatic with certbot)
sudo certbot renew --dry-run

# Check for security vulnerabilities
pip audit
```

## 🚨 Troubleshooting

### Common Issues

1. **Service won't start**:
   ```bash
   sudo journalctl -u emergency-response -f
   ```

2. **Database connection errors**:
   ```bash
   sudo -u postgres psql -c "\l"
   ```

3. **SSL certificate issues**:
   ```bash
   sudo certbot certificates
   sudo nginx -t
   ```

4. **High memory usage**:
   ```bash
   htop
   sudo systemctl restart emergency-response
   ```

### Log Analysis

```bash
# Application logs
tail -f /var/log/emergency-response/app.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# System logs
sudo journalctl -u emergency-response -f
```

## 📞 Support

For deployment support:
- **Documentation**: Check README.md and SECURITY.md
- **Issues**: Create GitHub issue with deployment logs
- **Emergency**: Contact system administrator

---

**Deployment completed successfully! 🎉**

Your Emergency Response USSD System is now running securely in production.