select
    host_id,
    count(*) as total_listings,
    avg(price_usd) as avg_price_usd
from {{ ref('stg_listings') }}
group by host_id
