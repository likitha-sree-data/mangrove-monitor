
with staged as (
    select * from {{ ref('stg_fao_annual_area') }}
    where dq_flag = 'VALID'
),
with_carbon as (
    select
        *,
        round(area_ha * 394, 0)             as carbon_stock_tonnes,
        round(abs(coalesce(net_change_ha,0)) * 394, 0) as carbon_flux_tonnes,
        round(area_ha * 57770, 0)           as flood_protection_usd,
        round(area_ha * 4185, 0)            as ecosystem_services_usd_yr
    from staged
),
latest_year as (
    select country_code, max(year) as max_year
    from staged
    group by country_code
),
final as (
    select
        w.country_code,
        w.country_name,
        w.region,
        w.year,
        w.area_ha,
        w.loss_ha,
        w.gain_ha,
        w.net_change_ha,
        w.net_change_pct,
        w.gross_flux_ha,
        w.carbon_stock_tonnes,
        w.carbon_flux_tonnes,
        w.flood_protection_usd,
        w.ecosystem_services_usd_yr,
        w.primary_driver,
        w.dq_flag,
        case when w.year = l.max_year then true else false end as is_latest_snapshot,
        case
            when w.net_change_pct is null   then 'UNKNOWN'
            when w.net_change_pct >= 0      then 'STABLE_OR_GAINING'
            when w.net_change_pct >= -1     then 'LOW_LOSS'
            when w.net_change_pct >= -3     then 'MODERATE_LOSS'
            when w.net_change_pct >= -5     then 'HIGH_LOSS'
            else                                 'CRITICAL_LOSS'
        end as loss_severity,
        current_timestamp() as dbt_updated_at
    from with_carbon w
    left join latest_year l on w.country_code = l.country_code
)
select * from final
