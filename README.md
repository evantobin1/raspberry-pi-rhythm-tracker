# Raspberry Pi Rhythm Tracker

Raspberry Pi Rhythm Tracker is a real-time beat detection and LED visualization system designed for the Raspberry Pi. This guide provides two installation methods: **downloading a prebuilt image** for an easy setup or **building the image from source** for advanced customization.

---

## Installation Options

### Option 1: Download and Flash a Prebuilt Image (Recommended)
For a quick and hassle-free setup, use the prebuilt image:

1. **Download** the latest `.zip` file from the [Releases](https://github.com/evantobin1/raspberry-pi-rhythm-tracker/releases) section.
2. **Unzip the file, flash the `.img`** to an SD card using either:
   - **Raspberry Pi Imager** (Recommended)
   - The command line (Linux/macOS):
     ```sh
     sudo dd if=your_downloaded_image.img of=/dev/sdX bs=4M status=progress
     ```
3. **Insert the SD card** into the Raspberry Pi and power it on.
4. The Rhythm Tracker should start automatically.
5. Access the web interface at: `http://raspberrypi.local:5000`
6. Verify the service is running:
   ```sh
   systemctl status rhythm-tracker
   ```
7. If needed, restart the service:
   ```sh
   sudo systemctl restart rhythm-tracker
   ```

---

### Option 2: Build from Source (For Advanced Users)
If you prefer to build a custom Raspberry Pi OS image with Rhythm Tracker pre-installed, follow these steps:

#### 1. Clone the Repositories
```sh
git clone https://github.com/evantobin1/raspberry-pi-rhythm-tracker.git
git clone https://github.com/RPi-Distro/pi-gen
cd pi-gen
```

#### 2. Copy Installation Scripts and Files
```sh
mkdir -p stage2/04-rhythm-tracker/
cp ../raspberry-pi-rhythm-tracker/pi-gen/stage2/04-rhythm-tracker/00-run.sh stage2/04-rhythm-tracker/
chmod +x stage2/04-rhythm-tracker/00-run.sh
cp -r ../raspberry-pi-rhythm-tracker/app stage2/04-rhythm-tracker/files/
cp -r ../raspberry-pi-rhythm-tracker/systemd stage2/04-rhythm-tracker/files/
cp ../raspberry-pi-rhythm-tracker/systemd/rhythm-tracker.service stage2/04-rhythm-tracker/files/
```

#### 3. Install Required Dependencies
```sh
sudo apt-get update && sudo apt-get install -y quilt qemu-user-static debootstrap zerofree zip libarchive-tools bc pigz arch-test parted dosfstools rsync xz-utils xxd file
```

#### 4. Build the Custom Raspberry Pi OS Image
```sh
sudo ./build.sh
```
> **Note:** The build process can take up to an hour, depending on your hardware.

#### 5. Flash the Custom OS Image to an SD Card
After the build is complete, the new Raspberry Pi OS image will be in:
```sh
pi-gen/deploy/
```
Flash the image using Raspberry Pi Imager or via the command line:
```sh
sudo dd if=pi-gen/deploy/your_custom_image.img of=/dev/sdX bs=4M status=progress
```

#### 6. First Boot and Verification
- Boot the Raspberry Pi with the custom OS.
- The Rhythm Tracker should start automatically.
- Access the web interface: `http://raspberrypi.local:5000`
- Check the service status:
  ```sh
  systemctl status rhythm-tracker
  ```
- Restart the service if needed:
  ```sh
  sudo systemctl restart rhythm-tracker
  ```

---

**Enjoy real-time beat detection and LED visualization with Raspberry Pi Rhythm Tracker!** 🎵💡

