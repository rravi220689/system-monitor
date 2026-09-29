import csv
import json
import logging
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Max, Min, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .metrics import get_current_metrics
from .models import OptimizationLog, SystemSnapshot
from .optimizer import optimize_ram_and_reduce_pressure, terminate_process_safely

logger = logging.getLogger(__name__)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next') or 'dashboard'
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect(next_url)
        else:
            messages.error(request, "Access Denied: Invalid credentials provided. Access is strictly restricted.")

    return render(request, 'dashboard/login.html')


def logout_view(request):
    auth_logout(request)
    messages.info(request, "You have been logged out securely.")
    return redirect('login')


@login_required
def dashboard_view(request):
    current = get_current_metrics()

    # Pre-populate initial chart data from recent snapshots (last 20)
    recent_snapshots = list(SystemSnapshot.objects.order_by('-timestamp')[:20])
    recent_snapshots.reverse()

    chart_labels = [s.timestamp.strftime('%H:%M:%S') for s in recent_snapshots]
    chart_cpu = [s.cpu_percent for s in recent_snapshots]
    chart_ram = [s.memory_percent for s in recent_snapshots]

    # Save a fresh snapshot if none exists or last is older than 30s
    last_snapshot = SystemSnapshot.objects.order_by('-timestamp').first()
    if not last_snapshot or (timezone.now() - last_snapshot.timestamp).total_seconds() > 30:
        _save_snapshot(current)

    context = {
        'metrics': current,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_cpu_json': json.dumps(chart_cpu),
        'chart_ram_json': json.dumps(chart_ram),
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def api_metrics_view(request):
    metrics = get_current_metrics()

    # Automatically persist snapshot every ~15 seconds to build report history
    last_snapshot = SystemSnapshot.objects.order_by('-timestamp').first()
    if not last_snapshot or (timezone.now() - last_snapshot.timestamp).total_seconds() >= 15:
        _save_snapshot(metrics)

    return JsonResponse(metrics)


@login_required
@require_POST
def api_optimize_ram_view(request):
    user_name = request.user.username if request.user.is_authenticated else 'Avinash'
    result = optimize_ram_and_reduce_pressure(user_name=user_name)
    return JsonResponse(result)


@login_required
@require_POST
def api_kill_process_view(request):
    try:
        data = json.loads(request.body)
        pid = int(data.get('pid'))
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid PID parameter provided."}, status=400)

    result = terminate_process_safely(pid)
    return JsonResponse(result)


@login_required
def reports_view(request):
    # Historical aggregate statistics
    snapshots = SystemSnapshot.objects.all()
    count = snapshots.count()

    stats = {
        'total_snapshots': count,
        'avg_cpu': round(snapshots.aggregate(Avg('cpu_percent'))['cpu_percent__avg'] or 0.0, 1),
        'max_cpu': round(snapshots.aggregate(Max('cpu_percent'))['cpu_percent__max'] or 0.0, 1),
        'avg_ram': round(snapshots.aggregate(Avg('memory_percent'))['memory_percent__avg'] or 0.0, 1),
        'max_ram': round(snapshots.aggregate(Max('memory_percent'))['memory_percent__max'] or 0.0, 1),
    }

    opt_logs = OptimizationLog.objects.all()
    opt_stats = {
        'total_optimizations': opt_logs.count(),
        'total_freed_mb': round(opt_logs.aggregate(Sum('memory_freed_mb'))['memory_freed_mb__sum'] or 0.0, 1),
        'total_processes_trimmed': opt_logs.aggregate(Sum('processes_trimmed'))['processes_trimmed__sum'] or 0,
    }

    recent_snapshots = snapshots.order_by('-timestamp')[:50]
    recent_optimizations = opt_logs.order_by('-timestamp')[:20]
    current = get_current_metrics()

    # Timeline data for reports chart (last 30)
    timeline_snapshots = list(snapshots.order_by('-timestamp')[:30])
    timeline_snapshots.reverse()
    timeline_labels = [s.timestamp.strftime('%H:%M:%S') for s in timeline_snapshots]
    timeline_cpu = [s.cpu_percent for s in timeline_snapshots]
    timeline_ram = [s.memory_percent for s in timeline_snapshots]

    context = {
        'stats': stats,
        'opt_stats': opt_stats,
        'recent_snapshots': recent_snapshots,
        'recent_optimizations': recent_optimizations,
        'current': current,
        'timeline_labels_json': json.dumps(timeline_labels),
        'timeline_cpu_json': json.dumps(timeline_cpu),
        'timeline_ram_json': json.dumps(timeline_ram),
    }
    return render(request, 'dashboard/reports.html', context)


@login_required
def export_csv_view(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="system_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'CPU Usage (%)', 'CPU Freq (MHz)', 'RAM Usage (%)',
        'RAM Used (GB)', 'RAM Total (GB)', 'Disk Usage (%)', 'Disk Used (GB)',
        'Network Sent (MB)', 'Network Recv (MB)', 'Active Processes', 'Health Score', 'Status'
    ])

    for s in SystemSnapshot.objects.order_by('-timestamp')[:500]:
        writer.writerow([
            s.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            s.cpu_percent,
            s.cpu_frequency_mhz,
            s.memory_percent,
            s.memory_used_gb,
            s.memory_total_gb,
            s.disk_percent,
            s.disk_used_gb,
            s.network_sent_mb,
            s.network_recv_mb,
            s.active_processes_count,
            s.health_score,
            s.status_level
        ])

    return response


