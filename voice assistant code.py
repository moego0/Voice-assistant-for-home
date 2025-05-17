import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import asyncio
import serial
import time
import pyttsx3
import threading
import speech_recognition as sr
from bleak import BleakScanner

# --- Function to create buttons with hover effect ---
def create_hover_button(parent, text, command):
    btn = tk.Button(parent, text=text, command=command, bg="lightgray", relief="raised", width=20)
    btn.bind("<Enter>", lambda e: btn.config(bg="gray"))
    btn.bind("<Leave>", lambda e: btn.config(bg="lightgray"))
    return btn

# Initialize TTS engine
try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    if voices:
        engine.setProperty('voice', voices[0].id)
    engine.setProperty('rate', 150)
except Exception as e:
    engine = None
    print("TTS Engine init failed:", e)

ser = None
ACTIVATION_PHRASE = "hey assistant"

# GUI Setup
root = tk.Tk()
root.title("Bluetooth Device Controller")
root.geometry("770x900")  # Set window size to 770x1024
root.configure(bg="#1e1e1e")

# Background
bg_image = Image.open("background.jpg").resize((1920, 1024))  # Adjust background size
bg_photo = ImageTk.PhotoImage(bg_image)
bg_label = tk.Label(root, image=bg_photo)
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

# Main Frame
frame = tk.Frame(root, bg="#ffffff", relief="sunken")
frame.place(x=10, y=10, width=750, height=1004)  # Adjust frame size

display_frame = tk.Frame(frame, bg="#000000", relief="ridge")
display_frame.pack(fill="x", pady=10)

display_box = tk.Text(
    display_frame,
    height=12,  # Adjust height
    wrap="word",
    bg="#1e1e1e",  # Darker background
    fg="lime",  # Bright text color
    font=("Courier", 12),  # Monospace font
    insertbackground="white",  # White cursor
    relief="flat",  # Flat border
)

display_box.pack(fill="x", padx=10, pady=5)
def update_display(user_text=None, assistant_text=None):
    display_box.config(state="normal")
    if user_text:
        display_box.insert(tk.END, f"\nYou: {user_text}")
    if assistant_text:
        display_box.insert(tk.END, f"\nAssistant: {assistant_text}")
    display_box.see(tk.END)
    display_box.config(state="disabled")

def speak(audio):
    print(f"Assistant: {audio}")
    update_display(assistant_text=audio)
    if engine:
        engine.say(audio)
        engine.runAndWait()

async def scan_bluetooth():
    devices = await BleakScanner.discover()
    if not devices:
        messagebox.showinfo("Scan", "No Bluetooth devices found.")
        return

    device_list = [f"{device.name or 'Unknown'} ({device.address})" for device in devices]
    choice = simpledialog.askstring("Bluetooth Devices", "Select device:\n" + "\n".join(device_list))
    if choice:
        addr_start = choice.find("(") + 1
        addr_end = choice.find(")")
        if addr_start != -1 and addr_end != -1:
            address = choice[addr_start:addr_end]
            bluetooth_address.set(address)
            connect_bluetooth()

def connect_bluetooth():
    global ser
    try:
        com_port = simpledialog.askstring("Bluetooth COM Port", "Enter COM port (e.g., COM5):")
        if com_port:
            ser = serial.Serial(com_port, 9600, timeout=2)
            time.sleep(2)
            speak("Bluetooth connected")
    except serial.SerialException as e:
        messagebox.showerror("Bluetooth Error", str(e))
        speak("Failed to connect to Bluetooth")

def send_command(cmd):
    if ser:
        try:
            ser.write(f"{cmd}\n".encode())
            time.sleep(0.5)
            if ser.in_waiting:
                return ser.readline().decode().strip()
        except serial.SerialException as e:
            messagebox.showerror("Serial Error", str(e))
    return None

