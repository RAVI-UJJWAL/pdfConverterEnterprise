import os

MAX_FILE_MB = 10
MAX_FILES_PER_JOB = 5

ALLOWED_EXTENSIONS = {
    "doc", "docx", "xls", "xlsx",
    "ppt", "pptx", "png", "jpg",
    "jpeg", "pdf"
}

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ConvertAPI
CONVERTAPI_SECRET = "UMWYdoGAZ5VxE1zk7BPqtwCyYHQq2yrs"
CONVERTAPI_TIMEOUT = 120
