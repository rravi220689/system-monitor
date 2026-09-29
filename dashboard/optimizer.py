import ctypes
import gc
import logging
import os
import psutil
from .models import OptimizationLog

logger = logging.getLogger(__name__)

# Protected process names to prevent accidental termination
PROTECTED_PROCESSES = {
    'system', 'system idle process', 'registry', 'smss.exe', 'csrss.exe',
    'wininit.exe', 'services.exe', 'lsass.exe', 'svchost.exe', 'fontdrvhost.exe',
    'winlogon.exe', 'dwm.exe', 'explorer.exe', 'python.exe', 'pythonw.exe'
}


def trim_system_memory():
    """
    Trims the working set of all accessible processes on Windows.
    This effectively tells Windows memory manager to page out idle memory
    and reclaim dirty/unused working set pages back to the available pool.
    """
    gc.collect()
    trimmed_count = 0
    errors_count = 0

    if os.name == 'nt':
        try:
            PROCESS_SET_QUOTA = 0x0100
            PROCESS_QUERY_INFORMATION = 0x0400
            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi

            # First trim the current process
            try:
                psapi.EmptyWorkingSet(kernel32.GetCurrentProcess())
                kernel32.SetProcessWorkingSetSize(kernel32.GetCurrentProcess(), -1, -1)
            except Exception as e:
                logger.debug(f"Failed to trim current process: {e}")

            # Then iterate through running processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pid = proc.info['pid']
                    if pid in (0, 4):  # System Idle, System
                        continue
                    handle = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
                    if handle:
                        if psapi.EmptyWorkingSet(handle):
                            trimmed_count += 1
                        kernel32.CloseHandle(handle)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    errors_count += 1
                except Exception:
                    errors_count += 1
        except Exception as e:
            logger.error(f"Error executing Windows memory trim: {e}")
    else:
        # Non-windows fallback (e.g. linux drop caches / python gc)
        gc.collect()

    return trimmed_count


def optimize_ram_and_reduce_pressure(user_name='Avinash'):
    """
    Performs full system RAM optimization, collects garbage,
    flushes working sets, logs the event, and returns before/after stats.
    """
    mem_before = psutil.virtual_memory()
    before_bytes = mem_before.used
    before_percent = mem_before.percent
    before_mb = before_bytes / (1024 * 1024)

    # Perform trimming
    trimmed_count = trim_system_memory()

    # Re-evaluate
    mem_after = psutil.virtual_memory()
    after_bytes = mem_after.used
    after_percent = mem_after.percent
    after_mb = after_bytes / (1024 * 1024)

    freed_mb = max(0.0, before_mb - after_mb)
    freed_gb = freed_mb / 1024.0

    # Save to database log
    try:
        OptimizationLog.objects.create(
            memory_before_mb=round(before_mb, 2),
            memory_after_mb=round(after_mb, 2),
            memory_freed_mb=round(freed_mb, 2),
            percent_before=round(before_percent, 1),
            percent_after=round(after_percent, 1),
            processes_trimmed=trimmed_count,
            initiated_by=user_name,
            details=f"Trimmed {trimmed_count} process working sets. Reclaimed {freed_mb:.1f} MB RAM."
        )
    except Exception as e:
        logger.warning(f"Could not persist OptimizationLog: {e}")

    return {
        "success": True,
        "freed_mb": round(freed_mb, 1),
        "freed_gb": round(freed_gb, 2),
        "before_mb": round(before_mb, 1),
        "after_mb": round(after_mb, 1),
        "before_percent": round(before_percent, 1),
        "after_percent": round(after_percent, 1),
        "total_gb": round(mem_after.total / (1024 ** 3), 2),
        "available_gb": round(mem_after.available / (1024 ** 3), 2),
        "processes_trimmed": trimmed_count,
        "message": f"Successfully optimized memory! Freed {freed_mb:.1f} MB across {trimmed_count} processes."
    }


def terminate_process_safely(pid, current_user_pid=None):
    """
    Safely terminates an unneeded high-memory process by PID.
    Guards against killing core OS components or current server.
    """
    if current_user_pid is None:
        current_user_pid = os.getpid()

    if pid == current_user_pid:
        return {"success": False, "error": "Cannot terminate the active monitoring server process."}

    try:
        proc = psutil.Process(pid)
        name = proc.name().lower()

        if name in PROTECTED_PROCESSES:
            return {"success": False, "error": f"Refusing to terminate critical system process: {name}"}

        proc_mem_mb = proc.memory_info().rss / (1024 * 1024)
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except psutil.TimeoutExpired:
            proc.kill()

        return {
            "success": True,
            "message": f"Process {name} (PID: {pid}) terminated successfully. Reclaimed ~{proc_mem_mb:.1f} MB RAM."
        }
    except psutil.NoSuchProcess:
        return {"success": False, "error": f"Process PID {pid} no longer exists."}
    except psutil.AccessDenied:
        return {"success": False, "error": f"Access denied. Insufficient privileges to terminate PID {pid}."}
    except Exception as e:
        return {"success": False, "error": str(e)}
