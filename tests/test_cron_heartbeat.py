from companio.cron import CronJob, CronSchedule


class TestCronTypes:
    def test_cron_schedule_every(self):
        s = CronSchedule(kind="every", every_ms=300_000)
        assert s.every_ms == 300_000
        assert s.kind == "every"

    def test_cron_schedule_cron_expr(self):
        s = CronSchedule(kind="cron", expr="0 9 * * *")
        assert s.expr == "0 9 * * *"
        assert s.kind == "cron"

    def test_cron_schedule_at(self):
        s = CronSchedule(kind="at", at_ms=1700000000000)
        assert s.at_ms == 1700000000000
        assert s.kind == "at"

    def test_cron_schedule_defaults(self):
        s = CronSchedule(kind="every")
        assert s.at_ms is None
        assert s.every_ms is None
        assert s.expr is None
        assert s.tz is None

    def test_cron_job_creation(self):
        schedule = CronSchedule(kind="every", every_ms=60_000)
        job = CronJob(
            id="test-job",
            name="remind me",
            enabled=True,
            schedule=schedule,
        )
        assert job.id == "test-job"
        assert job.name == "remind me"
        assert job.enabled is True
        assert job.schedule.every_ms == 60_000

    def test_cron_job_defaults(self):
        job = CronJob(id="j1", name="default-job")
        assert job.enabled is True
        assert job.delete_after_run is False
        assert job.created_at_ms == 0
        assert job.state.next_run_at_ms is None
        assert job.payload.kind == "agent_turn"


class TestHeartbeatConfig:
    def test_heartbeat_default_interval(self):
        """Heartbeat interval should default to 600 seconds (10 minutes)."""
        import inspect

        from companio.heartbeat import HeartbeatService

        sig = inspect.signature(HeartbeatService.__init__)
        default = sig.parameters["interval_s"].default
        assert default == 600, f"Expected 600s (10 min), got {default}s"
