"""
System Health Monitor using psutil.
Tracks CPU, RAM, and Disk usage to display in the HUD.
"""

import psutil
import logging

def get_system_stats() -> str:
    """Returns a compact string of system health metrics."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        # Add a little Rocky-style commentary if things are high
        status = "Optimal"
        if cpu > 80 or ram > 85:
            status = "Strained"
        
        return f"CPU: {cpu}% | RAM: {ram}% | DISK: {disk}% | STATUS: {status}"
    except Exception as e:
        logging.error(f"Error fetching system stats: {e}")
        return "System Health Data Unavailable"

def get_detailed_stats() -> dict:
    """Returns detailed metrics for potential widget rendering."""
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "temp": "N/A" # Requires hardware-specific libs like OpenHardwareMonitor or specific sensors
    }