@login_required
def print_report_view(request):
    current = get_current_metrics()
    snapshots = SystemSnapshot.objects.all()
    opt_logs = OptimizationLog.objects.all()

    stats = {
        'avg_cpu': round(snapshots.aggregate(Avg('cpu_percent'))['cpu_percent__avg'] or 0.0, 1),
        'max_cpu': round(snapshots.aggregate(Max('cpu_percent'))['cpu_percent__max'] or 0.0, 1),
        'avg_ram': round(snapshots.aggregate(Avg('memory_percent'))['memory_percent__avg'] or 0.0, 1),
        'max_ram': round(snapshots.aggregate(Max('memory_percent'))['memory_percent__max'] or 0.0, 1),
        'total_optimizations': opt_logs.count(),
        'total_freed_mb': round(opt_logs.aggregate(Sum('memory_freed_mb'))['memory_freed_mb__sum'] or 0.0, 1),
    }

    recent_snapshots = snapshots.order_by('-timestamp')[:15]
    recent_optimizations = opt_logs.order_by('-timestamp')[:10]

    context = {
        'current': current,
        'stats': stats,
        'recent_snapshots': recent_snapshots,
        'recent_optimizations': recent_optimizations,
        'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z'),
    }
    return render(request, 'dashboard/print_report.html', context)


def _save_snapshot(metrics):
    try:
        SystemSnapshot.objects.create(
            cpu_percent=metrics['cpu']['overall_percent'],
            cpu_frequency_mhz=metrics['cpu']['freq_current_mhz'],
            memory_percent=metrics['memory']['percent'],
            memory_used_gb=metrics['memory']['used_gb'],
            memory_total_gb=metrics['memory']['total_gb'],
            memory_available_gb=metrics['memory']['available_gb'],
            swap_percent=metrics['memory']['swap_percent'],
            disk_percent=metrics['disks']['primary_percent'],
            disk_used_gb=metrics['disks']['primary_used_gb'],
            disk_total_gb=metrics['disks']['primary_total_gb'],
            network_sent_mb=metrics['network']['sent_mb'],
            network_recv_mb=metrics['network']['recv_mb'],
            active_processes_count=metrics['processes_count'],
            health_score=metrics['health']['score'],
            status_level=metrics['health']['status_level'],
        )
    except Exception as e:
        logger.warning(f"Could not persist SystemSnapshot: {e}")
