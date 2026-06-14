select *
from {{ source('raw_airbnb', 'reviews') }}
