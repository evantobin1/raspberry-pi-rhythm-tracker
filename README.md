# Raspberry Pi Rhythm Tracker

Raspberry Pi Rhythm Tracker is a real-time beat detection and LED visualization system designed to run on a Raspberry Pi. This guide explains how to integrate the application into a custom Raspberry Pi OS image so that it is pre-installed and runs automatically when the Raspberry Pi boots.

## Prerequisites
- A system capable of running the `pi-gen` tool to build Raspberry Pi OS images
- A Raspberry Pi with a 3.5mm audio input
- Git installed to clone the necessary repositories

## Building a Custom Raspberry Pi OS Image with Rhythm Tracker Preinstalled

### 1. Clone the Required Repositories
First, clone the Rhythm Tracker repository, which contains the application files and installation scripts:
```sh
git clone https://github.com/evantobin1/raspberry-pi-rhythm-tracker.git
```

Next, clone the official Raspberry Pi OS build tool, `pi-gen`, which allows customization of the OS before flashing:
```sh
git clone https://github.com/RPi-Distro/pi-gen
cd pi-gen
```

### 2. Copy the Installation Script
From the `raspberry-pi-rhythm-tracker` repository, copy the `00-run.sh` script into `pi-gen`:
```sh
cp ../raspberry-pi-rhythm-tracker/pi-gen/stage2/04-rhythm-tracker/00-run.sh stage2/04-rhythm-tracker/
chmod +x stage2/04-rhythm-tracker/00-run.sh
```

### 3. Copy the Application Files
Copy the entire `app/` directory, including `app.py` and `requirements.txt`, from `raspberry-pi-rhythm-tracker` into the `pi-gen` build environment:
```sh
cp -r ../raspberry-pi-rhythm-tracker/app stage2/04-rhythm-tracker/files/
cp -r ../raspberry-pi-rhythm-tracker/templates stage2/04-rhythm-tracker/files/
cp -r ../raspberry-pi-rhythm-tracker/systemd stage2/04-rhythm-tracker/files/
```

### 4. Copy the Systemd Service File
To ensure the application starts automatically on boot, copy the systemd service file:
```sh
cp ../raspberry-pi-rhythm-tracker/systemd/rythym-tracker.service stage2/04-rhythm-tracker/files/
```

### 5. Build the Custom Raspberry Pi OS Image
Inside the `pi-gen` directory, run the build process:
```sh
./build.sh
```
This process may take up to an hour, depending on your hardware.

### 7. Flash the Custom OS Image to an SD Card
Once the build is complete, the new Raspberry Pi OS image will be located in:
```sh
pi-gen/deploy/
```
To flash the new OS:
1. Use Raspberry Pi Imager
2. OR use the command line:
```sh
sudo dd if=pi-gen/deploy/your_custom_image.img of=/dev/sdX bs=4M status=progress
```

### 8. First Boot and Verification
Once the Raspberry Pi boots with the custom OS:
- The Rhythm Tracker should start automatically.
- Access the web interface at: `http://raspberrypi.local:5000`
- Verify the service is running: `systemctl status rythym-tracker`
- Restart the service if needed: `sudo systemctl restart rythym-tracker`