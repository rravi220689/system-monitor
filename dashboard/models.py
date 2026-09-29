from django.db import models
from django.utils import timezone


class SystemSnapshot(models.Model):
    STATUS_CHOICES = [
        ('OPTIMAL', 'Optimal'),
        ('NORMAL', 'Normal'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    cpu_percent = models.FloatField(help_text="Overall CPU usage %")
    cpu_frequency_mhz = models.FloatField(default=0.0, help_text="Current CPU frequency in MHz")
    memory_percent = models.FloatField(help_text="RAM usage %")
    memory_used_gb = models.FloatField(help_text="RAM used in GB")
    memory_total_gb = models.FloatField(help_text="Total RAM in GB")
    memory_available_gb = models.FloatField(default=0.0, help_text="Available RAM in GB")
    swap_percent = models.FloatField(default=0.0, help_text="Swap/Pagefile usage %")
    disk_percent = models.FloatField(help_text="Primary disk usage %")
    disk_used_gb = models.FloatField(help_text="Primary disk used GB")
    disk_total_gb = models.FloatField(help_text="Primary disk total GB")
    network_sent_mb = models.FloatField(default=0.0, help_text="Total MB sent")
    network_recv_mb = models.FloatField(default=0.0, help_text="Total MB received")
    active_processes_count = models.IntegerField(default=0)
    health_score = models.IntegerField(default=100, help_text="Health Score (0-100)")
    status_level = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPTIMAL')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Snapshot at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - CPU: {self.cpu_percent}%, RAM: {self.memory_percent}%"


class OptimizationLog(models.Model):
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    memory_before_mb = models.FloatField()
    memory_after_mb = models.FloatField()
    memory_freed_mb = models.FloatField()
    percent_before = models.FloatField(default=0.0)
    percent_after = models.FloatField(default=0.0)
    processes_trimmed = models.IntegerField(default=0)
    initiated_by = models.CharField(max_length=100, default='Avinash')
    details = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Optimization at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - Freed {self.memory_freed_mb:.1f} MB"
