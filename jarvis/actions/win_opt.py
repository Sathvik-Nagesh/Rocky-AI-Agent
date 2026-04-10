import os
import shutil
import psutil
import logging
import subprocess

def optimize_system() -> str:
    """Perform a multi-point system optimization."""
    report = []
    
    # 1. Clear temp files
    temp_folders = [
        os.environ.get('TEMP'),
        os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
    ]
    
    cleaned_size = 0
    for folder in temp_folders:
        if not folder or not os.path.exists(folder): continue
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    cleaned_size += os.path.getsize(file_path)
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    cleaned_size += sum(os.path.getsize(os.path.join(dirpath, f)) for dirpath, _, filenames in os.walk(file_path) for f in filenames)
                    shutil.rmtree(file_path)
            except Exception:
                continue # Busy files stay
                
    if cleaned_size > 0:
        report.append(f"Purged {cleaned_size // (1024*1024)}MB of temporary debris.")
    
    # 2. Check Disk Health
    usage = shutil.disk_usage("/")
    free_gb = usage.free // (1024**3)
    if free_gb < 20:
        report.append(f"CRITICAL: Main drive has only {free_gb}GB left. Recommend further cleanup.")
    else:
        report.append(f"Storage remains healthy ({free_gb}GB free).")

    # 3. Memory Flush (Empty standby list is tricky via pure python, but we can suggest app closure)
    mem = psutil.virtual_memory()
    if mem.percent > 85:
        report.append(f"Memory load is high ({mem.percent}%). Recommending closure of background browsers.")

    return "System Optimization Report:\n- " + "\n- ".join(report)

def get_proactive_advice() -> str:
    """Return a single sentence of proactive system advice."""
    cpu = psutil.cpu_percent()
    if cpu > 70:
        return "I've noticed significant CPU load. Shall I identify the culprit?"
    
    # Battery check if laptop
    try:
        battery = psutil.sensors_battery()
        if battery and not battery.power_plugged and battery.percent < 30:
            return f"Strategic warning: Power level at {battery.percent}%. Suggest connecting the reactor."
    except:
        pass
        
    return "All systems optimal. Performance is within peak parameters."
