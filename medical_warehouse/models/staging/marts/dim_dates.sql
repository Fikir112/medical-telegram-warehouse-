{{ config(materialized='table') }}

with date_spine as (
    select distinct message_day as date_day
    from {{ ref('stg_telegram_messages') }}
)

select
    row_number() over (order by date_day)   as date_key,
    date_day                                as full_date,
    extract(year  from date_day)::int       as year,
    extract(month from date_day)::int       as month,
    extract(day   from date_day)::int       as day,
    extract(week  from date_day)::int       as week_of_year,
    extract(dow   from date_day)::int       as day_of_week,
    to_char(date_day, 'Day')                as day_name,
    to_char(date_day, 'Month')              as month_name,
    case
        when extract(dow from date_day) in (0, 6) then true
        else false
    end                                     as is_weekend
from date_spine