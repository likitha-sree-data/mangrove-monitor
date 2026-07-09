
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
html, body, [class*="css"] { font-family: IBM Plex Sans, sans-serif; }
.main { background-color: #f8f7f4; }
.block-container { padding-top: 2rem; max-width: 1100px; }
.metric-card { background: white; border: 1px solid #d4d1c8; padding: 20px 24px; margin-bottom: 8px; }
.metric-value { font-family: IBM Plex Mono, monospace; font-size: 2rem; font-weight: 400; color: #b83220; line-height: 1; margin: 4px 0; }
.metric-label { font-family: IBM Plex Mono, monospace; font-size: 0.6rem; letter-spacing: 0.15em; text-transform: uppercase; color: #6a6760; margin-bottom: 6px; }
.metric-source { font-family: IBM Plex Mono, monospace; font-size: 0.58rem; color: #a09d98; margin-top: 6px; }
.section-hdr { font-family: IBM Plex Mono, monospace; font-size: 0.6rem; letter-spacing: 0.18em; text-transform: uppercase; color: #6a6760; border-bottom: 1px solid #16150f; padding-bottom: 6px; margin: 28px 0 16px; }
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

# Header
st.markdown("""
<div style="border-bottom:2px solid #16150f;padding-bottom:12px;margin-bottom:24px">
  <div style="font-family:IBM Plex Mono,monospace;font-size:0.6rem;letter-spacing:.16em;text-transform:uppercase;color:#6a6760;margin-bottom:8px">
    Global Mangrove Loss Monitor · Data: FAO 2023, GMA 2024, UC Santa Cruz 2024
  </div>
  <h1 style="font-family:IBM Plex Sans,sans-serif;font-size:2rem;font-weight:300;letter-spacing:-.02em;margin:0">
    Global mangrove forest loss — <strong>real-time estimates</strong>
  </h1>
</div>
""", unsafe_allow_html=True)

try:
    gdf  = load_global()
    cdf  = load_countries()
    rdf  = load_regional()
    rate = float(gdf.iloc[-1]["LOSS_HA_PER_SECOND"])
    c    = live_counts(rate)

    # Live counters
    st.markdown(f'<div class="section-hdr">Cumulative estimates · year to date 2025 · Rate: {rate:.6f} ha/sec from FAO data</div>', unsafe_allow_html=True)

    cols = st.columns(5)
    metrics = [
        ("Hectares lost",        f"{c['ha']:,.0f}",              "Since 1 Jan 2025"),
        ("Carbon storage (t C)", f"{c['carbon']/1e6:,.2f}M",    "394 t C/ha · GMA 2024"),
        ("Flood protection",     f"${c['flood']/1e6:,.1f}M",    "$57,770/ha · World Bank 2024"),
        ("Marine juveniles",     f"{c['fish']/1e6:,.1f}M",      "54,054/ha · GMA 2024"),
        ("Coastline unshielded", f"{c['coast']/1000:,.2f} km",  "10 m/ha · IUCN 2024"),
    ]
    for col, (lbl, val, src) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{lbl}</div>
              <div class="metric-value">{val}</div>
              <div class="metric-source">{src}</div>
            </div>""", unsafe_allow_html=True)

    # Trend chart
    st.markdown('<div class="section-hdr">Annual loss trend · FAO data · 2000–2020</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=gdf["YEAR"], y=gdf["GLOBAL_LOSS_HA"],
                         name="Annual loss (ha)", marker_color="#b83220", opacity=0.75))
    fig.add_trace(go.Scatter(x=gdf["YEAR"], y=gdf["GLOBAL_LOSS_HA"],
                             name="Trend", line=dict(color="#1a6b3c", width=2, dash="dash")))
    fig.update_layout(plot_bgcolor="#f8f7f4", paper_bgcolor="#f8f7f4",
                      font=dict(family="IBM Plex Mono", size=11, color="#6a6760"),
                      height=300, margin=dict(l=0,r=0,t=24,b=0),
                      xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#e8e6e0"))
    st.plotly_chart(fig, use_container_width=True)

    # Regional breakdown
    st.markdown('<div class="section-hdr">Regional breakdown · 2020</div>', unsafe_allow_html=True)
    r2020 = rdf[rdf["YEAR"]==2020].copy()
    cl, cr = st.columns([1.2, 1])
    with cl:
        fig2 = px.bar(r2020.sort_values("TOTAL_AREA_HA"), x="TOTAL_AREA_HA", y="REGION",
                      orientation="h", color="AVG_NET_CHANGE_PCT",
                      color_continuous_scale=["#b83220","#e8e6e0","#1a6b3c"],
                      color_continuous_midpoint=0,
                      labels={"TOTAL_AREA_HA":"Area (ha)","REGION":"","AVG_NET_CHANGE_PCT":"Net chg %"})
        fig2.update_layout(plot_bgcolor="#f8f7f4", paper_bgcolor="#f8f7f4",
                           font=dict(family="IBM Plex Mono",size=10),
                           height=260, margin=dict(l=0,r=0,t=8,b=0))
        st.plotly_chart(fig2, use_container_width=True)
    with cr:
        disp = r2020[["REGION","TOTAL_AREA_HA","TOTAL_LOSS_HA","AVG_NET_CHANGE_PCT","DOMINANT_DRIVER"]].copy()
        disp.columns = ["Region","Area (ha)","Loss (ha)","Chg %","Driver"]
        disp["Area (ha)"] = disp["Area (ha)"].apply(lambda x: f"{x:,.0f}")
        disp["Loss (ha)"] = disp["Loss (ha)"].apply(lambda x: f"{x:,.0f}")
        disp["Chg %"]     = disp["Chg %"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(disp, use_container_width=True, height=260, hide_index=True)

    # Country table
    st.markdown('<div class="section-hdr">Country snapshot · most recent year available</div>', unsafe_allow_html=True)
    disp2 = cdf[["COUNTRY_NAME","REGION","YEAR","AREA_HA","NET_CHANGE_HA",
                  "LOSS_SEVERITY","CARBON_STOCK_TONNES","PRIMARY_DRIVER"]].copy()
    disp2.columns = ["Country","Region","Year","Area (ha)","Net Change (ha)",
                     "Severity","Carbon Stock (t)","Primary Driver"]
    disp2["Area (ha)"]        = disp2["Area (ha)"].apply(lambda x: f"{x:,.0f}")
    disp2["Net Change (ha)"]  = disp2["Net Change (ha)"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "—")
    disp2["Carbon Stock (t)"] = disp2["Carbon Stock (t)"].apply(lambda x: f"{x/1e6:,.2f}M" if pd.notna(x) else "—")
    st.dataframe(disp2, use_container_width=True, height=360, hide_index=True)

    # Footer
    st.markdown(f"""
    <div style="margin-top:40px;border-top:1px solid #d4d1c8;padding-top:16px;
                font-family:IBM Plex Mono,monospace;font-size:0.58rem;color:#a09d98;line-height:2">
        Data: FAO World's Mangroves 2000–2020 (2023) · GMA 2024 · UC Santa Cruz/World Bank 2024 · IUCN 2024<br>
        Built by <a href="https://linkedin.com/in/likitha-sree" style="color:#6a6760">Likitha Sree Yarabarla</a>
        · Climate Data Engineer ·
        <a href="https://github.com/likitha-sree-data/mangrove-monitor" style="color:#6a6760">GitHub</a><br>
        Last refreshed: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}
    </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Check Snowflake credentials in Streamlit Cloud secrets.")