# Command functions
def red_light(): send_command("RED_ON"); speak("Red light on")
def green_light(): send_command("GREEN_ON"); speak("Green light on")
def white_light(): send_command("WHITE_ON"); speak("White light on")
def red_off(): send_command("RED_OFF"); speak("Red light off")
def green_off(): send_command("GREEN_OFF"); speak("Green light off")
def white_off(): send_command("WHITE_OFF"); speak("White light off")
def all_lights_on(): send_command("ALL_LIGHTS_ON"); speak("All lights on")
def all_lights_off(): send_command("ALL_LIGHTS_OFF"); speak("All lights off")
def power_relay(): send_command("POWER_RELAY"); speak("Relay powered")
def power_off_relay(): send_command("POWER_OFF_RELAY"); speak("Relay powered off")

def speak_temperature():
    send_command("GET_TEMP")
    start = time.time()
    while time.time() - start < 2:
        if ser and ser.in_waiting:
            temp_data = ser.readline().decode().strip()
            if "ERROR" not in temp_data:
                speak(f"The temperature is {temp_data} degrees Celsius")
                return
            break
    speak("Could not read temperature")

def gaming_mode():
    send_command("gaming_mode")
    speak("Gaming mode activated")

def sleep_mode():
    send_command("SLEEP_MODE")
    speak("All components turned off for sleep mode")

def automatic_mode():
    speak("Monitoring temperature")
    while True:
        send_command("GET_TEMP")
        time.sleep(1)
        if ser and ser.in_waiting:
            temp_data = ser.readline().decode().strip()
            try:
                temp = float(temp_data)
                if temp > 30:
                    send_command("kill")
                    speak("High temperature! Buzzer on")
                    break
            except ValueError:
                continue
        root.update()
        if not auto_mode_running.get():
            speak("Automatic mode exited")
            break

def toggle_automatic():
    if auto_mode_running.get():
        threading.Thread(target=automatic_mode, daemon=True).start()

def voice_command():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 100
    recognizer.dynamic_energy_threshold = False
    with sr.Microphone() as source:
        speak("Yes?")
        try:
            audio = recognizer.listen(source, timeout=5)
            command = recognizer.recognize_google(audio).lower()
            update_display(user_text=command)
            print("Voice Command:", command)
            if "read on" in command: red_light()
            elif "red off" in command: red_off()
            elif "green on" in command: green_light()
            elif "green of" in command: green_off()
            elif "white on" in command: white_light()
            elif "white off" in command: white_off()
            elif "lights on" in command: all_lights_on()
            elif "lights off" in command: all_lights_off()
            elif "temperature" in command: speak_temperature()
            elif "gaming" in command: gaming_mode()
            elif "sleep" in command: sleep_mode()
            elif "relay on" in command: power_relay()
            elif "relay of" in command: power_off_relay()
            elif "automatic mode" in command: automatic_mode()
            else: speak("Command not recognized")
        except sr.UnknownValueError:
            speak("Sorry, I could not understand.")
        except sr.WaitTimeoutError:
            speak("Listening timed out.")

def activation_listener():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 100
    recognizer.dynamic_energy_threshold = False
    with sr.Microphone() as source:
        while True:
            try:
                audio = recognizer.listen(source, timeout=5)
                trigger = recognizer.recognize_google(audio).lower()
                if ACTIVATION_PHRASE in trigger:
                    voice_command()
            except (sr.UnknownValueError, sr.WaitTimeoutError):
                continue
            except Exception as e:
                print("Activation listener error:", e)
                break

def run_async_task(async_func):
    def wrapper():
        asyncio.run(async_func())
    threading.Thread(target=wrapper, daemon=True).start()



# Bluetooth
def create_hover_button(parent, text, command, bg="lightgray", fg="black"):
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, relief="raised", width=20)
    btn.bind("<Enter>", lambda e: btn.config(bg="gray", fg="white"))  # Hover effect
    btn.bind("<Leave>", lambda e: btn.config(bg=bg, fg=fg))  # Reset to original colors
    return btn
frame = tk.Frame(root, bg="#1e1e1e")
frame.pack(padx=20, pady=20)

