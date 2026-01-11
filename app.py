import os
import uuid
import threading
import zipfile
import convertapi
import io
from flask import Flask, request, jsonify, render_template, send_file
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= CONFIG =================
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
ZIP_DIR = "zips"


os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ZIP_DIR, exist_ok=True)


convertapi.api_credentials = "UMWYdoGAZ5VxE1zk7BPqtwCyYHQq2yrs"

app = Flask(__name__)

# ================= JOB STORAGE =================
jobs = {}  
# job_id -> {
#   "files": [{"src","pdf","status","progress"}],
#   "status": "processing|done|error|cancelled",
#   "cancelled": False
# }

executor = ThreadPoolExecutor(max_workers=4)

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")

# ================= CONVERT =================
@app.route("/api/convert", methods=["POST"])
def convert():
    uploaded_files = request.files.getlist("files")
    if not uploaded_files:
        return jsonify(error="No files uploaded"), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"files": [], "status": "processing", "cancelled": False}

    for f in uploaded_files:
        src = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{f.filename}")
        pdf = os.path.join(
            OUTPUT_DIR,
            os.path.splitext(os.path.basename(src))[0] + ".pdf"
        )
        f.save(src)

        jobs[job_id]["files"].append({
            "src": src,
            "pdf": pdf,
            "status": "pending",
            "progress": 0
        })

    threading.Thread(target=process_job, args=(job_id,), daemon=True).start()
    return jsonify(job_id=job_id)

# ================= JOB PROCESS =================
def process_job(job_id):
    job = jobs[job_id]
    futures = []

    for i in range(len(job["files"])):
        futures.append(executor.submit(convert_file, job_id, i))

    for _ in as_completed(futures):
        pass

    if job["cancelled"]:
        job["status"] = "cancelled"
    elif any(f["status"] == "error" for f in job["files"]):
        job["status"] = "error"
    else:
        job["status"] = "done"

def convert_file(job_id, index):
    job = jobs[job_id]
    f = job["files"][index]

    if job["cancelled"]:
        f["status"] = "cancelled"
        return

    try:
        f["status"] = "processing"
        f["progress"] = 10

        result = convertapi.convert("pdf", {"File": f["src"]})
        result.file.save(f["pdf"])

        f["progress"] = 100
        f["status"] = "done"

    except Exception as e:
        f["status"] = "error"
        f["progress"] = 0
        print("Conversion error:", e)

# ================= STATUS (FIXED) =================
@app.route("/api/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify(error="Invalid job"), 404

    files_status = []
    for i, f in enumerate(job["files"]):
        files_status.append({
            "download_url": f"/api/download/{job_id}/{i}" if f["status"] == "done" else None,
            "status": f["status"],
            "progress": f["progress"]
        })

    return jsonify(
        status=job["status"],
        files=files_status
    )

# ================= DOWNLOAD SINGLE =================
@app.route("/api/download/<job_id>/<int:index>")
def download(job_id, index):
    job = jobs.get(job_id)
    if not job or index >= len(job["files"]):
        return "File not found", 404

    pdf = job["files"][index]["pdf"]
    if not os.path.exists(pdf):
        return "File not ready", 404

    return send_file(pdf, as_attachment=True)

# ================= DOWNLOAD ZIP =================
@app.route("/api/download-zip", methods=["POST"])
def download_zip():
    data = request.get_json()
    job_id = data.get("job_id")

    job = jobs.get(job_id)
    if not job:
        return jsonify(error="Invalid job"), 404

    pdfs = [
        f["pdf"]
        for f in job["files"]
        if f["status"] == "done" and os.path.exists(f["pdf"])
    ]

    if len(pdfs) < 2:
        return jsonify(error="Not enough files"), 400

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for pdf in pdfs:
            zf.write(pdf, arcname=os.path.basename(pdf))

    mem.seek(0)
    return send_file(
        mem,
        mimetype="application/zip",
        as_attachment=True,
        download_name="converted_files.zip"
    )

# ================= CANCEL =================
@app.route("/api/cancel/<job_id>", methods=["POST"])
def cancel(job_id):
    job = jobs.get(job_id)
    if not job:
        return "", 404
    job["cancelled"] = True
    return "", 204

# ================= RESET =================
@app.route("/api/reset/<job_id>", methods=["POST"])
def reset_job(job_id):
    job = jobs.pop(job_id, None)
    if not job:
        return "", 204

    for f in job["files"]:
        for p in (f["src"], f["pdf"]):
            if os.path.exists(p):
                os.remove(p)
    return "", 204

@app.route("/api/reset-all", methods=["POST"])
def reset_all():
    # Cancel and remove all jobs
    for job_id in list(jobs.keys()):
        job = jobs.get(job_id)
        if not job:
            continue

        job["cancelled"] = True

        for f in job.get("files", []):
            if not f:
                continue
            for p in (f.get("src"), f.get("pdf")):
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

        jobs.pop(job_id, None)

    # Hard cleanup folders (failsafe)
    for folder in [UPLOAD_DIR, OUTPUT_DIR, ZIP_DIR]:
        if not os.path.exists(folder):
            continue
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    return jsonify({"status": "ok", "message": "All jobs and files reset"}), 200



# ================= MAIN =================
if __name__ == "__main__":
    app.run(port=9090, threaded=True)
