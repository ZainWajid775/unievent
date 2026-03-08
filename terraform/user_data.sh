#!/bin/bash
set -ex

# ── System updates ─────────────────────────────────────────────────────────────
yum update -y
yum install -y python3 python3-pip git

# ── Clone application from GitHub ─────────────────────────────────────────────
cd /home/ec2-user
if [ ! -d "unievent" ]; then
    git clone https://github.com/ZainWajid775/unievent.git
fi
cd unievent/app

# ── Install Python dependencies ────────────────────────────────────────────────
pip3 install --ignore-installed -r  requirements.txt

# ── Set environment variables ──────────────────────────────────────────────────
cat > /etc/unievent.env <<EOF
S3_BUCKET=${s3_bucket}
AWS_REGION=${aws_region}
TICKETMASTER_API_KEY=${ticketmaster_api_key}
EOF

# ── Create systemd service ─────────────────────────────────────────────────────
cat > /etc/systemd/system/unievent.service <<'SERVICE'
[Unit]
Description=UniEvent Flask Application
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/unievent/app
EnvironmentFile=/etc/unievent.env
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:5000 --workers 3 --timeout 120 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable unievent
systemctl start unievent
systemctl start unievent
