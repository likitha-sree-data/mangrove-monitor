import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

st.set_page_config(
    page_title="Global Mangrove Loss Monitor",
    page_icon="🌿",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif !important; background-color: #f8f7f4 !important; }
.block-container { padding-top: 1.5rem !important; max-width: 1080px !important; }
div[data-testid="metric-container"] { background: #ffffff; border: 1px solid #d4d1c8; padding: 18px 20px; }
div[data-testid="metric-container"] label { font-family: 'IBM Plex Mono', monospace !important; font-size: 0.58rem !important; letter-spacing: 0.14em !important; text-transform: uppercase !important; color: #6a6760 !important; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace !important; font-size: 1.7rem !important; font-weight: 400 !important; color: #b83220 !important; }
div[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-family: 'IBM Plex Mono', monospace !important; font-size: 0.58rem !important; color: #a09d98 !important; }
.section-rule { font-family: 'IBM Plex Mono', monospace; font-size: 0.58rem; letter-spacing: 0.18em; text-transform: uppercase; color: #6a6760; border-bottom: 1px solid #16150f; padding-bottom: 5px; margin-top: 28px; margin-bottom: 16px; }
.page-header { border-bottom: 2px solid #16150f; padding-bottom: 14px; margin-bottom: 24px; }
.page-kicker { font-family: 'IBM Plex Mono', monospace; font-size: 0.58rem; letter-spacing: 0.16em; text-transform: uppercase; color: #6a6760; margin-bottom: 8px; }
.page-title { font-family: 'IBM Plex Sans', sans-serif; font-size: 1.9rem; font-weight: 300; letter-spacing: -0.02em; color: #16150f; line-height: 1.15; margin: 0; }
.footer-text { font-family: 'IBM Plex Mono', monospace; font-size: 0.56rem; color: #a09d98; line-height: 2; border-top: 1px solid #d4d1c8; padding-top: 16px; margin-top: 40px; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    return snowflake.connector.connect(
        account   = st.secrets["snowflake"]["account"],
        user      = st.secrets["snowflake"]["user"],
        password  = st.secrets["snowflake"]["password"],
        warehouse = st.secrets["snowflake"]["warehouse"],
        database  = st.secrets["snowflake"]["database"],
        role      = st.secrets["snowflake"]["role"]
    )

@st.cache_data(ttl=3600)
def load_global():
    return pd.read_sql("""
        SELECT YEAR, GLOBAL_AREA_HA, GLOBAL_LOSS_HA,
               GLOBAL_NET_CHANGE_HA, GLOBAL_CARBON_STOCK_TONNES,
               LOSS_HA_PER_SECOND
        FROM MANGROVE_MONITOR.STAGING_MART.MART_GLOBAL_SUMMARY
        WHERE GLOBAL_LOSS_HA IS NOT NULL
        ORDER BY YEAR
    """, get_conn())

@st.cache_data(ttl=3600)
def load_countries():
    return pd.read_sql("""
        SELECT COUNTRY_NAME, REGION, YEAR, AREA_HA,
               NET_CHANGE_HA, NET_CHANGE_PCT, LOSS_SEVERITY,
               CARBON_STOCK_TONNES, FLOOD_PROTECTION_USD, PRIMARY_DRIVER
        FROM MANGROVE_MONITOR.STAGING_MART.MART_LOSS_BY_COUNTRY
        WHERE IS_LATEST_SNAPSHOT = TRUE
        ORDER BY AREA_HA DESC
    """, get_conn())

@st.cache_data(ttl=3600)
def load_regional():
    return pd.read_sql("""
        SELECT REGION, YEAR, TOTAL_AREA_HA, TOTAL_LOSS_HA,
               TOTAL_NET_CHANGE_HA, AVG_NET_CHANGE_PCT, DOMINANT_DRIVER
        FROM MANGROVE_MONITOR.STAGING_MART.MART_LOSS_BY_REGION
        ORDER BY YEAR, TOTAL_AREA_HA DESC
    """, get_conn())

def live_counts(rate):
    T0   = datetime(2025, 1, 1, tzinfo=timezone.utc)
    secs = (datetime.now(timezone.utc) - T0).total_seconds()
    ha   = secs * rate
    return dict(ha=ha, carbon=ha*394, flood=ha*57770, fish=ha*54054, coast=ha*10)

st.markdown("""
<div class="page-header">
    <div class="page-kicker">Global Mangrove Loss Monitor · v2.1 · Data: FAO 2023 · GMA 2024 · UC Santa Cruz 2024</div>
    <div class="page-title">Global mangrove forest loss &mdash; <strong>real-time estimates</strong></div>
</div>
""", unsafe_allow_html=True)

try:
    gdf  = load_global()
    cdf  = load_countries()
    rdf  = load_regional()
    rate = float(gdf.iloc[-1]["LOSS_HA_PER_SECOND"])
    c    = live_counts(rate)

    st.markdown(f'<div class="section-rule">Cumulative estimates · year to date 2025 · Rate: {rate:.6f} ha/sec · FAO 2023</div>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Hectares lost",        f"{c['ha']:,.0f}",           "Since 1 Jan 2025",              delta_color="off")
    col2.metric("Carbon storage lost",  f"{c['carbon']/1e6:,.2f}M t","394 t C/ha · GMA 2024",        delta_color="off")
    col3.metric("Flood protection",     f"${c['flood']/1e9:,.3f}B",  "$57,770/ha · World Bank 2024",  delta_color="off")
    col4.metric("Marine juveniles",     f"{c['fish']/1e6:,.1f}M",    "54,054/ha · GMA 2024",          delta_color="off")
    col5.metric("Coastline unshielded", f"{c['coast']/1000:,.1f} km","10 m/ha · IUCN 2024",           delta_color="off")

    st.markdown('<div class="section-rule">Annual loss trend · FAO data · 2000-2020</div>', unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=gdf["YEAR"], y=gdf["GLOBAL_LOSS_HA"], name="Annual loss (ha)",
                         marker_color="#b83220", opacity=0.75,
                         hovertemplate="Year: %{x}<br>Loss: %{y:,.0f} ha<extra></extra>"))
    fig.add_trace(go.Scatter(x=gdf["YEAR"], y=gdf["GLOBAL_LOSS_HA"], name="Trend",
                             mode="lines+markers", line=dict(color="#1a6b3c", width=2, dash="dash"),
                             marker=dict(size=6, color="#1a6b3c"),
                             hovertemplate="Year: %{x}<br>Loss: %{y:,.0f} ha<extra></extra>"))
    fig.update_layout(plot_bgcolor="#ffffff", paper_bgcolor="#f8f7f4",
                      font=dict(family="IBM Plex Mono", size=11, color="#6a6760"),
                      height=300, margin=dict(l=0,r=0,t=16,b=0),
                      xaxis=dict(title="Year", showgrid=False, linecolor="#d4d1c8"),
                      yaxis=dict(title="Hectares lost", showgrid=True, gridcolor="#e8e6e0", tickformat=",d"),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-rule">Regional breakdown · 2020</div>', unsafe_allow_html=True)
    r2020 = rdf[rdf["YEAR"]==2020].copy()
    left, right = st.columns([3,2])

    with left:
        fig2 = px.bar(r2020.sort_values("TOTAL_AREA_HA"), x="TOTAL_AREA_HA", y="REGION",
                      orientation="h", color="AVG_NET_CHANGE_PCT",
                      color_continuous_scale=["#b83220","#f0ede8","#1a6b3c"],
                      color_continuous_midpoint=0,
                      labels={"TOTAL_AREA_HA":"Total area (ha)","REGION":"","AVG_NET_CHANGE_PCT":"Net chg %"})
        fig2.update_layout(plot_bgcolor="#ffffff", paper_bgcolor="#f8f7f4",
                           font=dict(family="IBM Plex Mono", size=10, color="#6a6760"),
                           height=280, margin=dict(l=0,r=0,t=8,b=0),
                           xaxis=dict(tickformat=",d", showgrid=True, gridcolor="#e8e6e0"))
        st.plotly_chart(fig2, use_container_width=True)

    with right:
        disp = r2020[["REGION","TOTAL_AREA_HA","TOTAL_LOSS_HA","AVG_NET_CHANGE_PCT","DOMINANT_DRIVER"]].copy()
        disp.columns = ["Region","Area (ha)","Loss (ha)","Chg %","Driver"]
        disp["Area (ha)"] = disp["Area (ha)"].apply(lambda x: f"{x:,.0f}")
        disp["Loss (ha)"] = disp["Loss (ha)"].apply(lambda x: f"{x:,.0f}")
        disp["Chg %"]     = disp["Chg %"].apply(lambda x: f"{x:.3f}%")
        st.dataframe(disp, use_container_width=True, height=280, hide_index=True)

    st.markdown('<div class="section-rule">Country snapshot · most recent year per country</div>', unsafe_allow_html=True)

    fc1, fc2, _ = st.columns([1,1,3])
    with fc1:
        regions = ["All regions"] + sorted(cdf["REGION"].unique().tolist())
        sel_region = st.selectbox("Region", regions, label_visibility="collapsed")
    with fc2:
        severities = ["All severity levels"] + sorted(cdf["LOSS_SEVERITY"].unique().tolist())
        sel_sev = st.selectbox("Severity", severities, label_visibility="collapsed")

    filtered = cdf.copy()
    if sel_region != "All regions":
        filtered = filtered[filtered["REGION"] == sel_region]
    if sel_sev != "All severity levels":
        filtered = filtered[filtered["LOSS_SEVERITY"] == sel_sev]

    disp2 = filtered[["COUNTRY_NAME","REGION","YEAR","AREA_HA","NET_CHANGE_HA",
                       "LOSS_SEVERITY","CARBON_STOCK_TONNES","PRIMARY_DRIVER"]].copy()
    disp2.columns = ["Country","Region","Year","Area (ha)","Net Change (ha)","Severity","Carbon (t)","Driver"]
    disp2["Area (ha)"]       = disp2["Area (ha)"].apply(lambda x: f"{x:,.0f}")
    disp2["Net Change (ha)"] = disp2["Net Change (ha)"].apply(lambda x: f"{x:+,.0f}" if pd.notna(x) else "-")
    disp2["Carbon (t)"]      = disp2["Carbon (t)"].apply(lambda x: f"{x/1e6:,.2f}M" if pd.notna(x) else "-")
    st.dataframe(disp2, use_container_width=True, height=380, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(cdf)} countries · Source: FAO 2023")

    with st.expander("Methodology and data sources"):
        st.markdown("""
**Loss rate:** 677,000 ha lost 2000-2020 (FAO 2023) = 33,850 ha/yr = 0.001073 ha/sec  
**Carbon:** area_ha × 394 t C/ha (GMA 2024, global average biomass + top 1m soil)  
**Flood protection:** area_ha × $57,770 ($855B total / 14.8M ha, UC Santa Cruz / World Bank 2024)  
**Marine juveniles:** area_ha × 54,054 (800B/yr / 14.76M ha, GMA 2024)  
**Coastline:** area_ha × 10m (conservative peer-reviewed estimate, IUCN 2024)  

**Caveats:** All counters are projections not real-time measurements.
The 33,850 ha/yr is a 20-year average. Actual current rate is lower —
FAO data show decline from 46,700 ha/yr (1990-2000) to 21,200 ha/yr (2010-2020).

**Pipeline:** Python ingestion → Snowflake RAW → dbt STAGING → dbt MART → Streamlit  
**Repo:** github.com/likitha-sree-data/mangrove-monitor
        """)

    st.markdown(f"""
<div class="footer-text">
Data: FAO 2023 &middot; GMA 2024 &middot; UC Santa Cruz/World Bank 2024 &middot; IUCN 2024 &middot; GMW v4.0<br>
Built by <a href="https://linkedin.com/in/likitha-sree" style="color:#6a6760">Likitha Sree Yarabarla</a>
&middot; Climate Data Engineer &middot;
<a href="https://github.com/likitha-sree-data/mangrove-monitor" style="color:#6a6760">GitHub</a><br>
Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")} &middot; Snowflake · dbt · Python · Streamlit
</div>
""", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.code(str(e))
