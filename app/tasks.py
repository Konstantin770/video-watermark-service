import os
import subprocess

from rq import get_current_job
from app.config import PROCESSED_DIR


def process_video(input_path: str, output_path: str):
    job = get_current_job()

    try:
        if job:
            job.meta["status"] = "processing"
            job.save_meta()

        os.makedirs(PROCESSED_DIR, exist_ok=True)

        command = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-vf",
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "text='VIDEO WATERMARK':"
            "fontcolor=white@0.7:"
            "fontsize=32:"
            "x=w-tw-30:"
            "y=h-th-30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]

        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        if job:
            job.meta["status"] = "completed"
            job.save_meta()

        return output_path

    except subprocess.CalledProcessError as error:
        if job:
            job.meta["status"] = "failed"
            job.meta["error"] = error.stderr[-2000:]
            job.save_meta()

        raise

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
