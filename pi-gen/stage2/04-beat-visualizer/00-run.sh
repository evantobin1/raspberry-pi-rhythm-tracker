#!/bin/bash
echo "🔧 Installing Beat Visualizer into Raspberry Pi OS Image..."

# Create project directory
mkdir -p /home/pi/beat-visualizer
cd /home/pi/beat-visualizer

# Install dependencies
apt-get update && apt-get install -y \
    python3 python3-pip python3-venv portaudio19-dev libasound2-dev alsa-utils

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install numpy pyaudio aubio flask

# Copy application files (Ensure these exist in pi-gen)
cp -r /boot/beat-visualizer/* /home/pi/beat-visualizer/

# Enable systemd service
cp /boot/beat-visualizer/systemd/beat-visualizer.service /etc/systemd/system/
systemctl enable beat-visualizer

echo "✅ Beat Visualizer has been added to the OS image!"
