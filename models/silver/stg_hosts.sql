with source as (
    select * from {{ ref('src_hosts') }}
)

select
    cast(id as bigint) as host_id,
    name as host_name,
    
    -- Transformation des indicateurs 't' (true) / 'f' (false) en vrais types Booléens
    case 
        when is_superhost = 't' then true 
        when is_superhost = 'f' then false 
        else null 
    end as is_superhost,
    
    cast(created_at as timestamp) as created_at_ts,
    cast(updated_at as timestamp) as updated_at_ts

from source