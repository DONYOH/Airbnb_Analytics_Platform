with source as (
    select *
    from {{ ref('src_reviews') }}
),

cleaned as (
    select
        md5(
            coalesce(cast(listing_id as varchar), '') || '|' ||
            coalesce(cast(date as varchar), '') || '|' ||
            coalesce(cast(reviewer_name as varchar), '') || '|' ||
            coalesce(cast(comments as varchar), '')
        ) as review_id,

        cast(listing_id as bigint) as listing_id,
        cast(date as timestamp) as review_date,
        cast(date as date) as review_day,

        nullif(trim(cast(reviewer_name as varchar)), '') as reviewer_name,
        nullif(trim(cast(comments as varchar)), '') as comments,
        lower(nullif(trim(cast(sentiment as varchar)), '')) as sentiment

    from source
    where listing_id is not null
      and date is not null
)

select distinct *
from cleaned
