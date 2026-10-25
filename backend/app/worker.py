import logging
import time

from prometheus_client import start_http_server
from sqlalchemy import delete

from .config import settings
from .db import SessionLocal, now
from .models import ConsoleSession, RateBucket
from .replay import run_one
from .usage import expire_reservations


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    start_http_server(settings.worker_metrics_port)
    while True:
        try:
            with SessionLocal() as db:
                processed = run_one(db)
            with SessionLocal() as db:
                expire_reservations(db)
                db.execute(delete(ConsoleSession).where(ConsoleSession.expires_at < now()))
                db.execute(
                    delete(RateBucket).where(
                        RateBucket.minute < now().replace(hour=0, minute=0, second=0, microsecond=0)
                    )
                )
                db.commit()
            if not processed:
                time.sleep(1)
        except Exception:
            logging.error('{"event":"worker_failed","message":"Job transaction rolled back; retrying"}')
            time.sleep(5)


if __name__ == "__main__":
    main()
