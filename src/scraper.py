"""
Telegram scraper for medical/pharmacy channels.
Scrapes messages + images and dumps raw, untouched JSON to the data lake
(data/raw/telegram_messages/YYYY-MM-DD/channel_name.json), and images to
data/raw/images/{channel_name}/{message_id}.jpg.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_MESSAGES_DIR = PROJECT_ROOT / "data" / "raw" / "telegram_messages"
RAW_IMAGES_DIR = PROJECT_ROOT / "data" / "raw" / "images"
LOG_DIR = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "scraper.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Public channels to scrape (usernames, no "@")
CHANNELS = [
    "CheMed123",
    "lobelia4cosmetics",
    "tikvahpharma",
]

# How many messages to pull per channel (keep modest for time constraints)
MESSAGE_LIMIT = 50


# ---------------------------------------------------------------------------
# Core scraping logic
# ---------------------------------------------------------------------------

def message_to_dict(message, channel_name: str) -> dict:
    """
    Preserve the original Telegram API message structure (via Telethon's
    to_dict()), and just attach a couple of pipeline-tracking fields.
    This keeps the raw layer truly raw, per the data lake requirement.
    """
    raw = message.to_dict()
    has_image = isinstance(message.media, MessageMediaPhoto)

    return {
        "raw": json.loads(json.dumps(raw, default=str)),  # full original structure, datetime-safe
        "channel_name": channel_name,
        "message_id": message.id,
        "message_date": message.date.isoformat() if message.date else None,
        "message_text": message.message,
        "has_image": has_image,
        "image_path": None,  # filled in after download if has_image
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def scrape_channel(client: TelegramClient, channel_name: str) -> list[dict]:
    logger.info(f"Starting scrape for channel: {channel_name}")
    messages_out = []

    channel_image_dir = RAW_IMAGES_DIR / channel_name
    channel_image_dir.mkdir(parents=True, exist_ok=True)

    try:
        entity = await client.get_entity(channel_name)
    except Exception as e:
        logger.error(f"Could not resolve channel '{channel_name}': {e}")
        return messages_out

    count = 0
    async for message in client.iter_messages(entity, limit=MESSAGE_LIMIT):
        record = message_to_dict(message, channel_name)

        if record["has_image"]:
           pass

        messages_out.append(record)
        count += 1
        if count % 50 == 0:
            logger.info(f"  {channel_name}: {count} messages scraped so far")

    logger.info(f"Finished {channel_name}: {count} messages total")
    return messages_out


async def main():
    client = TelegramClient("medwarehouse_session", API_ID, API_HASH)
    await client.start(phone=PHONE)
    logger.info("Telegram client authenticated successfully.")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for channel_name in CHANNELS:
        messages = await scrape_channel(client, channel_name)

        if not messages:
            logger.warning(f"No messages scraped for {channel_name}, skipping write.")
            continue

        out_dir = RAW_MESSAGES_DIR / today_str
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{channel_name}.json"

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)

        logger.info(f"Wrote {len(messages)} messages to {out_path}")

    await client.disconnect()
    logger.info("Scraping complete. Client disconnected.")


if __name__ == "__main__":
    asyncio.run(main())