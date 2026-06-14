with reviews as (
    select *
    from {{ ref('stg_reviews') }}
),

full_moon as (
    select *
    from {{ ref('stg_full_moon_dates') }}
)

select
    r.review_id,
    r.listing_id,
    r.review_date,
    r.review_day,
    r.reviewer_name,
    r.comments,
    r.sentiment,

    case
        when f.full_moon_date is not null then true
        else false
    end as is_full_moon

from reviews r
left join full_moon f
    on r.review_day = f.full_moon_date
