#!/bin/bash
echo "Installing Rythym Tracker into Raspberry Pi OS Image..."

# Create project directory
mkdir -p /home/pi/rythym-tracker
cd /home/pi/rythym-tracker

# Install dependencies
apt-get update && apt-get install -y \
    python3 python3-pip python3-venv portaudio19-dev libasound2-dev alsa-utils

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install numpy pyaudio aubio flask

# Copy application files (Ensure these exist in pi-gen)
cp -r /boot/rythym-tracker/* /home/pi/rythym-tracker/

# Enable systemd service
cp /boot/rythym-tracker/systemd/rythym-tracker.service /etc/systemd/system/
systemctl enable rythym-tracker

echo "Rythym Tracker has been added to the OS image!"
