# jobs/job_queue.py

import concurrent.futures
import uuid
from redis import Redis
from threading import Lock
from django.conf import settings

redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, decode_responses=True)

class Job:
    def __init__(self, func, *args, **kwargs):
        self.id = str(uuid.uuid4())
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = "queued"
        self.future = None

class JobQueue:
    def __init__(self, max_workers=5):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.jobs = {}
        self.lock = Lock()

    def get_status(self, job_id):
        job_data = redis_client.hgetall(f"job:{job_id}")
        if job_data:
            return job_data
        return None

    def cancel_job(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.future and job.future.cancel():
                redis_client.hset(f"job:{job_id}", "status", "canceled")
                return True
            return False

    def remove_job(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.future and job.future.cancel():
                redis_client.delete(f"job:{job_id}")
                del self.jobs[job_id]
                return True
            return False

job_queue = JobQueue(max_workers=5)
