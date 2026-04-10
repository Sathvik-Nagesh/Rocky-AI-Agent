import subprocess
import re
import os
import logging

def scan_network() -> str:
    """Scan the local network for active devices."""
    print("[AEGIS] Initiating LAN scan...")
    devices = []
    
    try:
        # 1. Try system ARP table first (Works without admin often)
        output = subprocess.check_output(["arp", "-a"], text=True)
        # Regex to find IP addresses and MACs
        matches = re.findall(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-f-]{17})", output)
        for ip, mac in matches:
            if ip.startswith("192.168") or ip.startswith("10.0") or ip.startswith("172."):
                devices.append({ "ip": ip, "mac": mac, "name": "Unknown Device" })
                
        # 2. Add some logic to resolve names if possible (via ping -a)
        # (This is slow, so we'll just do it for the first 3)
        for dev in devices[:3]:
            try:
                name_out = subprocess.check_output(["ping", "-a", "-n", "1", "-w", "100", dev["ip"]], text=True)
                name_match = re.search(r"Pinging ([\w.-]+)", name_out)
                if name_match:
                    dev["name"] = name_match.group(1)
            except:
                pass
                
    except Exception as e:
        return f"Aegis scan failed: {e}"
        
    if not devices:
        return "Aegis found no active secondary devices on this node."
        
    report = [f"{d['name']} ({d['ip']})" for d in devices]
    return "Network Security Audit Result:\n- " + "\n- ".join(report)

def check_for_intruders(known_devices: list) -> list:
    """Check if any new devices have joined since last scan."""
    # (Simplified logic for now)
    return []
