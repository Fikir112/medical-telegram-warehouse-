
  create view "medical_warehouse"."public"."stg_telegram_messages__dbt_tmp"
    
    
  as (
    

with raw as (
    select * from "medical_warehouse"."public"."raw_telegram_messages"
)

select
    message_id::bigint                          as message_id,
    channel_name::varchar(100)                  as channel_name,
    message_date::timestamp with time zone      as message_date,
    message_text::text                          as message_text,
    has_image::boolean                          as has_image,
    image_path::text                            as image_path,
    scraped_at::timestamp with time zone        as scraped_at,
    date_trunc('day', message_date::timestamp)  as message_day,
    extract(hour from message_date::timestamp)  as message_hour,
    length(message_text)                        as text_length,
    (raw_data->>'views')::int                   as views,
    (raw_data->>'forwards')::int                as forwards
from raw
where message_id is not null
  );