from pathlib import Path
import sys


API_PATH = Path(__file__).resolve().parents[1] / "api"
if str(API_PATH) not in sys.path:
    sys.path.insert(0, str(API_PATH))


def process_once() -> str:
    from app.db.session import SessionLocal
    from app.queue.service import process_next_fake_job

    with SessionLocal() as db:
        job = process_next_fake_job(db)
        db.commit()
        if job is None:
            return "no_job"
        return job.id


if __name__ == "__main__":
    result = process_once()
    print(f"MercadoIA worker processed: {result}")
