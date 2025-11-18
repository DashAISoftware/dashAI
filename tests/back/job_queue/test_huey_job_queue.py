import time  # noqa: F401

import pytest

from DashAI.back.dependencies.job_queues.base_job_queue import JobQueueError
from DashAI.back.dependencies.job_queues.huey_job_queue import HueyJobQueue
from DashAI.back.job.base_job import BaseJob


class DummyJob(BaseJob):
    def run(self) -> None:
        return None

    def set_status_as_delivered(self) -> None:
        return None

    def set_status_as_error(self) -> None:
        return None

    def get_job_name(self) -> str:
        return "Test Job"


def test_empty_queue(test_job_queue: HueyJobQueue):
    assert test_job_queue.is_empty()

    job = DummyJob()
    job_id = test_job_queue.put(job).id
    assert isinstance(job_id, str)

    assert test_job_queue.is_empty()


def test_queue_jobs_list(test_job_queue: HueyJobQueue):
    jobs_list = test_job_queue.to_list()
    assert isinstance(jobs_list, list)
    assert len(jobs_list) == 0

    job_1 = DummyJob()
    job_1_id = test_job_queue.put(job_1).id
    time.sleep(0.05)

    jobs_list = test_job_queue.to_list()
    assert len(jobs_list) == 1
    assert jobs_list[0]["id"] == job_1_id
    assert jobs_list[0]["status"] == "finished"

    job_2 = DummyJob()
    job_2_id = test_job_queue.put(job_2).id
    time.sleep(0.05)

    jobs_list = test_job_queue.to_list()
    assert len(jobs_list) == 2
    assert jobs_list[0]["id"] == job_2_id
    assert jobs_list[1]["id"] == job_1_id


def test_job_status(test_job_queue: HueyJobQueue):
    job = DummyJob()
    job_id = test_job_queue.put(job).id

    status = test_job_queue.status(job_id)
    assert status["status"] == "finished"
    assert status["job_name"] == "Test Job"
    assert status["error"] is None


def test_delete_job(test_job_queue: HueyJobQueue):
    job = DummyJob()
    job_id = test_job_queue.put(job).id

    status = test_job_queue.status(job_id)
    assert status["status"] == "finished"

    result = test_job_queue.delete_from_db(job_id)
    assert result is True

    with pytest.raises(JobQueueError):
        test_job_queue.status(job_id)


def test_delete_all_jobs(test_job_queue: HueyJobQueue):
    jobs = []
    for _ in range(5):
        job = DummyJob()
        job_id = test_job_queue.put(job).id
        jobs.append(job_id)

    jobs_list = test_job_queue.to_list()
    assert len(jobs_list) == 5

    deleted = test_job_queue.delete_all_jobs()
    assert deleted >= 5

    jobs_list = test_job_queue.to_list()
    assert len(jobs_list) == 0


def test_get_nonexistent_job_status(test_job_queue: HueyJobQueue):
    with pytest.raises(JobQueueError):
        test_job_queue.status("nonexistent-job-id")


def test_peek_and_get_nonexistent(test_job_queue: HueyJobQueue):
    job = DummyJob()
    job_id = test_job_queue.put(job).id

    with pytest.raises(JobQueueError):
        test_job_queue.peek(job_id)

    with pytest.raises(JobQueueError):
        test_job_queue.get(job_id)
