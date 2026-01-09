from threading import Lock

jobs = {}
jobs_lock = Lock()

def create_job(job_id):
    with jobs_lock:
        jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "files": [],
            "error": None
        }

def update_job(job_id, **kwargs):
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(kwargs)

def get_job(job_id):
    with jobs_lock:
        return jobs.get(job_id)

def delete_job(job_id):
    with jobs_lock:
        jobs.pop(job_id, None)
