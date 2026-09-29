import datetime
import os
import platform
import threading
import time
import psutil

# Store previous I/O counters for calculating instantaneous transfer rates
_lock = threading.Lock()
_last_io_time = None
_last_net_io = None
_last_disk_io = None


def get_uptime_str(boot_timestamp):
    uptime_seconds = int(time.time() - boot_timestamp)
    days, rem = divmod(uptime_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m {seconds}s")
    return " ".join(parts)


def compute_health(cpu_pct, ram_pct, disk_pct, swap_pct):
    """
    Computes a system health score (0 to 100) and recommendations.
    """
    score = 100
    recommendations = []

    # CPU penalty
    if cpu_pct > 90:
        score -= 30
        recommendations.append("CPU usage is critically high (>90%). Close heavy background tasks.")
    elif cpu_pct > 75:
        score -= 15
        recommendations.append("CPU usage is elevated (>75%).")

    # RAM penalty
    if ram_pct > 90:
        score -= 35
        recommendations.append("RAM is near exhaustion (>90%). Click 'Optimize RAM Now' immediately!")
    elif ram_pct > 75:
        score -= 20
        recommendations.append("Memory pressure is high (>75%). Running RAM optimization is recommended.")
    elif ram_pct > 60:
        score -= 5

    # Disk penalty
    if disk_pct > 90:
        score -= 25
        recommendations.append("Primary drive storage is almost full (>90%). Clean up temporary files.")
    elif disk_pct > 80:
        score -= 10
        recommendations.append("Primary drive storage exceeds 80%.")

    # Swap penalty
    if swap_pct > 80:
        score -= 10
        recommendations.append("Pagefile/Swap utilization is high, system may experience thrashing.")

    score = max(5, min(100, score))

    if score >= 85:
        status_level = 'OPTIMAL'
        status_color = 'emerald'
        recommendations.insert(0, "All system subsystems are operating smoothly within healthy thresholds.")
    elif score >= 70:
        status_level = 'NORMAL'
        status_color = 'blue'
        recommendations.insert(0, "System performance is stable with moderate resource consumption.")
    elif score >= 50:
        status_level = 'WARNING'
        status_color = 'amber'
    else:
        status_level = 'CRITICAL'
        status_color = 'rose'

    return {
        "score": score,
        "status_level": status_level,
        "status_color": status_color,
        "recommendations": recommendations,
    }


def get_current_metrics():
    """
    Collects full, comprehensive system metrics for live updates.
    """
    global _last_io_time, _last_net_io, _last_disk_io

    now = time.time()

    # 1. CPU
    # psutil.cpu_percent with interval=None returns immediate reading based on previous call
    cpu_overall = psutil.cpu_percent(interval=None)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
    cpu_logical = psutil.cpu_count(logical=True) or 1
    cpu_physical = psutil.cpu_count(logical=False) or 1

    try:
        freq = psutil.cpu_freq()
        cpu_freq_current = round(freq.current, 1) if freq else 0
        cpu_freq_max = round(freq.max, 1) if (freq and freq.max) else 0
    except Exception:
        cpu_freq_current = 0
        cpu_freq_max = 0

    # 2. Memory
    vmem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    mem_data = {
        "total_gb": round(vmem.total / (1024 ** 3), 2),
        "used_gb": round(vmem.used / (1024 ** 3), 2),
        "available_gb": round(vmem.available / (1024 ** 3), 2),
        "free_gb": round(vmem.free / (1024 ** 3), 2),
        "percent": vmem.percent,
        "swap_total_gb": round(swap.total / (1024 ** 3), 2),
        "swap_used_gb": round(swap.used / (1024 ** 3), 2),
        "swap_free_gb": round(swap.free / (1024 ** 3), 2),
        "swap_percent": swap.percent,
    }

    # 3. Disks
    partitions_data = []
    primary_disk_pct = 0
    primary_disk_used_gb = 0
    primary_disk_total_gb = 0

    for part in psutil.disk_partitions(all=False):
        try:
            # On Windows, skip floppy or unready drives (like CD-ROM)
            if 'cdrom' in part.opts or part.fstype == '':
                continue
            usage = psutil.disk_usage(part.mountpoint)
            part_info = {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "percent": usage.percent,
            }
            partitions_data.append(part_info)
            if part.mountpoint.upper().startswith('C:') or primary_disk_total_gb == 0:
                primary_disk_pct = usage.percent
                primary_disk_used_gb = round(usage.used / (1024 ** 3), 2)
                primary_disk_total_gb = round(usage.total / (1024 ** 3), 2)
        except (PermissionError, OSError):
            continue

    # 4. Network and Disk I/O Rates
    net_io = psutil.net_io_counters()
    disk_io = psutil.disk_io_counters()

    download_speed_kbps = 0.0
    upload_speed_kbps = 0.0
    disk_read_speed_mb = 0.0
    disk_write_speed_mb = 0.0

    with _lock:
        if _last_io_time is not None:
            time_delta = max(0.2, now - _last_io_time)
            if _last_net_io:
                download_speed_kbps = round(max(0, net_io.bytes_recv - _last_net_io.bytes_recv) / (1024 * time_delta), 1)
                upload_speed_kbps = round(max(0, net_io.bytes_sent - _last_net_io.bytes_sent) / (1024 * time_delta), 1)
            if _last_disk_io and disk_io:
                disk_read_speed_mb = round(max(0, disk_io.read_bytes - _last_disk_io.read_bytes) / (1024 * 1024 * time_delta), 2)
                disk_write_speed_mb = round(max(0, disk_io.write_bytes - _last_disk_io.write_bytes) / (1024 * 1024 * time_delta), 2)

        _last_io_time = now
        _last_net_io = net_io
        _last_disk_io = disk_io

    net_data = {
        "sent_mb": round(net_io.bytes_sent / (1024 * 1024), 1),
        "recv_mb": round(net_io.bytes_recv / (1024 * 1024), 1),
        "upload_speed_kbps": upload_speed_kbps,
        "download_speed_kbps": download_speed_kbps,
    }

    disk_io_data = {
        "read_mb_s": disk_read_speed_mb,
        "write_mb_s": disk_write_speed_mb,
        "read_total_gb": round(disk_io.read_bytes / (1024 ** 3), 2) if disk_io else 0,
        "write_total_gb": round(disk_io.write_bytes / (1024 ** 3), 2) if disk_io else 0,
    }

    # 5. System Info
    boot_time = psutil.boot_time()
    system_info = {
        "os": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
        "hostname": platform.node(),
        "boot_time": datetime.datetime.fromtimestamp(boot_time).strftime('%Y-%m-%d %H:%M:%S'),
        "uptime": get_uptime_str(boot_time),
        "python_version": platform.python_version(),
    }

    # Battery
    battery = psutil.sensors_battery()
    battery_info = None
    if battery:
        battery_info = {
            "percent": battery.percent,
            "power_plugged": battery.power_plugged,
            "secsleft": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None,
        }

    # 6. Top Processes (sorted by memory RSS)
    processes = []
    total_procs = 0
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'memory_percent', 'num_threads', 'username', 'status']):
        try:
            total_procs += 1
            info = proc.info
            mem_info = info['memory_info']
            rss_mb = round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0
            processes.append({
                "pid": info['pid'],
                "name": info['name'] or 'Unknown',
                "cpu_percent": round(info['cpu_percent'] or 0.0, 1),
                "memory_percent": round(info['memory_percent'] or 0.0, 1),
                "memory_mb": rss_mb,
                "num_threads": info['num_threads'] or 1,
                "username": (info['username'] or '').split('\\')[-1],
                "status": info['status'] or 'running',
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort top processes by memory descending
    top_processes = sorted(processes, key=lambda p: p['memory_mb'], reverse=True)[:15]

    # 7. Diagnostic Health Score
    health = compute_health(cpu_overall, vmem.percent, primary_disk_pct, swap.percent)

    return {
        "timestamp": datetime.datetime.now().strftime('%H:%M:%S'),
        "iso_timestamp": datetime.datetime.now().isoformat(),
        "cpu": {
            "overall_percent": cpu_overall,
            "per_core": cpu_per_core,
            "logical_cores": cpu_logical,
            "physical_cores": cpu_physical,
            "freq_current_mhz": cpu_freq_current,
            "freq_max_mhz": cpu_freq_max,
        },
        "memory": mem_data,
        "disks": {
            "partitions": partitions_data,
            "primary_percent": primary_disk_pct,
            "primary_used_gb": primary_disk_used_gb,
            "primary_total_gb": primary_disk_total_gb,
            "io": disk_io_data,
        },
        "network": net_data,
        "system": system_info,
        "battery": battery_info,
        "processes_count": total_procs,
        "top_processes": top_processes,
        "health": health,
    }
