select
    listing_id,
    count(*) as total_reviews,
    sum(case when sentiment = 'positive' then 1 else 0 end) as positive_reviews,
    sum(case when sentiment = 'negative' then 1 else 0 end) as negative_reviews,
    sum(case when sentiment = 'neutral' then 1 else 0 end) as neutral_reviews,
    round(100.0 * sum(case when sentiment = 'positive' then 1 else 0 end) / nullif(count(*), 0), 2) as positive_rate_pct
from {{ ref('stg_reviews') }}
group by listing_id
