from django.conf import settings
from threading import Lock
import concurrent.futures
from redis import Redis
import uuid
import time
import traceback
import requests


redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
)


class Job:
    def __init__(self, func, name: str = "", *args, **kwargs):
        self.id = f"{name}_{str(uuid.uuid4())}"
        self.created_at = time.time()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = "queued"
        self.future = None


class JobScheduler:
    def __init__(self, max_workers: int = 5):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.jobs = {}
        self.lock = Lock()

    def get_jobs(self) -> dict:
        output = {"jobs": []}
        for key in redis_client.scan_iter("job:*"):
            job_id = key.split(":")[1]
            job_status = self.get_status(job_id)
            inner_dict = {"id": job_id}
            for status_keys in job_status.keys():
                inner_dict[status_keys] = job_status[status_keys]

            output["jobs"].append(inner_dict)
        
        return output
    
    def find_jobs(self, name) -> dict:
        output = {"jobs": []}
        for key in redis_client.scan_iter(f"job:{name}_*"):
            job_id = key.split(":")[1]
            job_status = self.get_status(job_id)
            inner_dict = {"id": job_id}
            for status_keys in job_status.keys():
                inner_dict[status_keys] = job_status[status_keys]

            output["jobs"].append(inner_dict)
        
        return output

    def add_job(self, func, name: str = "", *args, **kwargs) -> str:
        name = name.replace(" ", "_")
        job = Job(func, name, *args, **kwargs)
        with self.lock:
            self.jobs[job.id] = job
            redis_client.hset(
                f"job:{job.id}", mapping={"status": job.status, "createdAt": job.created_at, "result": ""}
            )
            job.future = self.executor.submit(self._run_job, job)
        return job.id

    def _run_job(self, job) -> str:
        try:
            redis_client.hset(f"job:{job.id}", mapping={"status": "running", "createdAt": job.created_at})
            result = job.func(*job.args, **job.kwargs)
            time_finished = time.time()

            output = ""
            if type(result) == requests.models.Response:
                json_data = result.json()
                if "message" in json_data.keys():
                    output = json_data["message"]
                elif "error" in json_data.keys():
                    output = json_data["error"]

            elif type(result) == dict:
                if "message" in result.keys():
                    output = result["message"]
                elif "error" in result.keys():
                    output = result["error"]

            redis_client.hset(
                f"job:{job.id}", mapping={
                    "status": "completed",
                    "createdAt": job.created_at,
                    "finishedAt": time_finished,
                    "elapsedTime": time_finished - job.created_at,
                    "result": output
                    }
            )
            return output
        except Exception as e:
            print(traceback.format_exc())
            time_finished = time.time()
            redis_client.hset(
                f"job:{job.id}", mapping={
                    "status": "failed",
                    "createdAt": job.created_at,
                    "finishedAt": time_finished,
                    "elapsedTime": time_finished - job.created_at,
                    "result": traceback.format_exc()
                    }
            )
            return str(e)

    def get_status(self, job_id: str) -> dict:
        job_data = redis_client.hgetall(f"job:{job_id}")
        if job_data:
            return job_data
        return None

    def cancel_job(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.future and job.future.cancel():
                time_finished = time.time()
                redis_client.hset(
                    f"job:{job.id}", mapping={
                        "status": "canceled",
                        "createdAt": job.created_at,
                        "finishedAt": time_finished,
                        "elapsedTime": time_finished - job.created_at,
                        "result": str(e)
                        }
                )
                return True
        return False

    def remove_job(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.future and not job.future.done():
                if job.future.cancel():
                    del self.jobs[job_id]
                    redis_client.delete(f"job:{job_id}")
                    return True
                return False
            else:
                redis_client.delete(f"job:{job_id}")
            
        return False


job_scheduler = JobScheduler(max_workers=settings.MAX_WORKERS)
