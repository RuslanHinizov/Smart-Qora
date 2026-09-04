import asyncio

import pytest

from app.services import worker_supervisor as ws


class _QuickService:
    instances = 0

    def __init__(self, _settings):
        _QuickService.instances += 1
        self.stream = None
        self.last_frame_at = None
        self.running = False

    async def run(self):
        self.running = True
        await asyncio.sleep(0.05)
        self.running = False

    def stop(self):
        self.running = False


@pytest.mark.asyncio
async def test_request_restart_revives_a_finished_worker(monkeypatch):
    monkeypatch.setattr(ws, "CountingService", _QuickService)
    _QuickService.instances = 0

    supervisor = ws.WorkerSupervisor(settings=None)
    supervisor.start()
    await asyncio.sleep(0.2)
    assert supervisor.state == "stopped" and _QuickService.instances == 1

    supervisor.request_restart()
    await asyncio.sleep(0.2)
    assert _QuickService.instances == 2 and supervisor.restarts == 1

    await supervisor.stop()
    assert supervisor.state == "stopped"
