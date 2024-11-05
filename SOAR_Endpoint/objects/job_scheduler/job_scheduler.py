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

class JobScheduler:
    def __init__(self, max_workers=5):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.jobs = {}
        self.lock = Lock()

    def add_job(self, func, *args, **kwargs):
        job = Job(func, *args, **kwargs)
        with self.lock:
            self.jobs[job.id] = job
            job.future = self.executor.submit(self._run_job, job)
            redis_client.hset(f"job:{job.id}", mapping={"status": job.status, "result": ""})
        return job.id

    def _run_job(self, job):
        try:
            redis_client.hset(f"job:{job.id}", "status", "running")
            result = job.func(*job.args, **job.kwargs)
            redis_client.hset(f"job:{job.id}", mapping={"status": "completed", "result": result})
            return result
        except Exception as e:
            redis_client.hset(f"job:{job.id}", mapping={"status": "failed", "result": str(e)})
            return str(e)

job_scheduler = JobScheduler(max_workers=5)
