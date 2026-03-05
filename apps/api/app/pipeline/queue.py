import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

_job_queue: asyncio.Queue | None = None
_workers: list[asyncio.Task] = []

# Registry for pipeline runner - set during app startup
_pipeline_runner: Callable | None = None


def set_pipeline_runner(runner: Callable):
    global _pipeline_runner
    _pipeline_runner = runner


async def _worker(worker_id: int):
    logger.info(f"Job worker {worker_id} started")
    while True:
        job_id, video_id = await _job_queue.get()
        logger.info(f"Worker {worker_id} processing job {job_id} for video {video_id}")
        try:
            if _pipeline_runner:
                await _pipeline_runner(job_id, video_id)
            else:
                logger.warning("No pipeline runner registered, skipping job")
        except Exception as e:
            logger.error(f"Worker {worker_id} error on job {job_id}: {e}")
        finally:
            _job_queue.task_done()


async def start_workers(num_workers: int = 2):
    global _job_queue, _workers
    _job_queue = asyncio.Queue()
    for i in range(num_workers):
        task = asyncio.create_task(_worker(i))
        _workers.append(task)
    logger.info(f"Started {num_workers} job workers")


async def stop_workers():
    for task in _workers:
        task.cancel()
    _workers.clear()


async def enqueue_job(job_id: str, video_id: str):
    if _job_queue is None:
        raise RuntimeError("Job queue not initialized")
    await _job_queue.put((job_id, video_id))
    logger.info(f"Enqueued job {job_id} for video {video_id}")
