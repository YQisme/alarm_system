#!/bin/bash

SERVICE_NAME=start-server
SCRIPT_PATH=$(realpath ./start_server.sh)

echo "Creating systemd service for $SCRIPT_PATH"

sudo bash -c "cat > /etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Start Server Script
After=network.target

[Service]
Type=simple
ExecStart=/bin/bash ${SCRIPT_PATH}
Restart=always
User=$(whoami)
WorkingDirectory=$(dirname ${SCRIPT_PATH})

[Install]
WantedBy=multi-user.target
EOF

echo "Reload systemd..."
sudo systemctl daemon-reload

echo "Enable service (start at boot)..."
sudo systemctl enable ${SERVICE_NAME}.service

echo "Start service now..."
sudo systemctl start ${SERVICE_NAME}.service

echo "Done."

echo "Check status with:"
echo "systemctl status ${SERVICE_NAME}.service"
