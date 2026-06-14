with source as (
    select * from {{ ref('src_listings') }}
)

select
    -- Typage explicite des identifiants
    cast(id as bigint) as listing_id,
    listing_url,
    name as listing_name,
    room_type,
    cast(minimum_nights as integer) as min_nights,
    cast(host_id as bigint) as host_id,
    
    -- Nettoyage de la colonne 'price' (on retire le '$' et les virgules pour le transtyper en Décimal)
    cast(regexp_replace(price, '[$,]', '', 'g') as decimal(10,2)) as price_usd,
    
    -- Conversion des chaînes ISO (ex: 2009-06-05T21:34:42Z) en véritables Timestamps
    cast(created_at as timestamp) as created_at_ts,
    cast(updated_at as timestamp) as updated_at_ts

from source