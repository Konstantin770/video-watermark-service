from rq import Queue, Worker
from app.config import redis_connection

queue = Queue("video_tasks", connection=redis_connection)

if __name__ == "__main__":
    print("Worker started. Waiting for tasks...")

    worker = Worker(
        [queue],
        connection=redis_connection
    )

    worker.work()
