

with channel_stats as (
    select
        channel_name,
        min(message_date)   as first_post_date,
        max(message_date)   as last_post_date,
        count(*)            as total_posts,
        sum(has_image::int) as total_images
    from "medical_warehouse"."public"."stg_telegram_messages"
    group by channel_name
)

select
    row_number() over (order by channel_name)   as channel_key,
    channel_name,
    case channel_name
        when 'CheMed123'         then 'Medical'
        when 'lobelia4cosmetics' then 'Cosmetics'
        when 'tikvahpharma'      then 'Pharmaceutical'
        else 'Other'
    end                                         as channel_type,
    first_post_date,
    last_post_date,
    total_posts,
    total_images
from channel_stats