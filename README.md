# medical-telegram-warehouse-
# Ethiopian Medical Telegram Data Warehouse

A data engineering pipeline that scrapes public Telegram channels selling medical and pharmaceutical products in Ethiopia, stores raw data in a structured data lake, and transforms it into a star schema data warehouse using dbt.

Built for 10 Academy KAIM Week 8.

---

## Project Structure
medical-telegram-warehouse/

├── data/

│   └── raw/

│       ├── telegram_messages/   # Partitioned JSON data lake (YYYY-MM-DD/channel.json)

│       └── images/              # Downloaded channel images

├── logs/                        # Scraper and loader logs

├── src/

│   ├── scraper.py               # Telegram scraper (Telethon)

│   └── load_to_postgres.py      # JSON → PostgreSQL loader

├── medical_warehouse/           # dbt project

│   ├── dbt_project.yml

│   ├── profiles.yml

│   └── models/

│       ├── staging/

│       │   ├── stg_telegram_messages.sql

│       │   └── sources.yml

│       └── marts/

│           ├── dim_channels.sql

│           ├── dim_dates.sql

│           ├── fct_messages.sql

│           └── schema.yml

├── .env                         # Credentials (not committed)

├── requirements.txt

└── interim_report.pdf
---

## Channels Scraped

| Channel | Username | Type |
|---|---|---|
| CheMed | CheMed123 | Medical Products |
| Lobelia Cosmetics | lobelia4cosmetics | Cosmetics & Health |
| Tikvah Pharma | tikvahpharma | Pharmaceuticals |

---

## Setup

**1. Clone the repo and install dependencies:**
```bash
pip install -r requirements.txt
```

**2. Create a `.env` file in the root:**


**3. Run the scraper:**
```bash
python src/scraper.py
```

**4. Start PostgreSQL and create the database:**
```bash
psql -U postgres -c "CREATE DATABASE medical_warehouse ENCODING 'UTF8' TEMPLATE template0;"
```

**5. Load raw data into PostgreSQL:**
```bash
python src/load_to_postgres.py
```

**6. Run dbt transformations:**
```bash
cd medical_warehouse
dbt run --profiles-dir .
dbt test --profiles-dir .
```

---

## Star Schema

The warehouse implements a star schema with:
- **fct_messages** — central fact table (one row per message)
- **dim_channels** — channel dimension with type and aggregate stats
- **dim_dates** — date dimension derived from message timestamps

---

## Tech Stack

- Python 3.14
- Telethon (Telegram API)
- PostgreSQL + psycopg v3
- dbt-postgres
- pandas