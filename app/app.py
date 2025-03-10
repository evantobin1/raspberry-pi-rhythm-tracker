import pyaudio
import numpy as np
import aubio
import socket
import time
import threading
from struct import pack
from flask import Flask, request, render_template, jsonify

# --- Default Configuration (Editable via Web Interface) ---
config = {
    "SAMPLERATE": 44100,      # Audio sample rate
    "BUF_SIZE": 128,          # Audio buffer size for beat detection
    "LED_COUNT": 300,         # Number of LEDs in the strip
    "DELAY_MS": 10,           # Delay between packets (milliseconds)
    "FADE_STEP": 15,          # Amount of brightness decrease per step
    "FADE_INTERVAL": 0.05,    # Smooth fading interval
    "AUDIO_DEVICE_INDEX": None,  # Default to ALSA input
    "COLOR_0": "#FF0000",     # Default color for flip_state 0 (red)
    "COLOR_1": "#0000FF"      # Default color for flip_state 1 (blue)
}

MAX_LEDS_PER_PACKET = 500
PACKET_SIZE = 500 * 5

# Global variable to hold the current beat information
last_beat_info = {
    "flip_state": None,  # 0 or 1
    "bpm": 0,
    "confidence": 0.0,
    "timestamp": time.time()
}

# --- Flask Web Server for Configuring Parameters ---
app = Flask(__name__, template_folder="templates")
global udp_sender
global beat_detector

@app.route("/", methods=["GET", "POST"])
def index():
    p = pyaudio.PyAudio()
    
    # Get available **input** audio devices only
    audio_devices = [
        {"index": i, "name": p.get_device_info_by_index(i)["name"]}
        for i in range(p.get_device_count()) 
        if p.get_device_info_by_index(i)["maxInputChannels"] > 0  # Ensure it has input channels
    ]
    
    if request.method == "POST":
        try:
            config["LED_COUNT"] = int(request.form["led_count"])
            config["DELAY_MS"] = int(request.form["delay_ms"])
            selected_device = int(request.form["audio_device"])

            # Update colors from the form (color input values come as hex strings)
            config["COLOR_0"] = request.form.get("color0", config["COLOR_0"])
            config["COLOR_1"] = request.form.get("color1", config["COLOR_1"])
            
            # Ensure selected device is actually valid
            if selected_device not in [d["index"] for d in audio_devices]:
                raise ValueError("Invalid audio input device selected.")

            config["AUDIO_DEVICE_INDEX"] = selected_device

            # Restart beat detection with the new audio device and colors
            restart_beat_detection()
        except Exception as e:
            print(f"Error: {e}")

    return render_template("index.html", config=config, audio_devices=audio_devices)

@app.route("/beat", methods=["GET"])
def get_beat():
    """Return the latest beat info as JSON."""
    return jsonify(last_beat_info)