bluetooth_address = tk.StringVar(value='')

def on_exit():
    if ser and ser.is_open:
        all_lights_off()
        ser.close()
    root.destroy() 

# Bluetooth Controls
bt_frame = tk.LabelFrame(frame, text="Bluetooth Controls", fg="white", bg="#2c2c2c", padx=10, pady=10, font=('Arial', 10, 'bold'))
bt_frame.pack(fill="x", pady=(50, 10))  # Add top padding to move it lower

tk.Entry(bt_frame, textvariable=bluetooth_address, width=25).pack(pady=5)
create_hover_button(bt_frame, "Connect Bluetooth", connect_bluetooth, bg="#007acc", fg="white").pack(pady=5)
create_hover_button(bt_frame, "Scan Bluetooth Devices", lambda: run_async_task(scan_bluetooth), bg="#007acc", fg="white").pack(pady=5)

# Light Controls
light_frame = tk.LabelFrame(frame, text="Light Controls", fg="white", bg="#2c2c2c", padx=10, pady=10, font=('Arial', 10, 'bold'))
light_frame.pack(fill="x", pady=10)

create_hover_button(light_frame, "Red Light On", red_light, bg="#ff4c4c", fg="white").pack(pady=2)
create_hover_button(light_frame, "Red Light Off", red_off, bg="#a83232", fg="white").pack(pady=2)

create_hover_button(light_frame, "Green Light On", green_light, bg="#4caf50", fg="white").pack(pady=2)
create_hover_button(light_frame, "Green Light Off", green_off, bg="#388e3c", fg="white").pack(pady=2)

create_hover_button(light_frame, "White Light On", white_light, bg="#f5f5f5", fg="black").pack(pady=2)
create_hover_button(light_frame, "White Light Off", white_off, bg="#cfcfcf", fg="black").pack(pady=2)

create_hover_button(light_frame, "All Lights On", all_lights_on, bg="#ffd700", fg="black").pack(pady=2)
create_hover_button(light_frame, "All Lights Off", all_lights_off, bg="#b8860b", fg="white").pack(pady=2)

# Power Controls
power_frame = tk.LabelFrame(frame, text="Power Controls", fg="white", bg="#2c2c2c", padx=10, pady=10, font=('Arial', 10, 'bold'))
power_frame.pack(fill="x", pady=10)

create_hover_button(power_frame, "Power Relay", power_relay, bg="#ffa500", fg="black").pack(pady=2)
create_hover_button(power_frame, "Power Off Relay", power_off_relay, bg="#cc8400", fg="black").pack(pady=2)

# Modes and Extras
extras_frame = tk.LabelFrame(frame, text="Modes & Extras", fg="white", bg="#2c2c2c", padx=10, pady=10, font=('Arial', 10, 'bold'))
extras_frame.pack(fill="x", pady=10)

create_hover_button(extras_frame, "Speak Temperature", speak_temperature, bg="#00bcd4", fg="white").pack(pady=2)
create_hover_button(extras_frame, "Gaming Mode", gaming_mode, bg="#673ab7", fg="white").pack(pady=2)
create_hover_button(extras_frame, "Sleep Mode", sleep_mode, bg="#607d8b", fg="white").pack(pady=2)

auto_mode_running = tk.BooleanVar()
tk.Checkbutton(extras_frame, text="Automatic Mode", variable=auto_mode_running, command=toggle_automatic, bg="#2c2c2c", fg="white", selectcolor="#444").pack(pady=5)
create_hover_button(extras_frame, "🎤 Voice Command", voice_command, bg="#e91e63", fg="white").pack(pady=10)

# Exit Button
create_hover_button(frame, "Exit", on_exit, bg="#d32f2f", fg="white").pack(pady=20)  # Add padding to move it lower
# Start Listener

threading.Thread(target=activation_listener, daemon=True).start()
speak("Hi, I'm ready to help.")
root.mainloop()
    