

with messages as (
    select * from "medical_warehouse"."public"."stg_telegram_messages"
),
channels as (
    select * from "medical_warehouse"."public"."dim_channels"
),
dates as (
    select * from "medical_warehouse"."public"."dim_dates"
)

select
    m.message_id,
    c.channel_key,
    d.date_key,
    m.channel_name,
    m.message_date,
    m.message_text,
    m.text_length,
    m.has_image,
    m.image_path,
    m.views,
    m.forwards,
    m.scraped_at
from messages m
left join channels c on m.channel_name = c.channel_name
left join dates   d on m.message_day   = d.full_date