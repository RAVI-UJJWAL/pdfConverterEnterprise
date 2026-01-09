import os
import convertapi
from app import jobs, OUTPUT_DIR  # import shared jobs dict and output folder

convertapi.api_credentials = "UMWYdoGAZ5VxE1zk7BPqtwCyYHQq2yrs"
convertapi.upload_timeout = 120

def convert_job(job_id, files):
    jobs[job_id]["status"] = "processing"

    results = []
    try:
        for file_path in files:
            result = convertapi.convert("pdf", {"File": file_path})
            pdf_path = os.path.join(
                OUTPUT_DIR,
                os.path.basename(file_path).rsplit(".", 1)[0] + ".pdf"
            )
            result.file.save(pdf_path)
            results.append(pdf_path)

        jobs[job_id]["status"] = "done"
        jobs[job_id]["files"] = results

    except convertapi.exceptions.ApiError as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
