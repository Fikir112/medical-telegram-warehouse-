-- Custom test: no message should have a date in the future
SELECT message_id
FROM {{ ref('fct_messages') }}
WHERE message_date > NOW()