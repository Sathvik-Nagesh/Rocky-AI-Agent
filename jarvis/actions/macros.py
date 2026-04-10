import json
import os
import time
import logging
import threading
from pynput import mouse, keyboard

MACRO_FILE = "jarvis/memory/macros.json"

class MacroRecorder:
    def __init__(self):
        self.events = []
        self.is_recording = False
        self.start_time = 0
        self.mouse_listener = None
        self.kb_listener = None

    def _on_click(self, x, y, button, pressed):
        if self.is_recording:
            self.events.append({
                "type": "click",
                "x": x, "y": y,
                "button": str(button),
                "pressed": pressed,
                "time": time.time() - self.start_time
            })

    def _on_press(self, key):
        if self.is_recording:
            try:
                k = key.char
            except AttributeError:
                k = str(key)
            self.events.append({
                "type": "key",
                "key": k,
                "time": time.time() - self.start_time
            })

    def start(self):
        self.events = []
        self.is_recording = True
        self.start_time = time.time()
        self.mouse_listener = mouse.Listener(on_click=self._on_click)
        self.kb_listener = keyboard.Listener(on_press=self._on_press)
        self.mouse_listener.start()
        self.kb_listener.start()
        print("[VORTEX] Recording started...")

    def stop(self, macro_name: str):
        self.is_recording = False
        if self.mouse_listener: self.mouse_listener.stop()
        if self.kb_listener: self.kb_listener.stop()
        
        # Save to file
        macros = {}
        if os.path.exists(MACRO_FILE):
            with open(MACRO_FILE, 'r') as f:
                macros = json.load(f)
        
        macros[macro_name] = self.events
        with open(MACRO_FILE, 'w') as f:
            json.dump(macros, f, indent=2)
        print(f"[VORTEX] Saved macro: {macro_name}")

recorder = MacroRecorder()

def play_macro(name: str):
    """Replay a recorded macro."""
    if not os.path.exists(MACRO_FILE):
        return "No macros found."
    
    with open(MACRO_FILE, 'r') as f:
        macros = json.load(f)
    
    if name not in macros:
        return f"Macro '{name}' not found."
    
    events = macros[name]
    from pynput.mouse import Button, Controller as MouseController
    from pynput.keyboard import Controller as KBController
    
    m = MouseController()
    k = KBController()
    
    print(f"[VORTEX] Replaying {name}...")
    start_time = time.time()
    
    for event in events:
        # Wait until the correct relative time
        elapsed = time.time() - start_time
        wait = event['time'] - elapsed
        if wait > 0:
            time.sleep(wait)
            
        if event['type'] == 'click':
            m.position = (event['x'], event['y'])
            # Parse button string
            btn = Button.left if 'left' in event['button'] else Button.right
            if event['pressed']:
                m.press(btn)
            else:
                m.release(btn)
        
        elif event['type'] == 'key':
            key_val = event['key']
            # Reconstruct special keys if needed
            k.press(key_val.replace("Key.", ""))
            k.release(key_val.replace("Key.", ""))

    return f"Macro '{name}' completed successfully."
