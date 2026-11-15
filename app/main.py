import os
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from rq import Queue
from rq.job import Job
from redis.exceptions import RedisError

from app.config import (
    redis_connection,
    UPLOAD_DIR,
    PROCESSED_DIR
)
from app.tasks import process_video


app = FastAPI(
    title="Video Watermark Service",
    description="Background video processing with Redis and FFmpeg",
    version="1.0.0"
)

queue = Queue("video_tasks", connection=redis_connection)


@app.get("/")
def home():
    return {
        "service": "Video Watermark Service",
        "status": "running"
    }


@app.get("/health")
def health():
    try:
        redis_connection.ping()
        return {"api": "ok", "redis": "ok"}
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Redis is unavailable"
        )


@app.post("/tasks")
async def create_task(video: UploadFile = File(...)):
    if not video.filename:
        raise HTTPException(400, "No filename provided")

    extension = os.path.splitext(video.filename)[1].lower()

    if extension not in [".mp4", ".mov", ".mkv", ".avi", ".webm"]:
        raise HTTPException(400, "Unsupported video format")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    task_id = str(uuid.uuid4())

    input_path = os.path.join(
        UPLOAD_DIR, f"{task_id}{extension}"
    )

    output_path = os.path.join(
        PROCESSED_DIR, f"{task_id}.mp4"
    )

    try:
        with open(input_path, "wb") as file:
            while chunk := await video.read(1024 * 1024):
                file.write(chunk)

        job = queue.enqueue(
            process_video,
            input_path,
            output_path,
            job_timeout=3600,
            result_ttl=86400,
            failure_ttl=86400
        )

        return {
            "task_id": job.id,
            "status": "queued",
            "message": "Video added to processing queue"
        }

    except Exception as error:
        if os.path.exists(input_path):
            os.remove(input_path)

        raise HTTPException(500, str(error))

    finally:
        await video.close()


@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    try:
        job = Job.fetch(task_id, connection=redis_connection)
    except Exception:
        raise HTTPException(404, "Task not found")

    status = job.get_status(refresh=True)

    if status == "finished":
        status = "completed"
    elif status in ["started", "deferred", "scheduled"]:
        status = "processing"

    return {
        "task_id": task_id,
        "status": status,
        "error": job.meta.get("error")
    }


@app.get("/tasks/{task_id}/result")
def get_task_result(task_id: str):
    try:
        job = Job.fetch(task_id, connection=redis_connection)
    except Exception:
        raise HTTPException(404, "Task not found")

    if job.get_status(refresh=True) != "finished":
        raise HTTPException(409, "Video processing is not completed")

    output_path = job.result

    if not output_path or not os.path.exists(output_path):
        raise HTTPException(404, "Processed video not found")

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=f"{task_id}.mp4"
    )