def hex_to_rgb(hex_color):
    """Convert a hex color (e.g. '#FF0000') to an (R, G, B) tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def restart_beat_detection():
    """Safely restart the beat detector to apply new audio device settings."""
    global beat_detector

    # Validate that the selected device is actually valid
    available_devices = [
        d["index"] for d in [
            {"index": i, "name": pyaudio.PyAudio().get_device_info_by_index(i)}
            for i in range(pyaudio.PyAudio().get_device_count())
        ] if d["name"]["maxInputChannels"] > 0  # Ensure it's an input device
    ]

    if config["AUDIO_DEVICE_INDEX"] not in available_devices:
        print(f"❌ Selected audio device {config['AUDIO_DEVICE_INDEX']} is not a valid input device.")
        return

    # Stop and clean up the current instance if it exists
    if beat_detector is not None:
        try:
            beat_detector.stop()  # Gracefully close the stream
            del beat_detector  # Destroy the object
        except Exception as e:
            print(f"Error while stopping BeatDetector: {e}")

    # Start a new BeatDetector instance
    beat_detector = BeatDetector(udp_sender)
    if beat_detector.stream:  # Only start processing if the stream opened successfully
        threading.Thread(target=beat_detector.process_audio, daemon=True).start()
    else:
        print("⚠️ BeatDetector could not start due to an invalid audio device.")

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
        self.running = True  # Used to safely exit threads
        self.stream = None  # Ensure self.stream exists before trying to use it

        # Debug: Print available devices
        print("\nAvailable Audio Devices:")
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            print(f"Device {i}: {dev['name']}")

        try:
            # Use the selected audio input device
            self.stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=config["SAMPLERATE"],
                input=True,
                frames_per_buffer=config["BUF_SIZE"],
                input_device_index=config["AUDIO_DEVICE_INDEX"]
            )
            print(f"\nListening for beats on device {config['AUDIO_DEVICE_INDEX']}...\n")

        except OSError as e:
            print(f"❌ Error opening audio input device: {e}")
            self.stream = None  # Prevent further errors

        threading.Thread(target=self.fade_leds, daemon=True).start()

    def process_audio(self):
        """Processes the audio input stream and detects beats with confidence."""
        global last_beat_info
        tempo = aubio.tempo("default", config["BUF_SIZE"] * 2, config["BUF_SIZE"], config["SAMPLERATE"])
        
        while self.running:
            data = np.frombuffer(self.stream.read(config["BUF_SIZE"], exception_on_overflow=False), dtype=np.float32)
            is_beat = tempo(data)[0]
            
            if is_beat:
                confidence = tempo.get_confidence()  # Get confidence score (0-1 range)
                self.bpm = tempo.get_bpm()
                self.flip_state = 1 - self.flip_state
                beat_symbol = "▚" if self.flip_state == 0 else "▞"
                print(f"{beat_symbol}\tBPM: {self.bpm:.1f} | Confidence: {confidence:.2f}")
                
                # Update the global beat state for the webpage
                last_beat_info = {
                    "flip_state": self.flip_state,  # 0 means first color, 1 means second color
                    "bpm": self.bpm,
                    "confidence": confidence,
                    "timestamp": time.time()
                }
                
                # Calculate LED color based on the configurable color and confidence
                if self.flip_state == 0:
                    base_color = hex_to_rgb(config["COLOR_0"])
                else:
                    base_color = hex_to_rgb(config["COLOR_1"])
                color = tuple(min(255, int(channel * confidence)) for channel in base_color)

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
                if not self.current_led_state:
                    continue
                
                faded = []
                change_detected = False
                
                for led in self.current_led_state:
                    if len(led) != 3:
                        continue
                    
                    r, g, b = led
                    new_r = max(0, r - config["FADE_STEP"])
                    new_b = max(0, b - config["FADE_STEP"])
                    faded.append((new_r, g, new_b))
                    
                    if new_r != r or new_b != b:
                        change_detected = True
                
                if change_detected:
                    self.current_led_state = faded
                    self.udp_sender.send_led_data(faded)

    def stop(self):
        """Safely stop audio processing and release resources."""
        self.running = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Error closing audio stream: {e}")
        self.p.terminate()
        print("BeatDetector stopped and resources released.")

    def __del__(self):
        """Destructor to clean up the audio stream properly."""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()
        except Exception as e:
            print(f"Error in destructor: {e}")

# --- UDP LED Sender ---
class UDPSender:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.is_connected = True
        print(f"UDP sender initialized for {ip}:{port}")

    def send_led_data(self, led_colors):
        """Send LED data in packets without artificial delay between updates."""
        if not self.is_connected:
            return
        total_leds = len(led_colors)
        leds_sent = 0
        delay = config["DELAY_MS"] / 1000

        while leds_sent < total_leds:
            leds_in_this_packet = min(MAX_LEDS_PER_PACKET, total_leds - leds_sent)
            is_final_packet = (leds_sent + leds_in_this_packet) >= total_leds
            packet = self.prepare_packet(led_colors, leds_sent, leds_in_this_packet, is_final_packet)
            self.send_packet(packet)
            leds_sent += leds_in_this_packet
            
            if delay > 0:
                time.sleep(delay)  

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
    global udp_sender
    global beat_detector
    udp_sender = UDPSender("192.168.0.150", 7777)
    beat_detector = BeatDetector(udp_sender)
    threading.Thread(target=beat_detector.process_audio, daemon=True).start()

    # Start the web server
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    main()
