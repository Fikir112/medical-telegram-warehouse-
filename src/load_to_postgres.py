"""
Loads scraped JSON files from data/raw/telegram_messages/
into PostgreSQL table: public.raw_telegram_messages
"""

import json
import logging
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_MESSAGES_DIR = PROJECT_ROOT / "data" / "raw" / "telegram_messages"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "loader.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

CONN_STR = (
    f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"dbname={os.getenv('POSTGRES_DB', 'medical_warehouse')} "
    f"user={os.getenv('POSTGRES_USER', 'postgres')} "
    f"password={os.getenv('POSTGRES_PASSWORD')} "
    f"client_encoding=utf8"
)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS raw_telegram_messages (
    id              SERIAL PRIMARY KEY,
    message_id      BIGINT,
    channel_name    VARCHAR(100),
    message_date    TIMESTAMPTZ,
    message_text    TEXT,
    has_image       BOOLEAN,
    image_path      TEXT,
    scraped_at      TIMESTAMPTZ,
    raw_data        JSONB
);
"""

INSERT_SQL = """
INSERT INTO raw_telegram_messages
    (message_id, channel_name, message_date, message_text,
     has_image, image_path, scraped_at, raw_data)
VALUES
    (%(message_id)s, %(channel_name)s, %(message_date)s, %(message_text)s,
     %(has_image)s, %(image_path)s, %(scraped_at)s, %(raw_data)s)
ON CONFLICT DO NOTHING;
"""


def load_json_files():
    files = list(RAW_MESSAGES_DIR.rglob("*.json"))
    if not files:
        logger.warning("No JSON files found in data/raw/telegram_messages/")
        return

    with psycopg.connect(CONN_STR) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            conn.commit()
            logger.info("Table raw_telegram_messages ready.")

            total_inserted = 0
            for json_file in files:
                logger.info(f"Loading {json_file}")
                with open(json_file, encoding="utf-8") as f:
                    records = json.load(f)

                rows = []
                for r in records:
                    rows.append({
                        "message_id":   r.get("message_id"),
                        "channel_name": r.get("channel_name"),
                        "message_date": r.get("message_date"),
                        "message_text": r.get("message_text"),
                        "has_image":    r.get("has_image", False),
                        "image_path":   r.get("image_path"),
                        "scraped_at":   r.get("scraped_at"),
                        "raw_data":     json.dumps(r.get("raw", {})),
                    })

                cur.executemany(INSERT_SQL, rows)
                conn.commit()
                total_inserted += len(rows)
                logger.info(f"  Inserted {len(rows)} rows from {json_file.name}")

    logger.info(f"Load complete. Total rows inserted: {total_inserted}")


if __name__ == "__main__":
    load_json_files()