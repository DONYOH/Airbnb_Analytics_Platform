select *
from {{ source('raw_airbnb', 'full_moon_dates') }}
