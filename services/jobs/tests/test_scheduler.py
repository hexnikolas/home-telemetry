import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

from app.scheduler import start_scheduler


class TestScheduler:
    """Test APScheduler setup and configuration."""
    
    @pytest.fixture(autouse=True)
    def _setup(self, jobs_env):
        """Setup environment for each test."""
        pass

    def test_scheduler_starts(self):
        """Test that scheduler initializes without errors."""
        with patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            with patch("app.scheduler.sync_mqtt_topics_to_redis"):
                with patch("app.scheduler.train_temperature_model"):
                    scheduler = start_scheduler()
        
        # Verify scheduler was created and started
        mock_scheduler.start.assert_called_once()

    def test_scheduler_adds_mqtt_job(self):
        """Test that MQTT sync job is scheduled."""
        with patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            with patch("app.scheduler.sync_mqtt_topics_to_redis") as mock_mqtt_task:
                with patch("app.scheduler.train_temperature_model"):
                    scheduler = start_scheduler()
            
            # Verify add_job was called for MQTT sync
            calls = [c for c in mock_scheduler.add_job.call_args_list]
            assert any("sync_mqtt_topics" in str(c) for c in calls)

    def test_scheduler_adds_open_meteo_job(self):
        """Test that Open Meteo fetch job is scheduled."""
        with patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            with patch("app.scheduler.sync_mqtt_topics_to_redis"):
                with patch("app.scheduler.fetch_open_meteo_data") as mock_meteo_task:
                    with patch("app.scheduler.train_temperature_model"):
                        scheduler = start_scheduler()
            
            # Verify add_job was called for Open Meteo
            calls = [c for c in mock_scheduler.add_job.call_args_list]
            assert any("fetch_open_meteo" in str(c) for c in calls)

    def test_scheduler_adds_temperature_model_job(self):
        """Test that temperature model training job is scheduled."""
        with patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            with patch("app.scheduler.sync_mqtt_topics_to_redis"):
                with patch("app.scheduler.fetch_open_meteo_data"):
                    with patch("app.scheduler.train_temperature_model") as mock_train_task:
                        scheduler = start_scheduler()
            
            # Verify add_job was called for temperature model
            calls = [c for c in mock_scheduler.add_job.call_args_list]
            assert any("train_temperature" in str(c) for c in calls)

    def test_scheduler_enqueues_startup_jobs(self):
        """Test that startup jobs are enqueued immediately."""
        with patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            with patch("app.scheduler.sync_mqtt_topics_to_redis") as mock_mqtt_task:
                with patch("app.scheduler.train_temperature_model") as mock_train_task:
                    scheduler = start_scheduler()
            
            # Verify startup jobs were sent
            assert mock_mqtt_task.send.called
            assert mock_train_task.send.called

    def test_cron_trigger_mqtt_every_5_minutes(self):
        """Test that MQTT sync is scheduled every 5 minutes."""
        with patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            with patch("app.scheduler.CronTrigger") as mock_cron_class:
                with patch("app.scheduler.sync_mqtt_topics_to_redis"):
                    with patch("app.scheduler.train_temperature_model"):
                        scheduler = start_scheduler()
            
            # Check CronTrigger was called with correct minute pattern
            calls = [c for c in mock_cron_class.call_args_list]
            # Should have calls with minute="*/5"
            assert any("*/5" in str(c) for c in calls)

    def test_cron_trigger_open_meteo_at_00_30(self):
        """Test that Open Meteo is scheduled at :00 and :30 every hour."""
        with patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            with patch("app.scheduler.CronTrigger") as mock_cron_class:
                with patch("app.scheduler.sync_mqtt_topics_to_redis"):
                    with patch("app.scheduler.train_temperature_model"):
                        scheduler = start_scheduler()
            
            # Check CronTrigger was called with correct minute pattern
            calls = [c for c in mock_cron_class.call_args_list]
            # Should have calls with minute="0,30"
            assert any("0,30" in str(c) for c in calls)

    def test_cron_trigger_temperature_model_on_odd_days(self):
        """Test that temperature model training is scheduled on all days at midnight."""
        with patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            with patch("app.scheduler.CronTrigger") as mock_cron_class:
                with patch("app.scheduler.sync_mqtt_topics_to_redis"):
                    with patch("app.scheduler.fetch_open_meteo_data"):
                        with patch("app.scheduler.train_temperature_model"):
                            scheduler = start_scheduler()
            
            # Check CronTrigger was called with correct day pattern for all days
            calls = [c for c in mock_cron_class.call_args_list]
            # Should have calls with all days: 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
            # Check the keyword arguments for the day pattern
            assert any("1,2,3,4,5" in str(c.kwargs.get("day", "")) for c in calls)
