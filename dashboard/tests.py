import json
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from .models import OptimizationLog, SystemSnapshot


class SystemMonitorTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'Avinash'
        self.password = 'Avinash@526'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password
        )

    def test_unauthenticated_access_is_blocked(self):
        """Verify pages are blocked without credentials and redirect to login."""
        protected_urls = [
            reverse('dashboard'),
            reverse('reports'),
            reverse('api_metrics'),
            reverse('print_report'),
            reverse('export_csv'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"URL {url} should redirect unauthenticated users")
            self.assertTrue('/login/' in response.url, f"URL {url} should redirect to /login/")

    def test_invalid_login_credentials(self):
        """Verify invalid credentials cannot authenticate."""
        response = self.client.post(reverse('login'), {
            'username': 'wronguser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Access Denied")

    def test_valid_login_and_dashboard_access(self):
        """Verify user Avinash with Avinash@526 logs in successfully and accesses dashboard."""
        login_res = self.client.post(reverse('login'), {
            'username': self.username,
            'password': self.password
        }, follow=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.context['user'].is_authenticated)
        self.assertContains(login_res, "SysMonitor")
        self.assertContains(login_res, "Optimize RAM")

    def test_api_metrics_authenticated(self):
        """Verify api/metrics returns live JSON when logged in."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('api_metrics'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('cpu', data)
        self.assertIn('memory', data)
        self.assertIn('disks', data)
        self.assertIn('network', data)
        self.assertIn('health', data)
        self.assertIn('top_processes', data)

    def test_api_optimize_ram(self):
        """Verify RAM optimization endpoint triggers and logs."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('api_optimize_ram'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('freed_mb', data)
        self.assertIn('processes_trimmed', data)
        self.assertTrue(OptimizationLog.objects.filter(initiated_by=self.username).exists())

    def test_reports_page(self):
        """Verify reports page renders historical data."""
        self.client.login(username=self.username, password=self.password)
        # Create a sample snapshot
        SystemSnapshot.objects.create(
            cpu_percent=15.0,
            cpu_frequency_mhz=2400.0,
            memory_percent=45.0,
            memory_used_gb=7.2,
            memory_total_gb=16.0,
            disk_percent=55.0,
            disk_used_gb=120.0,
            disk_total_gb=256.0,
            health_score=95,
            status_level='OPTIMAL'
        )
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Telemetry & Health Reports")

    def test_export_csv(self):
        """Verify CSV export streams valid data."""
        self.client.login(username=self.username, password=self.password)
        SystemSnapshot.objects.create(
            cpu_percent=20.0,
            memory_percent=50.0,
            memory_used_gb=8.0,
            memory_total_gb=16.0,
            disk_percent=60.0,
            disk_used_gb=150.0,
            disk_total_gb=256.0,
            health_score=90,
            status_level='OPTIMAL'
        )
        response = self.client.get(reverse('export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue('CPU Usage (%)' in response.content.decode('utf-8'))
