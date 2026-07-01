"""
FastAPI application exposing the medical telegram data warehouse.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Ethiopian Medical Telegram Warehouse API",
    description="API for querying scraped medical Telegram channel data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CONN_STR = (
    f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"dbname={os.getenv('POSTGRES_DB', 'medical_warehouse')} "
    f"user={os.getenv('POSTGRES_USER', 'postgres')} "
    f"password={os.getenv('POSTGRES_PASSWORD')} "
    f"client_encoding=utf8"
)


def get_conn():
    return psycopg.connect(CONN_STR)


@app.get("/")
def root():
    return {"message": "Ethiopian Medical Telegram Warehouse API", "status": "running"}


@app.get("/channels")
def get_channels():
    """List all channels with their stats."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT channel_name, channel_type, total_posts, total_images,
                       first_post_date, last_post_date
                FROM dim_channels
                ORDER BY total_posts DESC
            """)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]


@app.get("/messages/top")
def get_top_messages(limit: int = Query(default=10, le=100)):
    """Get most recent messages across all channels."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT message_id, channel_name, message_date,
                       message_text, has_image, views, forwards
                FROM fct_messages
                ORDER BY message_date DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]


@app.get("/messages/search")
def search_messages(q: str = Query(..., description="Search term")):
    """Search messages by keyword."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT message_id, channel_name, message_date, message_text
                FROM fct_messages
                WHERE message_text ILIKE %s
                ORDER BY message_date DESC
                LIMIT 50
            """, (f"%{q}%",))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]


@app.get("/messages/channel/{channel_name}")
def get_messages_by_channel(channel_name: str, limit: int = Query(default=20, le=100)):
    """Get messages for a specific channel."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT message_id, channel_name, message_date,
                       message_text, has_image, views, forwards
                FROM fct_messages
                WHERE channel_name = %s
                ORDER BY message_date DESC
                LIMIT %s
            """, (channel_name, limit))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]


@app.get("/detections/top")
def get_top_detections(limit: int = Query(default=10, le=100)):
    """Get most frequently detected objects across all images."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT detected_class, COUNT(*) as detection_count,
                       ROUND(AVG(confidence_score)::numeric, 3) as avg_confidence
                FROM image_detections
                WHERE detected_class != 'none'
                GROUP BY detected_class
                ORDER BY detection_count DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]


@app.get("/stats")
def get_stats():
    """Overall warehouse statistics."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fct_messages")
            total_messages = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM fct_messages WHERE has_image = true")
            total_with_images = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM image_detections WHERE detected_class != 'none'")
            total_detections = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT channel_name) FROM fct_messages")
            total_channels = cur.fetchone()[0]

            return {
                "total_messages": total_messages,
                "total_with_images": total_with_images,
                "total_detections": total_detections,
                "total_channels": total_channels,
            }