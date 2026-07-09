
with source as (
    select * from {{ source('raw', 'FAO_ANNUAL_AREA') }}
),
cleaned as (
    select
        load_id,
        country_code,
        upper(trim(country_name))   as country_name,
        upper(trim(region))         as region,
        year::integer               as year,
        area_ha::float              as area_ha,
        loss_ha::float              as loss_ha,
        gain_ha::float              as gain_ha,
        area_change_ha::float       as net_change_ha,
        case
            when area_ha > 0 and area_change_ha is not null
            then round((area_change_ha / area_ha) * 100, 4)
            else null
        end                         as net_change_pct,
        case
            when loss_ha is not null and gain_ha is not null
            then loss_ha + gain_ha
            else null
        end                         as gross_flux_ha,
        primary_driver,
        source_file,
        loaded_at,
        case
            when area_ha is null then 'MISSING_AREA'
            when year < 1990     then 'YEAR_OUT_OF_RANGE'
            when area_ha < 0     then 'NEGATIVE_AREA'
            else 'VALID'
        end                         as dq_flag
    from source
    where source_file is not null
)
select * from cleaned
