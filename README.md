# SysMonitor Pro - Python Django Live System Status & RAM Optimizer

A high-performance Windows system telemetry dashboard and memory optimization platform built with Python Django, `psutil`, Windows Native Psapi/Kernel32 APIs, and Chart.js.

---

## 🔒 Security & Authentication
Strict access control is implemented across the entire application:
- **No unauthenticated access allowed**: Any attempt to open the dashboard, API endpoints, or reports without logging in is redirected to the login gateway.
- **Preconfigured Credentials**:
  - **Username**: `Avinash`
  - **Password**: `Avinash@526`

---

## 🚀 Key Features

### 1. ⚡ Live System Tracking & Real-Time Telemetry
- **CPU Monitoring**:
  - Overall CPU percentage with smooth animated gauges.
  - Per-core workload visualizer (interactive bar grid for all logical cores/threads).
  - Current CPU frequency (MHz) and max frequency.
  - Physical vs. logical core counts.
- **RAM / Memory Tracking**:
  - Live RAM usage percentage and real-time usage (Used GB / Total GB).
  - Available memory and Free memory statistics.
  - Swap / Windows Pagefile utilization tracking.
- **Disk & Storage Subsystem**:
  - Partition monitoring for all drives (`C:`, `D:`, etc.) with filesystem types and storage limits.
  - Live Disk I/O Read and Write throughput rates (MB/s).
- **Network Throughput**:
  - Real-time download & upload bandwidth rate monitors (KB/s and MB/s).
  - Total cumulative sent and received bandwidth (MB).
- **System Information**:
  - Operating System details, Windows build, platform architecture.
  - Live uptime counter and system boot timestamp.
  - Python runtime version.
  - Laptop battery status & power-plugged state (if applicable).

### 2. ⚡ RAM Optimization & System Pressure Reduction
- **One-Click Memory Trimmer**:
  - Calls native Windows APIs (`psapi.EmptyWorkingSet` and `kernel32.SetProcessWorkingSetSize`) across all active processes.
  - Reclaims cached/idle memory from working sets directly back to the Windows memory manager.
  - Executes Python runtime garbage collection (`gc.collect()`).
  - Displays instant before-and-after memory statistics (e.g., *"Freed 550 MB RAM across 300 processes"*).
- **Process Pressure Reducer**:
  - Top 15 memory-consuming processes live table.
  - Displays Process Name, PID, RAM RSS (MB), RAM %, CPU %, Status, and User.
  - Instant process search filter.
  - Safe **"End"** button with confirmation prompt to safely terminate heavy or rogue tasks and relieve immediate memory/CPU pressure.

### 3. 📊 Interactive Graphs & Real-Time Charts
- **CPU & RAM Trajectory Chart**: Dynamic multi-line chart tracking rolling usage percentages.
- **Network Speed Chart**: Real-time download vs. upload streaming speed curves.
- **Adjustable Polling Controller**: Select update frequencies: `1s (Ultra Live)`, `2s (Default)`, `5s (Low CPU)`, or `Paused`.

### 4. 📑 Comprehensive Health Reports & Analytics
- **System Diagnostic Health Score**: Dynamic rating (0-100) with color-coded status badge (`OPTIMAL`, `NORMAL`, `WARNING`, `CRITICAL`).
- **Automated Recommendations**: Actionable advice generated dynamically based on system stress.
- **Historical Snapshot Log**: Periodic database snapshots capturing historical system performance.
- **Audit Log of RAM Optimizations**: Full history of who ran optimizations, how much RAM was freed, and when.
- **Export Options**:
  - **Export to CSV**: Instant download of all recorded snapshots.
  - **Print / PDF Audit Report**: Clean, printer-friendly executive summary report ready to print or save as PDF.

---

## 🛠️ How to Start the Server

### Option A: Using the Batch Launcher (Easiest)
Double-click `run_server.bat` in this folder, or run:
```cmd
run_server.bat
```

### Option B: Manual Terminal Execution
```powershell
cd C:\Users\Avinash\system_monitor
python init_setup.py
python manage.py runserver 0.0.0.0:8000
```

Open your browser at:
👉 **http://127.0.0.1:8000**
