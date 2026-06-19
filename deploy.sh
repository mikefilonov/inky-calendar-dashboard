#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 [user@]hostname"
  echo "Example: $0 pi@raspberrypi.local"
  exit 1
fi

SSH_HOST="$1"
REMOTE_DIR="~/inky-calendar"

echo "=== 1. Copying project files to ${SSH_HOST} ==="
# Copy files excluding virtual environment, previews, local configurations, and git files
rsync -avz \
  --exclude 'venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'calendar.png' \
  --exclude '.git/' \
  --exclude '.gitignore' \
  --exclude 'config.json' \
  --exclude 'deploy.sh' \
  ./ "${SSH_HOST}:${REMOTE_DIR}/"

echo "=== 2. Configuring Remote Environment ==="
ssh -t "${SSH_HOST}" bash -c "'
  set -e
  echo \"Checking system dependencies (python3-dev)...\"
  if ! dpkg -s python3-dev >/dev/null 2>&1; then
    echo \"Installing python3-dev...\"
    sudo apt-get update && sudo apt-get install -y python3-dev
  else
    echo \"python3-dev is already installed.\"
  fi
  
  echo \"Setting up Python virtual environment...\"
  python3 -m venv ${REMOTE_DIR}/venv
  
  echo \"Upgrading pip and installing requirements...\"
  ${REMOTE_DIR}/venv/bin/pip install --upgrade pip
  ${REMOTE_DIR}/venv/bin/pip install -r ${REMOTE_DIR}/requirements.txt
  ${REMOTE_DIR}/venv/bin/pip install inky smbus2

  if [ ! -f ${REMOTE_DIR}/config.json ]; then
    echo \"Creating default config.json...\"
    cp ${REMOTE_DIR}/config.json.example ${REMOTE_DIR}/config.json
    echo \"WARNING: Created config.json with placeholder calendar URL. Please edit ${REMOTE_DIR}/config.json on the Pi to add your Google Calendar URL.\"
  fi

  echo \"=== 3. Setting up Cron Job ===\"
  CRON_LINE=\"*/5 * * * * ${REMOTE_DIR}/venv/bin/python ${REMOTE_DIR}/main.py >> ${REMOTE_DIR}/cron.log 2>&1\"
  REBOOT_LINE=\"@reboot sleep 30 && ${REMOTE_DIR}/venv/bin/python ${REMOTE_DIR}/main.py --force >> ${REMOTE_DIR}/cron.log 2>&1\"
  
  # Read existing cron, remove any existing inky-calendar lines, append the new ones, and write back safely
  (crontab -l 2>/dev/null | grep -v \"inky-calendar\" || true; echo \"\$CRON_LINE\"; echo \"\$REBOOT_LINE\") | crontab -
  echo \"Cron job configured: Run every 5 minutes and on startup.\"

  echo \"=== 4. Running ad-hoc for the first time ===\"
  # Force update the display on deploy
  ${REMOTE_DIR}/venv/bin/python ${REMOTE_DIR}/main.py --force
'"

echo "=== 5. Fetching generated calendar.png for debugging ==="
scp "${SSH_HOST}:${REMOTE_DIR}/calendar.png" ./calendar.png

echo "=== Deploy Finished Successfully! ==="
