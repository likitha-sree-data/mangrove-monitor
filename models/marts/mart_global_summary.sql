
with regional as (
    select * from {{ ref('mart_loss_by_region') }}
),
global_by_year as (
    select
        year,
        sum(country_count)                     as total_countries,
        round(sum(total_area_ha), 0)           as global_area_ha,
        round(sum(total_loss_ha), 0)           as global_loss_ha,
        round(sum(total_gain_ha), 0)           as global_gain_ha,
        round(sum(total_net_change_ha), 0)     as global_net_change_ha,
        round(sum(total_carbon_stock_tonnes),0) as global_carbon_stock_tonnes,
        round(sum(total_flood_protection_usd),0) as global_flood_protection_usd,
        round(
            sum(total_loss_ha) / 365.25 / 24 / 3600
        , 8)                                   as loss_ha_per_second,
        current_timestamp()                    as dbt_updated_at
    from regional
    group by year
)
select * from global_by_year
order by year
