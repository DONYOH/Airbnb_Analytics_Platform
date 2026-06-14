select
    listing_id,
    name,
    room_type,
    price_usd,
    host_id
from {{ ref('stg_listings') }}
