"""
Global Energy Chokepoints Monitor
Tracks critical maritime energy passages with geopolitical access status.
"""

import streamlit as st
import plotly.graph_objects as go
import feedparser
import pandas as pd
import requests
import re
from datetime import datetime

st.set_page_config(
    page_title="Global Energy Chokepoints Monitor",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Status System ─────────────────────────────────────────────────────────────
# OPEN            = All nations transit freely
# SELECTIVE       = Open in name, but controller can deny/harass specific flags
# HOSTILE_TARGETED= Active attacks on specific nation-linked vessels, others safe
# RESTRICTED      = Capacity significantly reduced (non-political)
# CLOSED          = Full blockade / shutdown

STATUS_CONFIG = {
    "OPEN":             {"color": "#00cc44", "bg": "#002211", "emoji": "🟢", "label": "Open"},
    "SELECTIVE":        {"color": "#00aaff", "bg": "#001833", "emoji": "🔵", "label": "Selective"},
    "HOSTILE_TARGETED": {"color": "#ff8800", "bg": "#2a1000", "emoji": "🟠", "label": "Hostile-Targeted"},
    "RESTRICTED":       {"color": "#ffcc00", "bg": "#2a2200", "emoji": "🟡", "label": "Restricted"},
    "CLOSED":           {"color": "#ff3333", "bg": "#330000", "emoji": "🔴", "label": "Closed"},
}

RISK_CONFIG = {
    "LOW":       {"color": "#00cc44", "emoji": "🔵"},
    "MEDIUM":    {"color": "#ffcc00", "emoji": "🟡"},
    "HIGH":      {"color": "#ff8800", "emoji": "🟠"},
    "VERY HIGH": {"color": "#ff3333", "emoji": "🔴"},
}

# ── Chokepoint Data ───────────────────────────────────────────────────────────
CHOKEPOINTS = {
    "Strait of Hormuz": {
        "lat": 26.5, "lon": 56.3,
        "oil_flow_mbd": 17.0,
        "pct_global_oil": 20,
        "pct_global_lng": 17,
        "region": "Persian Gulf / Oman",
        "status": "SELECTIVE",
        "risk": "HIGH",
        "icon": "🛢️",
        "controller": "Iran (de facto) / Oman",
        "description": (
            "World's most critical oil chokepoint. Connects Persian Gulf producers "
            "(Saudi Arabia, UAE, Iraq, Kuwait, Iran, Qatar) to the Indian Ocean. "
            "~20% of global oil + 17% of LNG. Iran regularly seizes or harasses "
            "vessels linked to 'enemy' nations while allowing allied/neutral ships to pass freely."
        ),
        "access": {
            "free": ["🇨🇳 China", "🇷🇺 Russia", "🇮🇳 India", "🇵🇰 Pakistan", "neutral flags"],
            "restricted": ["🇺🇸 US-affiliated vessels", "🇮🇱 Israeli-linked cargo", "🇬🇧 UK vessels (high risk)"],
            "restriction_reason": "Iran seizes/harasses vessels for leverage in nuclear negotiations or retaliation; 2023–2024: 10+ vessels seized or harassed",
        },
        "keywords": ["Strait of Hormuz", "Iran tanker seizure", "Persian Gulf shipping", "Hormuz blockade"],
        "affected_countries": [
            {"country": "🇯🇵 Japan",       "score": 95, "reason": "87–90% crude from Middle East; strategic reserves cover ~90 days only. Selective access = cost spike even if 'open'"},
            {"country": "🇹🇼 Taiwan",       "score": 92, "reason": "Near-total import dependence; no domestic oil; ~85% from Middle East; TSMC fab energy at risk"},
            {"country": "🇰🇷 South Korea",  "score": 88, "reason": "70%+ crude + 40% LNG from Gulf; export-heavy economy crippled by energy cost surge"},
            {"country": "🇸🇬 Singapore",    "score": 82, "reason": "World's 3rd-largest refining hub; entire crude supply chain disrupted; Jurong Island refinery risk"},
            {"country": "🇮🇳 India",        "score": 72, "reason": "60%+ crude from Gulf; Iran sanctions complicate sourcing; Reliance refinery calibrated for Gulf crudes"},
            {"country": "🇨🇳 China",        "score": 60, "reason": "~40% crude from Middle East; SPR buffer (90 days); Iran relationship = partial protection under 'selective' regime"},
            {"country": "🇦🇪 UAE",          "score": 55, "reason": "Fujairah port = critical transshipment hub; domestic exports (ADCO) directly blocked"},
            {"country": "🇸🇦 Saudi Arabia", "score": 50, "reason": "~6M bbl/day exports via Ras Tanura; East–West pipeline (Petro Rabigh) offers partial bypass to Red Sea"},
        ],
    },

    "Strait of Malacca": {
        "lat": 2.5, "lon": 101.5,
        "oil_flow_mbd": 16.0,
        "pct_global_oil": 25,
        "pct_global_lng": 0,
        "region": "Malaysia / Singapore / Indonesia",
        "status": "OPEN",
        "risk": "MEDIUM",
        "icon": "⚓",
        "controller": "Malaysia, Singapore, Indonesia (joint)",
        "description": (
            "Busiest shipping lane by tonnage. ~25% of global seaborne trade. "
            "Currently open to all flags with no political restrictions. "
            "Piracy remains a low-level risk but has declined sharply since 2010. "
            "VLCCs (very large crude carriers) must transit partially laden — deepest draft ~25m."
        ),
        "access": {
            "free": ["All nations"],
            "restricted": [],
            "restriction_reason": "No current political restrictions. Minor piracy risk in northern reaches near Myanmar coast.",
        },
        "keywords": ["Strait of Malacca", "Malacca shipping", "South China Sea route", "Malacca piracy"],
        "affected_countries": [
            {"country": "🇸🇬 Singapore",    "score": 98, "reason": "Economy built entirely on this chokepoint: port, bunkering, refining — existential if blocked"},
            {"country": "🇨🇳 China",        "score": 92, "reason": "'Malacca Dilemma': ~80% energy imports transit here; Pearl River Delta manufacturing collapses"},
            {"country": "🇯🇵 Japan",        "score": 90, "reason": "All Middle East/Africa energy transits here; no viable alternative for VLCCs"},
            {"country": "🇰🇷 South Korea",  "score": 87, "reason": "Same as Japan — island-like energy dependency; Ulsan/Yeosu petrochemical hubs paralysed"},
            {"country": "🇹🇼 Taiwan",       "score": 85, "reason": "TSMC + semiconductor supply chain entirely dependent on uninterrupted sea-lane energy delivery"},
            {"country": "🇦🇺 Australia",    "score": 55, "reason": "Iron ore + LNG + coal exports to NE Asia disrupted; ~45% export revenue at risk"},
            {"country": "🇮🇩 Indonesia",    "score": 28, "reason": "Controls strait; own coal/palm oil can reroute via Sunda/Lombok; internal waters usable"},
            {"country": "🇮🇳 India",        "score": 25, "reason": "Eastern port exports disrupted; oil imports less exposed vs Hormuz"},
        ],
    },

    "Suez Canal": {
        "lat": 30.5, "lon": 32.3,
        "oil_flow_mbd": 5.5,
        "pct_global_oil": 9,
        "pct_global_lng": 8,
        "region": "Egypt",
        "status": "OPEN",
        "risk": "MEDIUM",
        "icon": "🚢",
        "controller": "Egypt (Suez Canal Authority)",
        "description": (
            "Critical shortcut between Mediterranean and Red Sea. ~9% oil + 8% LNG globally. "
            "Open to all commercial flags. Egypt earns ~$9–10B/year in toll revenue (~2% GDP) "
            "— giving it strong incentive to keep it open. "
            "2021 Ever Given blockage cost ~$9.6B/day. Closure = +14 days via Cape of Good Hope."
        ),
        "access": {
            "free": ["All commercial vessels"],
            "restricted": ["Israeli military vessels (Egypt reserves right)"],
            "restriction_reason": "Egypt has historically closed to Israeli warships (1967 war). Commercial shipping is universally open under international law.",
        },
        "keywords": ["Suez Canal", "Egypt shipping", "Red Sea reroute", "Suez Canal traffic"],
        "affected_countries": [
            {"country": "🇪🇬 Egypt",        "score": 92, "reason": "Canal = ~$10B/year revenue + tourism lifeline; closure = IMF crisis for debt-laden economy"},
            {"country": "🇮🇱 Israel",       "score": 75, "reason": "All sea access to Asia goes via Suez or longer route; Eilat port (Red Sea) becomes critical only exit"},
            {"country": "🇮🇹 Italy",        "score": 65, "reason": "Mediterranean gateway; Asian goods + Middle East energy imports all rerouted; refinery input delays"},
            {"country": "🇩🇪 Germany",      "score": 55, "reason": "Largest EU manufacturer; Asia components (China, Vietnam, Thailand) +2–3 weeks delay = factory slowdowns"},
            {"country": "🇳🇱 Netherlands",  "score": 55, "reason": "Rotterdam = Europe's main gateway; ARA (Amsterdam-Rotterdam-Antwerp) hub throughput drops 30%+"},
            {"country": "🇬🇧 UK",           "score": 45, "reason": "Asian goods rerouted; energy imports partly affected; inflation driven by freight surge"},
            {"country": "🇮🇳 India",        "score": 40, "reason": "Pharma + textile exports to EU/US rerouted via Cape — weeks of delay; JNPT port backed up"},
            {"country": "🇨🇳 China",        "score": 35, "reason": "BRI goods to Europe face +2 weeks delay; Yiwu–Madrid freight train (trans-Siberian) gains traffic"},
        ],
    },

    "Bab-el-Mandeb Strait": {
        "lat": 12.6, "lon": 43.3,
        "oil_flow_mbd": 3.8,
        "pct_global_oil": 6,
        "pct_global_lng": 4,
        "region": "Yemen / Djibouti / Eritrea",
        "status": "HOSTILE_TARGETED",
        "risk": "VERY HIGH",
        "icon": "⚠️",
        "controller": "Houthi Movement (de facto Yemen coast control)",
        "description": (
            "Southern gateway to Red Sea / Suez. Since October 2023, Houthis have launched "
            "300+ drone/missile attacks on vessels. Critically: attacks are SELECTIVE — "
            "US, UK, Israeli-linked ships are primary targets. Chinese and Russian vessels "
            "pass without incident. 80%+ of major carriers rerouted via Cape of Good Hope."
        ),
        "access": {
            "free": ["🇨🇳 Chinese-flagged vessels", "🇷🇺 Russian-flagged vessels", "🇮🇷 Iranian vessels", "vessels with no US/UK/IL link"],
            "restricted": ["🇺🇸 US-affiliated ships", "🇬🇧 UK-linked vessels", "🇮🇱 Israeli cargo/port-of-call"],
            "restriction_reason": "Houthis explicitly exempt Chinese + Russian ships. US/UK vessels face active missile + drone attacks. Maersk, MSC, CMA CGM suspended Red Sea service since Dec 2023.",
        },
        "keywords": ["Bab el Mandeb", "Houthi attack Red Sea", "Red Sea shipping attack", "Yemen Houthi drone ship"],
        "affected_countries": [
            {"country": "🇩🇯 Djibouti",     "score": 95, "reason": "Port of Djibouti = 95% of GDP; Horn of Africa trade hub collapses without Red Sea traffic"},
            {"country": "🇾🇪 Yemen",         "score": 90, "reason": "Humanitarian aid shipments blocked; Houthis control, but their own population starves faster"},
            {"country": "🇪🇬 Egypt",         "score": 85, "reason": "Suez Canal revenue already collapsed 50%+ from rerouting; foreign currency crisis deepened"},
            {"country": "🇪🇺 EU",            "score": 60, "reason": "40% Asian goods + 30% energy rerouted via Cape; shipping costs x3; inflation impact visible"},
            {"country": "🇮🇱 Israel",        "score": 58, "reason": "Eilat port (main Red Sea outlet) effectively closed; Ashdod/Haifa overloaded; trade corridor lost"},
            {"country": "🇸🇦 Saudi Arabia",  "score": 52, "reason": "Yanbu Red Sea terminal at risk; Eastern pipeline bypasses Hormuz but not Bab-el-Mandeb exit"},
            {"country": "🇮🇳 India",         "score": 38, "reason": "Europe-bound pharma/textile exports rerouted; Indian Navy conducting escort operations"},
            {"country": "🇨🇳 China",         "score": 12, "reason": "Chinese vessels pass freely by Houthi agreement — BRI port investments partly insulated"},
        ],
    },

    "Turkish Straits (Bosphorus)": {
        "lat": 41.1, "lon": 29.0,
        "oil_flow_mbd": 2.4,
        "pct_global_oil": 3,
        "pct_global_lng": 0,
        "region": "Turkey",
        "status": "SELECTIVE",
        "risk": "MEDIUM",
        "icon": "🌊",
        "controller": "Turkey (under 1936 Montreux Convention)",
        "description": (
            "Only sea passage from Black Sea to Mediterranean. Turkey holds legal authority "
            "under Montreux Convention to restrict warships in wartime — exercised since Feb 2022 "
            "(Russia-Ukraine war). Commercial shipping remains open. "
            "~2.4M bbl/day: Russian Novorossiysk + Kazakh CPC pipeline exports."
        ),
        "access": {
            "free": ["All commercial vessels", "Non-belligerent warships in peacetime"],
            "restricted": ["Warships of belligerent nations (Montreux Art.19)", "Russian Navy warships (since Feb 2022)"],
            "restriction_reason": "Turkey closed to all non-Black Sea warships since Russia invaded Ukraine. Commercial oil tankers (Russia/Kazakhstan) continue to pass freely — Turkey avoids secondary sanctions risk.",
        },
        "keywords": ["Bosphorus Strait", "Turkish Straits Montreux", "Black Sea oil export", "Russia tanker Bosphorus"],
        "affected_countries": [
            {"country": "🇷🇺 Russia",        "score": 68, "reason": "Baltic terminals (Primorsk/Ust-Luga) carry more load since Bosphorus Navy closure; oil tankers still pass"},
            {"country": "🇰🇿 Kazakhstan",    "score": 65, "reason": "CPC pipeline exports ~1.5M bbl/day via Russia to Novorossiysk — only viable export route; closure = catastrophe"},
            {"country": "🇺🇦 Ukraine",       "score": 60, "reason": "Russian Black Sea fleet locked in — benefit. But Odessa grain exports constrained by Russian naval presence"},
            {"country": "🇧🇬 Bulgaria",      "score": 52, "reason": "Burgas port depends on Black Sea tanker traffic; energy imports from Russian crude historically high"},
            {"country": "🇷🇴 Romania",       "score": 38, "reason": "Offshore Black Sea gas (Neptune Deep project) export blocked if full closure; Constanta port traffic drops"},
            {"country": "🇹🇷 Turkey",        "score": 30, "reason": "Transit toll revenue loss; but Turkey benefits geopolitically from leverage over both sides"},
            {"country": "🇬🇷 Greece",        "score": 25, "reason": "Thessaloniki port disrupted; Russian tourist + trade flows already sanctioned, impact manageable"},
            {"country": "🇦🇿 Azerbaijan",    "score": 15, "reason": "BTC pipeline exports to Ceyhan (Mediterranean) bypass Bosphorus entirely — protected"},
        ],
    },

    "Panama Canal": {
        "lat": 9.1, "lon": -79.7,
        "oil_flow_mbd": 1.0,
        "pct_global_oil": 2,
        "pct_global_lng": 7,
        "region": "Panama",
        "status": "RESTRICTED",
        "risk": "MEDIUM",
        "icon": "🌧️",
        "controller": "Panama Canal Authority",
        "description": (
            "Critical for US LNG exports (~7% global LNG) and Pacific-Atlantic trade. "
            "Restriction is CLIMATE-DRIVEN, not political — 2023–24 drought reduced water "
            "levels so severely that daily transits fell from 36 to 22 vessels. "
            "LNG tanker queues stretched 6+ weeks. Politically neutral: all flags equally affected."
        ),
        "access": {
            "free": ["All nations (politically)"],
            "restricted": ["All large vessels (physically — water depth limits)"],
            "restriction_reason": "Not geopolitical — El Niño drought reduced Gatun Lake to record low levels. Draft restrictions mean LNG tankers and VLCCs must wait or reroute via Cape Horn (+21 days). Expected to ease when rains return.",
        },
        "keywords": ["Panama Canal drought", "Panama Canal restriction", "LNG tanker Panama delay", "Canal water level 2024"],
        "affected_countries": [
            {"country": "🇵🇦 Panama",        "score": 92, "reason": "Canal = 6% direct GDP + multiplier effect; toll revenue plunged $200M+ during drought restriction"},
            {"country": "🇺🇸 USA",           "score": 55, "reason": "LNG export revenue at risk (Qatar/Australia competition gains); East/West coast shipping efficiency lost"},
            {"country": "🇯🇵 Japan",         "score": 52, "reason": "US LNG (~20–25% of imports) rerouted via Cape Horn; spot LNG price spike forces expensive alternatives"},
            {"country": "🇰🇷 South Korea",   "score": 48, "reason": "US LNG contracts delayed; forced to buy expensive spot cargoes from Qatar/Australia at premium"},
            {"country": "🇨🇳 China",         "score": 35, "reason": "US soy/corn agricultural imports rerouted; LNG from alternative suppliers costlier"},
            {"country": "🇨🇱 Chile",         "score": 30, "reason": "Copper + lithium exports to Atlantic rerouted; freight cost surge cuts export margins"},
            {"country": "🇦🇷 Argentina",     "score": 22, "reason": "Soy/beef exports to Asia disrupted; geographic position means Cape Horn is still reachable"},
            {"country": "🇹🇼 Taiwan",        "score": 20, "reason": "US military logistics to Pacific impacted marginally; Taiwan Strait remains primary strategic concern"},
        ],
    },

    "Danish Straits": {
        "lat": 55.8, "lon": 12.0,
        "oil_flow_mbd": 1.5,
        "pct_global_oil": 2,
        "pct_global_lng": 3,
        "region": "Denmark / Sweden",
        "status": "OPEN",
        "risk": "LOW",
        "icon": "🧊",
        "controller": "Denmark (Øresund / Great Belt authority)",
        "description": (
            "Gateway to/from Baltic Sea. Open to all commercial shipping. "
            "Russian Baltic pipeline terminals (Primorsk ~1.5M bbl/day, Ust-Luga) depend on this passage. "
            "Denmark has legal authority to restrict passage under international law but has not exercised it. "
            "Nord Stream pipeline sabotage (2022) shifted gas dynamics but tanker traffic continues."
        ),
        "access": {
            "free": ["All commercial vessels"],
            "restricted": ["Russian military vessels (NATO political pressure, not formal closure)"],
            "restriction_reason": "No formal closure. Denmark faces pressure to restrict Russian oil tanker passage but has declined citing international law. 'Shadow fleet' tankers transit regularly.",
        },
        "keywords": ["Danish Straits", "Baltic Sea shipping", "Russia oil Baltic", "Primorsk terminal", "shadow fleet Baltic"],
        "affected_countries": [
            {"country": "🇫🇮 Finland",       "score": 78, "reason": "All seaborne trade exits via Baltic/Danish Straits; Vuosaari (Helsinki) port is Finland's economic artery"},
            {"country": "🇱🇹 Lithuania",     "score": 70, "reason": "Klaipeda LNG terminal (only Baltic LNG import terminal) access blocked; gas security crisis"},
            {"country": "🇪🇪 Estonia",       "score": 68, "reason": "Tallinn port entirely Baltic-dependent; 35% of GDP linked to maritime trade services"},
            {"country": "🇱🇻 Latvia",        "score": 65, "reason": "Riga port; Russian transit traffic declining but remaining hydrocarbon flows critical"},
            {"country": "🇸🇪 Sweden",        "score": 58, "reason": "Baltic export hub; automotive (Volvo Gothenburg), telecom (Ericsson) components stall"},
            {"country": "🇵🇱 Poland",        "score": 42, "reason": "Gdansk (Lotos refinery) + Swinoujscie LNG terminal access blocked; both are strategic Polish energy assets"},
            {"country": "🇷🇺 Russia",        "score": 40, "reason": "Primorsk + Ust-Luga terminals (key sanctions-evading oil export route) shut down = revenue collapse"},
            {"country": "🇩🇪 Germany",       "score": 20, "reason": "Kiel Canal alternative available; majority of shipping via North Sea/Rotterdam — manageable"},
        ],
    },

    "Lombok Strait": {
        "lat": -8.7, "lon": 115.7,
        "oil_flow_mbd": 2.5,
        "pct_global_oil": 4,
        "pct_global_lng": 0,
        "region": "Indonesia (Bali / Lombok)",
        "status": "OPEN",
        "risk": "LOW",
        "icon": "🌴",
        "controller": "Indonesia",
        "description": (
            "Deep-water VLCC alternative when Malacca is blocked or congested. "
            "Wide enough for fully laden VLCCs (which Malacca cannot accommodate at full draft). "
            "+2–3 days vs Malacca route. No political restrictions. "
            "Acts as pressure-release valve — becomes critical if Malacca is disrupted."
        ),
        "access": {
            "free": ["All nations"],
            "restricted": [],
            "restriction_reason": "No restrictions. Indonesia exercises archipelagic sea lane rights under UNCLOS — transit passage guaranteed.",
        },
        "keywords": ["Lombok Strait", "Indonesia VLCC tanker", "Sunda Strait", "Malacca alternative route"],
        "affected_countries": [
            {"country": "🇨🇳 China",         "score": 32, "reason": "Fallback if Malacca blocked; cannot absorb full Malacca volume — large tankers only, not bulk shipping"},
            {"country": "🇯🇵 Japan",         "score": 28, "reason": "VLCCs already use Lombok; blockage = no Pacific deep-water alternative; smaller vessels can use Sunda"},
            {"country": "🇦🇺 Australia",     "score": 22, "reason": "LNG tanker traffic to NE Asia transits here; Woodside/INPEX project revenue at risk"},
            {"country": "🇮🇩 Indonesia",     "score": 18, "reason": "Territorial waters; Bali tourism economy secondarily affected; internal Pertamina logistics impacted"},
        ],
    },
}


# ── News Fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=900)
def fetch_news(keywords: list, max_items: int = 6) -> list:
    results, seen = [], set()
    for kw in keywords[:2]:
        try:
            url = f"https://news.google.com/rss/search?q={requests.utils.quote(kw)}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_items]:
                title = entry.get("title", "")
                if title in seen:
                    continue
                seen.add(title)
                clean = re.sub(r'\s+-\s+\S+\s*$', '', title)
                results.append({
                    "title": clean,
                    "link": entry.get("link", "#"),
                    "published": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", ""),
                })
        except Exception:
            pass
    return results[:max_items]


# ── Map ───────────────────────────────────────────────────────────────────────
def build_map(selected: str = None) -> go.Figure:
    lats, lons, texts, colors, sizes, icons = [], [], [], [], [], []
    for name, cp in CHOKEPOINTS.items():
        sc = STATUS_CONFIG[cp["status"]]
        rc = RISK_CONFIG[cp["risk"]]
        lats.append(cp["lat"])
        lons.append(cp["lon"])
        icons.append(cp["icon"])
        colors.append(sc["color"])
        sizes.append(24 if name == selected else 16)
        texts.append(
            f"<b>{name}</b><br>"
            f"Controller: {cp['controller']}<br>"
            f"Status: {sc['emoji']} {sc['label']}<br>"
            f"Risk: {rc['emoji']} {cp['risk']}<br>"
            f"Oil: {cp['oil_flow_mbd']}M bbl/day ({cp['pct_global_oil']}% world)"
        )

    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons,
        mode="markers+text",
        marker=dict(size=sizes, color=colors, symbol="circle",
                    line=dict(width=2, color="white"), opacity=0.92),
        text=icons,
        textposition="middle center",
        textfont=dict(size=13),
        hovertext=texts,
        hoverinfo="text",
        showlegend=False,
    ))
    fig.add_trace(go.Scattergeo(
        lat=[cp["lat"] + 2.8 for cp in CHOKEPOINTS.values()],
        lon=[cp["lon"] for cp in CHOKEPOINTS.values()],
        mode="text",
        text=list(CHOKEPOINTS.keys()),
        textfont=dict(size=8, color="rgba(220,220,255,0.7)"),
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.update_layout(
        geo=dict(
            showland=True, landcolor="#1a2332",
            showocean=True, oceancolor="#0d1421",
            showcoastlines=True, coastlinecolor="#2a3a4a",
            showcountries=True, countrycolor="#243040",
            showframe=False,
            projection_type="natural earth",
            bgcolor="#0d1421",
        ),
        paper_bgcolor="#0d1421",
        margin=dict(l=0, r=0, t=0, b=0),
        height=470,
    )
    return fig


# ── UI helpers ────────────────────────────────────────────────────────────────
def status_badge(status: str) -> str:
    sc = STATUS_CONFIG[status]
    return (f'<span style="background:{sc["bg"]};color:{sc["color"]};'
            f'padding:2px 10px;border-radius:4px;border:1px solid {sc["color"]};'
            f'font-size:0.82em;font-weight:bold">{sc["emoji"]} {sc["label"]}</span>')


def risk_badge(risk: str) -> str:
    rc = RISK_CONFIG[risk]
    return f'<span style="color:{rc["color"]};font-weight:bold">{rc["emoji"]} {risk}</span>'


def impact_bar(score: int) -> str:
    filled = int(score / 10)
    color = "#ff3333" if score >= 80 else "#ff8800" if score >= 50 else "#ffcc00"
    bar = (f'<span style="color:{color}">{"█" * filled}</span>'
           f'<span style="color:#333">{"░" * (10 - filled)}</span>')
    return f'{bar} <b style="color:{color}">{score}%</b>'


# ── Legend ────────────────────────────────────────────────────────────────────
def render_legend():
    items = [
        ("🟢", "OPEN", "All nations freely transit"),
        ("🔵", "SELECTIVE", "Open in name; controller restricts specific nations"),
        ("🟠", "HOSTILE-TARGETED", "Active attacks on specific flags; others safe"),
        ("🟡", "RESTRICTED", "Capacity reduced (non-political, e.g. climate)"),
        ("🔴", "CLOSED", "Full blockade / shutdown"),
    ]
    html = '<div style="background:#111;border:1px solid #333;border-radius:8px;padding:12px 16px;font-size:0.82em">'
    html += '<b style="color:#ccc">Status Legend</b><br><br>'
    for emoji, label, desc in items:
        html += f'{emoji} <b>{label}</b> — <span style="color:#999">{desc}</span><br>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.markdown("""
    <div style="text-align:center;padding:8px 0 4px 0">
        <h1 style="color:#ff8800;margin:0;font-size:1.9em">🛢️ Global Energy Chokepoints Monitor</h1>
        <p style="color:#888;margin:4px 0;font-size:0.9em">
        Geopolitical access status · Country impact analysis · Live news
        </p>
    </div>
    """, unsafe_allow_html=True)

    # KPI bar
    statuses = [cp["status"] for cp in CHOKEPOINTS.values()]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Chokepoints", len(CHOKEPOINTS))
    c2.metric("🟢 Open", statuses.count("OPEN"))
    c3.metric("🔵 Selective", statuses.count("SELECTIVE"))
    c4.metric("🟠 Hostile-Targeted", statuses.count("HOSTILE_TARGETED"))
    c5.metric("🟡 Restricted", statuses.count("RESTRICTED"))
    c6.metric("🔴 Closed", statuses.count("CLOSED"))

    st.divider()

    # Layout
    col_map, col_side = st.columns([3, 1])

    with col_side:
        st.markdown("### 🗺️ Chokepoint")
        selected = st.radio(
            "select",
            list(CHOKEPOINTS.keys()),
            format_func=lambda x: f"{CHOKEPOINTS[x]['icon']} {x}",
            label_visibility="collapsed",
        )
        cp = CHOKEPOINTS[selected]
        st.markdown("---")
        st.markdown(f"**Status:** {status_badge(cp['status'])}", unsafe_allow_html=True)
        st.markdown(f"**Risk:** {risk_badge(cp['risk'])}", unsafe_allow_html=True)
        st.markdown(f"**Controller:** {cp['controller']}")
        st.markdown(f"**Oil:** {cp['oil_flow_mbd']}M bbl/d ({cp['pct_global_oil']}% global)")
        if cp["pct_global_lng"]:
            st.markdown(f"**LNG:** {cp['pct_global_lng']}% global")
        st.markdown("---")
        render_legend()

    with col_map:
        st.plotly_chart(build_map(selected), use_container_width=True,
                        config={"displayModeBar": False})

    # Detail
    cp = CHOKEPOINTS[selected]
    st.markdown(f"## {cp['icon']} {selected}")
    st.markdown(f"*{cp['description']}*")

    tab_access, tab_impact, tab_news, tab_compare = st.tabs(
        ["🔐 Access Control", "🌍 Country Impact", "📰 News", "📊 Compare All"]
    )

    # ── Tab: Access Control ───────────────────────────────────────────────────
    with tab_access:
        ac = cp["access"]
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### 🟢 Can Transit Freely")
            for f in ac["free"]:
                st.markdown(f"- {f}")
        with col_b:
            st.markdown("#### 🔴 Restricted / At Risk")
            if ac["restricted"]:
                for r in ac["restricted"]:
                    st.markdown(f"- {r}")
            else:
                st.markdown("- *None currently*")

        st.markdown(
            f'<div style="background:#1a1a1a;border-left:3px solid #ff8800;'
            f'padding:10px 14px;border-radius:4px;margin-top:8px">'
            f'<b>📋 Reason / Context:</b><br><span style="color:#ccc">{ac["restriction_reason"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Tab: Country Impact ───────────────────────────────────────────────────
    with tab_impact:
        st.markdown(f"#### If **{selected}** is fully blocked — impact by country:")
        st.markdown("")
        for item in sorted(cp["affected_countries"], key=lambda x: x["score"], reverse=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(
                    f'<div style="padding:6px 0">'
                    f'<b style="font-size:1.05em">{item["country"]}</b><br>'
                    f'{impact_bar(item["score"])}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                color = "#ff3333" if item["score"] >= 80 else "#ff8800" if item["score"] >= 50 else "#ffcc00"
                st.markdown(
                    f'<div style="background:#111;border-left:3px solid {color};'
                    f'padding:8px 12px;border-radius:4px;margin-top:4px">'
                    f'<small>{item["reason"]}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("")

    # ── Tab: News ─────────────────────────────────────────────────────────────
    with tab_news:
        st.markdown(f"#### Latest news — {selected}")
        with st.spinner("Fetching..."):
            news = fetch_news(cp["keywords"])
        if news:
            for item in news:
                src = f' — <span style="color:#888">{item["source"]}</span>' if item["source"] else ""
                pub = f'<span style="color:#555;font-size:0.8em">{item["published"][:25]}</span>'
                st.markdown(
                    f'<div style="background:#111;border:1px solid #282828;padding:10px 14px;'
                    f'border-radius:6px;margin-bottom:8px">'
                    f'<a href="{item["link"]}" target="_blank" style="color:#4da6ff;font-weight:500">'
                    f'{item["title"]}</a>{src}<br>{pub}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No recent news found. Check your internet connection.")
        if st.button("🔄 Refresh", key="refresh"):
            st.cache_data.clear()
            st.rerun()

    # ── Tab: Compare All ──────────────────────────────────────────────────────
    with tab_compare:
        st.markdown("#### All Chokepoints Overview")
        rows = []
        for name, data in CHOKEPOINTS.items():
            sc = STATUS_CONFIG[data["status"]]
            rc = RISK_CONFIG[data["risk"]]
            free_count = len(data["access"]["free"])
            restricted_count = len(data["access"]["restricted"])
            rows.append({
                "Chokepoint": f'{data["icon"]} {name}',
                "Controller": data["controller"],
                "Status": f'{sc["emoji"]} {sc["label"]}',
                "Risk": f'{rc["emoji"]} {data["risk"]}',
                "Oil (Mbbl/d)": data["oil_flow_mbd"],
                "% World Oil": f'{data["pct_global_oil"]}%',
                "% World LNG": f'{data["pct_global_lng"]}%' if data["pct_global_lng"] else "—",
                "Restricted Parties": restricted_count if restricted_count else "None",
                "Top Impacted": data["affected_countries"][0]["country"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### Country Exposure Heatmap (Full Blockage Scenario)")

        all_c = {}
        for name, data in CHOKEPOINTS.items():
            for item in data["affected_countries"]:
                c = item["country"]
                if c not in all_c:
                    all_c[c] = {}
                all_c[c][name] = item["score"]

        mdf = pd.DataFrame(all_c).T.fillna(0)
        mdf["_total"] = mdf.sum(axis=1)
        mdf = mdf.sort_values("_total", ascending=False).drop(columns=["_total"])
        mdf = mdf[[c for c in CHOKEPOINTS.keys() if c in mdf.columns]]

        fig_h = go.Figure(go.Heatmap(
            z=mdf.values,
            x=[f"{CHOKEPOINTS[c]['icon']} {c}" for c in mdf.columns],
            y=mdf.index.tolist(),
            colorscale=[[0, "#0d1421"], [0.25, "#1a2800"], [0.55, "#7a3300"], [1.0, "#ff2200"]],
            text=mdf.values.astype(int),
            texttemplate="%{text}",
            textfont={"size": 9},
            showscale=True,
            colorbar=dict(title="Impact %", tickfont=dict(color="white"), titlefont=dict(color="white")),
        ))
        fig_h.update_layout(
            paper_bgcolor="#0d1421", plot_bgcolor="#0d1421",
            font=dict(color="white"),
            xaxis=dict(tickangle=-35, tickfont=dict(size=8)),
            yaxis=dict(tickfont=dict(size=9)),
            height=520, margin=dict(l=10, r=10, t=10, b=90),
        )
        st.plotly_chart(fig_h, use_container_width=True)

    st.markdown("---")
    st.markdown(
        f'<p style="color:#444;text-align:center;font-size:0.78em">'
        f'Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")} · News via Google News RSS · '
        f'Status based on geopolitical analysis · Impact scores are analytical estimates</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
