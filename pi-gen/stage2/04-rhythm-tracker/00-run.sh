#!/bin/bash
echo "Installing rhythm Tracker into Raspberry Pi OS Image..."

# Create project directory
mkdir -p /home/pi/rhythm-tracker
cd /home/pi/rhythm-tracker

# Install dependencies
apt-get update && apt-get install -y \
    python3 python3-pip python3-venv portaudio19-dev libasound2-dev alsa-utils

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Copy application files (Ensure these exist in pi-gen)
cp -r /boot/rhythm-tracker/* /home/pi/rhythm-tracker/

# Install Python dependencies
pip install -r /home/pi/rhythm-tracker/app/requirements.txt

# Enable systemd service
cp /boot/rhythm-tracker/systemd/rhythm-tracker.service /etc/systemd/system/
systemctl enable rhythm-tracker

echo "rhythm Tracker has been added to the OS image!"