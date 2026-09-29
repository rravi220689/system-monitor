from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('reports/', views.reports_view, name='reports'),
    path('reports/csv/', views.export_csv_view, name='export_csv'),
    path('reports/print/', views.print_report_view, name='print_report'),
    path('api/metrics/', views.api_metrics_view, name='api_metrics'),
    path('api/optimize-ram/', views.api_optimize_ram_view, name='api_optimize_ram'),
    path('api/kill-process/', views.api_kill_process_view, name='api_kill_process'),
]
