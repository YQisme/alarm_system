#!/bin/bash

SERVICE_NAME=start-server

echo "Stopping service: $SERVICE_NAME"

sudo systemctl stop ${SERVICE_NAME}.service

echo "Service stopped."

echo "Current status:"
systemctl status ${SERVICE_NAME}.service --no-pager
