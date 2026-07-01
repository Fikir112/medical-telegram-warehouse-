"""
YOLO image enrichment for medical Telegram channel images.
Runs YOLOv8 object detection on downloaded images and stores
results in PostgreSQL table: public.image_detections
"""

import json
import logging
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from ultralytics import YOLO

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_IMAGES_DIR = PROJECT_ROOT / "data" / "raw" / "images"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "yolo.log", encoding="utf-8"),
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
CREATE TABLE IF NOT EXISTS image_detections (
    id                  SERIAL PRIMARY KEY,
    message_id          BIGINT,
    channel_name        VARCHAR(100),
    image_path          TEXT,
    detected_class      VARCHAR(100),
    confidence_score    FLOAT,
    image_category      VARCHAR(50),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
"""

INSERT_SQL = """
INSERT INTO image_detections
    (message_id, channel_name, image_path, detected_class, confidence_score, image_category)
VALUES
    (%(message_id)s, %(channel_name)s, %(image_path)s,
     %(detected_class)s, %(confidence_score)s, %(image_category)s)
ON CONFLICT DO NOTHING;
"""


def classify_image(detected_classes: list[str]) -> str:
    """
    Assign a high-level image category based on YOLO detected classes.
    - 'person' detected → promotional (human holding/showing product)
    - No person → product_display
    - Nothing detected → unclear
    """
    if not detected_classes:
        return "unclear"
    if "person" in detected_classes:
        return "promotional"
    return "product_display"


def run_yolo_on_images():
    image_files = list(RAW_IMAGES_DIR.rglob("*.jpg"))
    if not image_files:
        logger.warning("No images found in data/raw/images/")
        return

    logger.info(f"Found {len(image_files)} images. Loading YOLOv8 model...")
    model = YOLO("yolov8n.pt")  # downloads ~6MB nano model automatically
    logger.info("Model loaded.")

    rows = []
    for image_path in image_files:
        # Extract channel_name and message_id from path structure
        # data/raw/images/{channel_name}/{message_id}.jpg
        channel_name = image_path.parent.name
        message_id_str = image_path.stem
        try:
            message_id = int(message_id_str)
        except ValueError:
            message_id = None

        try:
            results = model(str(image_path), verbose=False)
            detected_classes = []
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    class_name = model.names[class_id]
                    confidence = float(box.conf[0])
                    detected_classes.append(class_name)
                    rows.append({
                        "message_id": message_id,
                        "channel_name": channel_name,
                        "image_path": str(image_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "detected_class": class_name,
                        "confidence_score": round(confidence, 4),
                        "image_category": classify_image(detected_classes),
                    })

            # If nothing detected, still record the image
            if not detected_classes:
                rows.append({
                    "message_id": message_id,
                    "channel_name": channel_name,
                    "image_path": str(image_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "detected_class": "none",
                    "confidence_score": 0.0,
                    "image_category": "unclear",
                })

            logger.info(f"  {channel_name}/{image_path.name}: {detected_classes or ['none']}")

        except Exception as e:
            logger.warning(f"Failed to process {image_path}: {e}")

    logger.info(f"Detection complete. Inserting {len(rows)} rows into PostgreSQL...")

    with psycopg.connect(CONN_STR) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            conn.commit()
            cur.executemany(INSERT_SQL, rows)
            conn.commit()

    logger.info("YOLO enrichment complete.")


if __name__ == "__main__":
    run_yolo_on_images()