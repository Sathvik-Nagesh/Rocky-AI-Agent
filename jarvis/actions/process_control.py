"""
Process Terminator — Advanced System Control.
Identifies top CPU/RAM hogs via psutil and gives Rocky the ability to kill them
after explicit user confirmation.
"""

import psutil
import subprocess
import logging


def get_top_processes(top_n: int = 5) -> list[dict]:
    """Returns top N processes sorted by CPU usage."""
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Sort by CPU, then memory as tiebreaker
    procs.sort(key=lambda p: (p.get('cpu_percent', 0) + p.get('memory_percent', 0)), reverse=True)
    return procs[:top_n]


def describe_top_processes() -> str:
    """Returns a human-readable summary of the top CPU hogs."""
    procs = get_top_processes(3)
    if not procs:
        return "Could not read process list."
    parts = []
    for p in procs:
        name = p.get('name', 'unknown')
        cpu  = p.get('cpu_percent', 0)
        mem  = p.get('memory_percent', 0)
        parts.append(f"{name} at {cpu:.1f}% CPU and {mem:.1f}% RAM")
    return "Top resource users: " + ", then ".join(parts) + "."


# 🛡️ SECURITY: Never kill these critical OS processes
_PROTECTED_PROCESSES = {
    "system", "csrss.exe", "wininit.exe", "services.exe",
    "svchost.exe", "lsass.exe", "winlogon.exe", "dwm.exe",
    "explorer.exe", "smss.exe", "spoolsv.exe"
}

def kill_process_by_name(name: str) -> str:
    """Kill all processes with the given name. Requires confirmation before calling."""
    killed = 0
    errors = 0
    name_lower = name.lower()

    if name_lower in _PROTECTED_PROCESSES or name_lower + ".exe" in _PROTECTED_PROCESSES:
        return f"Blocked: {name} is a protected system process. Terminating it would destabilize Windows."

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if name_lower in proc.info['name'].lower():
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logging.debug(f"Process kill error: {e}")
            errors += 1

    if killed > 0:
        return f"Terminated {killed} instance(s) of {name}. System should stabilise."
    elif errors > 0:
        return f"Access denied when trying to terminate {name}. Try running Rocky as Administrator."
    else:
        return f"No process named {name} was found running."


def is_system_stressed() -> tuple[bool, str]:
    """
    Returns (True, reason_string) if the system is under significant strain.
    Used by self-repair and proactive observer.
    """
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    
    if cpu > 85:
        return True, f"CPU critically high at {cpu:.0f}%"
    if ram > 90:
        return True, f"RAM critically high at {ram:.0f}%"
    return False, ""
