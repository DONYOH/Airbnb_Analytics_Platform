select
    cast(full_moon_date as date) as full_moon_date
from {{ ref('src_full_moon_dates') }}
where full_moon_date is not null
