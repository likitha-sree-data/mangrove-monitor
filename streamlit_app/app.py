import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import time


st.set_page_config(page_title="Global Mangrove Loss Monitor", page_icon="🌿", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif!important;background:#f8f7f4!important}
.block-container{padding-top:1rem!important;max-width:1080px!important}
div[data-testid="metric-container"]{background:#fff;border:1px solid #d4d1c8;padding:16px 18px}
div[data-testid="metric-container"] label{font-family:'IBM Plex Mono',monospace!important;font-size:.56rem!important;letter-spacing:.14em!important;text-transform:uppercase!important;color:#6a6760!important}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{font-family:'IBM Plex Mono',monospace!important;font-size:1.6rem!important;font-weight:400!important;color:#b83220!important}
div[data-testid="metric-container"] [data-testid="stMetricDelta"]{font-family:'IBM Plex Mono',monospace!important;font-size:.55rem!important;color:#a09d98!important}
h2{font-family:'IBM Plex Sans',sans-serif!important;font-weight:300!important;letter-spacing:-.02em!important}
.kicker{font-family:'IBM Plex Mono',monospace;font-size:.56rem;letter-spacing:.16em;text-transform:uppercase;color:#6a6760}
.rule{font-family:'IBM Plex Mono',monospace;font-size:.56rem;letter-spacing:.16em;text-transform:uppercase;color:#6a6760;border-bottom:1px solid #16150f;padding-bottom:5px;margin:24px 0 14px}
.footer{font-family:'IBM Plex Mono',monospace;font-size:.54rem;color:#a09d98;line-height:2;border-top:1px solid #d4d1c8;padding-top:14px;margin-top:36px}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    return snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        role=st.secrets["snowflake"]["role"]
    )

@st.cache_data(ttl=3600)
def load_global():
    return pd.read_sql("""
        SELECT YEAR, GLOBAL_AREA_HA, GLOBAL_LOSS_HA,
               GLOBAL_NET_CHANGE_HA, LOSS_HA_PER_SECOND
        FROM MANGROVE_MONITOR.STAGING_MART.MART_GLOBAL_SUMMARY
        WHERE GLOBAL_LOSS_HA IS NOT NULL ORDER BY YEAR
    """, get_conn())

@st.cache_data(ttl=3600)
def load_countries():
    return pd.read_sql("""
        SELECT COUNTRY_CODE, COUNTRY_NAME, REGION, YEAR, AREA_HA,
               NET_CHANGE_HA, NET_CHANGE_PCT, LOSS_SEVERITY,
               CARBON_STOCK_TONNES, FLOOD_PROTECTION_USD, PRIMARY_DRIVER
        FROM MANGROVE_MONITOR.STAGING_MART.MART_LOSS_BY_COUNTRY
        WHERE IS_LATEST_SNAPSHOT = TRUE ORDER BY AREA_HA DESC
    """, get_conn())

@st.cache_data(ttl=3600)
def load_regional():
    return pd.read_sql("""
        SELECT REGION, YEAR, TOTAL_AREA_HA, TOTAL_LOSS_HA,
               AVG_NET_CHANGE_PCT, DOMINANT_DRIVER
        FROM MANGROVE_MONITOR.STAGING_MART.MART_LOSS_BY_REGION
        ORDER BY YEAR, TOTAL_AREA_HA DESC
    """, get_conn())

def live_counts(rate):
    T0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    secs = (datetime.now(timezone.utc) - T0).total_seconds()
    ha = secs * rate
    return dict(ha=ha, carbon=ha*394, flood=ha*57770, fish=ha*54054, coast=ha*10)

st.markdown('<p class="kicker">Global Mangrove Loss Monitor · v2.1 · FAO 2023 · GMA 2024 · UC Santa Cruz 2024 · IUCN 2024</p>', unsafe_allow_html=True)
st.markdown('<hr style="border:none;border-top:2px solid #16150f;margin:4px 0 10px">', unsafe_allow_html=True)
st.markdown("## Global mangrove forest loss — **real-time estimates**")
st.markdown('<hr style="border:none;border-top:1px solid #d4d1c8;margin:0 0 16px">', unsafe_allow_html=True)

try:
    gdf = load_global()
    cdf = load_countries()
    rdf = load_regional()
    rate = float(gdf.iloc[-1]["LOSS_HA_PER_SECOND"])
    c = live_counts(rate)

    st.markdown(f'<p class="rule">Cumulative estimates · year to date 2025 · Rate: {rate:.6f} ha/sec · FAO 2023</p>', unsafe_allow_html=True)
    col1,col2,col3,col4,col5 = st.columns(5)
    col1.metric("Hectares lost",        f"{c['ha']:,.0f}",            "Since 1 Jan 2025",             delta_color="off")
    col2.metric("Carbon storage lost",  f"{c['carbon']/1e6:,.2f}M t", "394 t C/ha · GMA 2024",       delta_color="off")
    col3.metric("Flood protection",     f"${c['flood']/1e9:,.3f}B",   "$57,770/ha · World Bank 2024", delta_color="off")
    col4.metric("Marine juveniles",     f"{c['fish']/1e6:,.1f}M",     "54,054/ha · GMA 2024",         delta_color="off")
    col5.metric("Coastline unshielded", f"{c['coast']/1000:,.1f} km", "10 m/ha · IUCN 2024",         delta_color="off")

    st.markdown('<p class="rule">Mangrove loss intensity by country · net change % · most recent year</p>', unsafe_allow_html=True)
    map_df = cdf[cdf["NET_CHANGE_PCT"].notna()].copy()
    fig_map = px.choropleth(
        map_df, locations="COUNTRY_CODE", color="NET_CHANGE_PCT",
        hover_name="COUNTRY_NAME",
        hover_data={"AREA_HA":":.0f","NET_CHANGE_HA":":.0f","LOSS_SEVERITY":True,"PRIMARY_DRIVER":True,"COUNTRY_CODE":False},
        color_continuous_scale=["#b83220","#f0ede8","#1a6b3c"],
        color_continuous_midpoint=0, range_color=[-6,6],
        labels={"NET_CHANGE_PCT":"Net chg %"}
    )
    fig_map.update_layout(
        geo=dict(showframe=False,showcoastlines=True,coastlinecolor="#d4d1c8",
                 showland=True,landcolor="#f8f7f4",showocean=True,oceancolor="#eef2f5",
                 bgcolor="#f8f7f4",projection_type="natural earth"),
        paper_bgcolor="#f8f7f4",
        font=dict(family="IBM Plex Mono",size=10,color="#6a6760"),
        height=340, margin=dict(l=0,r=0,t=0,b=0),
        coloraxis_colorbar=dict(title="Net chg %",thickness=10,len=0.7,tickfont=dict(size=9))
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption("Red = net loss · Green = net gain · Grey = no data in this dataset · Hover for country detail")

    st.markdown('<p class="rule">Annual loss trend · 2000-2020 · complete global data years only</p>', unsafe_allow_html=True)
    trend_df = gdf[gdf["YEAR"].isin([2000,2010,2020])].copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=trend_df["YEAR"],
        y=trend_df["GLOBAL_LOSS_HA"],
        marker_color="#b83220",
        opacity=0.8,
        hovertemplate="Year: %{x}<br>Loss: %{y:,.0f} ha<extra></extra>"
    ))
    fig.add_annotation(
        x=2000,
        y=float(trend_df[trend_df["YEAR"]==2000]["GLOBAL_LOSS_HA"].values[0]),
        text="46,700 ha/yr<br>1990-2000 avg",
        showarrow=True, arrowhead=2, arrowcolor="#6a6760",
        font=dict(size=9, family="IBM Plex Mono", color="#6a6760"),
        ax=0, ay=-45
    )
    fig.add_annotation(
        x=2020,
        y=float(trend_df[trend_df["YEAR"]==2020]["GLOBAL_LOSS_HA"].values[0]),
        text="21,200 ha/yr<br>2010-2020 · -54%",
        showarrow=True, arrowhead=2, arrowcolor="#1a6b3c",
        font=dict(size=9, family="IBM Plex Mono", color="#1a6b3c"),
        ax=50, ay=-45
    )
    fig.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#f8f7f4",
        font=dict(family="IBM Plex Mono",size=11,color="#6a6760"),
        height=280,
        margin=dict(l=0,r=0,t=16,b=0),
        showlegend=False,
        xaxis=dict(title="Year",showgrid=False,linecolor="#d4d1c8",tickvals=[2000,2010,2020]),
        yaxis=dict(title="Hectares lost",showgrid=True,gridcolor="#e8e6e0",tickformat=",d")
    )
    st.plotly_chart(fig, use_container_width=True)


    st.markdown('<p class="rule">Regional breakdown · 2020</p>', unsafe_allow_html=True)
    r2020 = rdf[rdf["YEAR"]==2020].copy()
    left, right = st.columns([3,2])
    with left:
        fig2 = px.bar(
            r2020.sort_values("TOTAL_AREA_HA"),
            x="TOTAL_AREA_HA", y="REGION", orientation="h",
            color="AVG_NET_CHANGE_PCT",
            color_continuous_scale=["#b83220","#f0ede8","#1a6b3c"],
            color_continuous_midpoint=0,
            labels={"TOTAL_AREA_HA":"Area (ha)","REGION":"","AVG_NET_CHANGE_PCT":"Net chg %"}
        )
        fig2.update_layout(
            plot_bgcolor="#ffffff", paper_bgcolor="#f8f7f4",
            font=dict(family="IBM Plex Mono",size=10,color="#6a6760"),
            height=260, margin=dict(l=0,r=0,t=8,b=0),
            xaxis=dict(tickformat=",d",showgrid=True,gridcolor="#e8e6e0"),
            coloraxis_colorbar=dict(thickness=10,len=0.7,tickfont=dict(size=9))
        )
        st.plotly_chart(fig2, use_container_width=True)
    with right:
        disp_r = r2020[["REGION","TOTAL_AREA_HA","TOTAL_LOSS_HA","AVG_NET_CHANGE_PCT","DOMINANT_DRIVER"]].copy()
        disp_r.columns = ["Region","Area (ha)","Loss (ha)","Chg %","Driver"]
        disp_r["Area (ha)"] = disp_r["Area (ha)"].apply(lambda x: f"{x:,.0f}")
        disp_r["Loss (ha)"] = disp_r["Loss (ha)"].apply(lambda x: f"{x:,.0f}")
        disp_r["Chg %"]     = disp_r["Chg %"].apply(lambda x: f"{x:.3f}%")
        st.dataframe(disp_r, use_container_width=True, height=260, hide_index=True)
    st.markdown('<p class="rule">Country snapshot · most recent year per country</p>', unsafe_allow_html=True)
    fc1,fc2,_ = st.columns([1,1,3])
    with fc1:
        regions = ["All regions"] + sorted(cdf["REGION"].unique().tolist())
        sel_region = st.selectbox("Region", regions, label_visibility="collapsed")
    with fc2:
        severities = ["All severity"] + sorted(cdf["LOSS_SEVERITY"].unique().tolist())
        sel_sev = st.selectbox("Severity", severities, label_visibility="collapsed")

    filtered = cdf.copy()
    if sel_region != "All regions":
        filtered = filtered[filtered["REGION"]==sel_region]
    if sel_sev != "All severity":
        filtered = filtered[filtered["LOSS_SEVERITY"]==sel_sev]

    disp2 = filtered[["COUNTRY_NAME","REGION","YEAR","AREA_HA","NET_CHANGE_HA","LOSS_SEVERITY","CARBON_STOCK_TONNES","PRIMARY_DRIVER"]].copy()
    disp2.columns = ["Country","Region","Year","Area (ha)","Net Change (ha)","Severity","Carbon (t)","Driver"]
    disp2["Area (ha)"]       = disp2["Area (ha)"].apply(lambda x: f"{x:,.0f}")
    disp2["Net Change (ha)"] = disp2["Net Change (ha)"].apply(lambda x: f"{x:+,.0f}" if pd.notna(x) else "-")
    disp2["Carbon (t)"]      = disp2["Carbon (t)"].apply(lambda x: f"{x/1e6:,.2f}M" if pd.notna(x) else "-")
    st.dataframe(disp2, use_container_width=True, height=360, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(cdf)} countries · Source: FAO 2023")

    with st.expander("Methodology and data sources"):
        m1,m2 = st.columns(2)
        with m1:
            st.code("Loss rate : 33,850 ha/yr / 31,557,600 sec = 0.001073 ha/sec\nSource    : FAO 2023 (677,000 ha / 20 yr)\nCarbon    : area_ha x 394 t C/ha (GMA 2024)\nFlood     : area_ha x $57,770 (World Bank 2024)\nJuveniles : area_ha x 54,054/ha/yr (GMA 2024)\nCoastline : area_ha x 10 m (IUCN 2024)")
        with m2:
            st.markdown("**Caveats:** All counters are projections not measurements. The 33,850 ha/yr is a 20-year average. Actual current rate is lower: 46,700 ha/yr (1990-2000) falling to 21,200 ha/yr (2010-2020), a 54% reduction.")
            st.markdown("**Pipeline:** Python ingestion → Snowflake RAW → dbt STAGING → dbt MART → Streamlit")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(f'''<div class="footer">
Data: FAO 2023 &middot; GMA 2024 &middot; UC Santa Cruz/World Bank 2024 &middot; IUCN 2024 &middot; GMW v4.0<br>
Built by <a href="https://linkedin.com/in/likitha-sree" style="color:#6a6760">Likitha Sree Yarabarla</a>
&middot; Climate Data Engineer &middot;
<a href="https://github.com/likitha-sree-data/mangrove-monitor" style="color:#6a6760">github.com/likitha-sree-data/mangrove-monitor</a><br>
Pipeline: Python &middot; Snowflake &middot; dbt &middot; Streamlit &middot; Last updated: {now_str}
</div>''', unsafe_allow_html=True)

    # Auto-refresh every 60 seconds
    refresh_placeholder = st.empty()
    with refresh_placeholder:
        for remaining in range(60, 0, -1):
            refresh_placeholder.caption(f"Auto-refreshing in {remaining}s · {datetime.now().strftime('%H:%M:%S UTC')}")
            time.sleep(1)
    st.rerun()

except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.code(str(e))
