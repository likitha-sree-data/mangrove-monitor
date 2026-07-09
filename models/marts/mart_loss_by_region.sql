
with country_data as (
    select * from {{ ref('mart_loss_by_country') }}
),
regional as (
    select
        region,
        year,
        count(distinct country_code)        as country_count,
        round(sum(area_ha), 0)              as total_area_ha,
        round(sum(loss_ha), 0)              as total_loss_ha,
        round(sum(gain_ha), 0)              as total_gain_ha,
        round(sum(net_change_ha), 0)        as total_net_change_ha,
        round(sum(carbon_stock_tonnes), 0)  as total_carbon_stock_tonnes,
        round(sum(flood_protection_usd), 0) as total_flood_protection_usd,
        round(
            sum(net_change_ha) / nullif(sum(area_ha), 0) * 100
        , 4)                                as avg_net_change_pct,
        mode(primary_driver)                as dominant_driver,
        current_timestamp()                 as dbt_updated_at
    from country_data
    where dq_flag = 'VALID'
    group by region, year
)
select * from regional
order by region, year
