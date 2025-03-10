import pyaudio
import numpy as np
import aubio
import socket
import time
import threading
from struct import pack
from flask import Flask, request, render_template

# --- Default Configuration (Editable via Web Interface) ---
config = {
    "SAMPLERATE": 44100,  # Audio sample rate
    "BUF_SIZE": 128,  # Audio buffer size for beat detection
    "LED_COUNT": 300,  # Number of LEDs in the strip
    "DELAY_MS": 10,  # Delay between packets (milliseconds)
    "FADE_STEP": 15,  # Amount of brightness decrease per step
    "FADE_INTERVAL": 0.05,  # Smooth fading interval
    "AUDIO_DEVICE_INDEX": None  # Default to ALSA input
}

MAX_LEDS_PER_PACKET = 500
PACKET_SIZE = 500 * 5

# --- Flask Web Server for Configuring Parameters ---
app = Flask(__name__, template_folder="templates")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        config["LED_COUNT"] = int(request.form["led_count"])
        config["DELAY_MS"] = int(request.form["delay_ms"])
    return render_template("index.html", config=config)

# --- Beat Detector Class ---
class BeatDetector:
    def __init__(self, udp_sender):
        self.udp_sender = udp_sender
        self.p = pyaudio.PyAudio()
        self.current_led_state = [(0, 0, 0)] * config["LED_COUNT"]
        self.lock = threading.Lock()
        self.last_beat_time = 0
        self.bpm = 120
        self.flip_state = 0

        # List available audio devices (for debugging)
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            print(f"Device {i}: {dev['name']}")

        # Use Raspberry Pi's 3.5mm audio input
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=config["SAMPLERATE"],
            input=True,
            frames_per_buffer=config["BUF_SIZE"],
            input_device_index=config["AUDIO_DEVICE_INDEX"]
        )

        # Start background fading thread
        threading.Thread(target=self.fade_leds, daemon=True).start()

        print("Listening for beats...")

    def process_audio(self):
        """Processes the audio input stream."""
        tempo = aubio.tempo("default", config["BUF_SIZE"] * 2, config["BUF_SIZE"], config["SAMPLERATE"])
        while True:
            data = np.frombuffer(self.stream.read(config["BUF_SIZE"], exception_on_overflow=False), dtype=np.float32)
            if tempo(data)[0]:
                self.bpm = tempo.get_bpm()
                color = (255, 0, 0) if self.flip_state == 0 else (0, 0, 255)
                self.flip_state = 1 - self.flip_state
                beat_symbol = "▚" if self.flip_state == 0 else "▞"
                print(f"{beat_symbol}\tBPM: {self.bpm:.1f}")
                self.set_leds([color] * config["LED_COUNT"])

    def set_leds(self, new_state):
        """Update LED state only if changed, avoiding unnecessary network traffic."""
        with self.lock:
            if new_state != self.current_led_state:
                self.current_led_state = new_state
                self.udp_sender.send_led_data(new_state)

    def fade_leds(self):
        """Gradually fades out LEDs over time."""
        while True:
            time.sleep(config["FADE_INTERVAL"])
            with self.lock:
                faded = []
                change_detected = False
                for r, g, b in self.current_led_state:
                    new_r = max(0, r - config["FADE_STEP"])
                    new_b = max(0, b - config["FADE_STEP"])
                    faded.append((new_r, g, new_b))
                    if new_r != r or new_b != b:
                        change_detected = True
                if change_detected:
                    self.current_led_state = faded
                    self.udp_sender.send_led_data(faded)

    def __del__(self):
        self.stream.close()
        self.p.terminate()

# --- UDP LED Sender ---
class UDPSender:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.is_connected = True
        print(f"UDP sender initialized for {ip}:{port}")

    def send_led_data(self, led_colors):
        if not self.is_connected:
            return
        total_leds = len(led_colors)
        leds_sent = 0
        while leds_sent < total_leds:
            leds_in_this_packet = min(MAX_LEDS_PER_PACKET, total_leds - leds_sent)
            is_final_packet = (leds_sent + leds_in_this_packet) >= total_leds
            packet = self.prepare_packet(led_colors, leds_sent, leds_in_this_packet, is_final_packet)
            self.send_packet(packet)
            leds_sent += leds_in_this_packet
            time.sleep(config["DELAY_MS"] / 1000)

    def prepare_packet(self, led_data, start_index, num_leds, is_final_packet):
        packet = bytearray(PACKET_SIZE)
        packet[0] = 0x01 if is_final_packet else 0x00
        packet_index = 1
        for i in range(num_leds):
            led_index = start_index + i
            packet[packet_index:packet_index+2] = pack(">H", led_index)
            packet[packet_index+2:packet_index+5] = led_data[led_index]
            packet_index += 5
        while packet_index < PACKET_SIZE:
            packet[packet_index:packet_index+2] = b'\xFF\xFF'
            packet[packet_index+2:packet_index+5] = b'\x00\x00\x00'
            packet_index += 5
        return packet

    def send_packet(self, data):
        try:
            self.socket.sendto(data, (self.ip, self.port))
        except Exception as e:
            print(f"Error sending UDP packet: {e}")

# --- Main Function ---
def main():
    udp_sender = UDPSender("192.168.0.150", 7777)
    beat_detector = BeatDetector(udp_sender)
    threading.Thread(target=beat_detector.process_audio, daemon=True).start()

    # Start the web server
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    main()
