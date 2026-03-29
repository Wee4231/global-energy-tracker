"""
Global Energy Chokepoints Monitor
Real-time maritime energy passage tracking with geopolitical access status & AIS vessel overlay.
"""

import streamlit as st
import plotly.graph_objects as go
import feedparser
import pandas as pd
import requests
import re
import asyncio
import json
import threading
import time
import queue
from datetime import datetime

st.set_page_config(
    page_title="Global Energy Chokepoints Monitor",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Status System ─────────────────────────────────────────────────────────────
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
        "bbox": [[24.0, 54.0, 28.0, 59.0]],
        "oil_flow_mbd": 17.0, "daily_vessels": 2100,
        "pct_global_oil": 20, "pct_global_lng": 17,
        "region": "Persian Gulf / Oman",
        "status": "SELECTIVE", "risk": "HIGH",
        "icon": "🛢️",
        "controller": "Iran (de facto) / Oman",
        "description": (
            "World's most critical oil chokepoint. Connects Persian Gulf producers "
            "(Saudi Arabia, UAE, Iraq, Kuwait, Iran, Qatar) to the Indian Ocean. "
            "~20% of global oil + 17% of LNG. Iran regularly seizes vessels linked "
            "to 'enemy' nations while allowing allied/neutral ships to pass freely."
        ),
        "access": {
            "free": ["🇨🇳 China", "🇷🇺 Russia", "🇮🇳 India", "🇵🇰 Pakistan", "Neutral-flag vessels"],
            "restricted": ["🇺🇸 US-affiliated vessels", "🇮🇱 Israeli-linked cargo", "🇬🇧 UK vessels (elevated risk)"],
            "restriction_reason": (
                "Iran seizes/harasses vessels for nuclear negotiations leverage. "
                "2023–2024: 10+ tankers seized or harassed. IRGC Navy uses speedboat swarms. "
                "Chinese + Russian vessels pass without incident by diplomatic arrangement."
            ),
        },
        "keywords": ["Strait of Hormuz", "Iran tanker seizure", "Persian Gulf shipping", "Hormuz blockade"],
        "affected_countries": [
            {"country": "🇯🇵 Japan",           "score": 95, "reason": "87–90% crude from Middle East; strategic reserves ~90 days only; selective access = cost spike even if 'open'"},
            {"country": "🇹🇼 Taiwan",           "score": 92, "reason": "Near-total import dependence; no domestic oil; ~85% from Middle East; TSMC fab energy at existential risk"},
            {"country": "🇰🇷 South Korea",      "score": 88, "reason": "70%+ crude + 40% LNG from Gulf; Ulsan/Yeosu petrochemical hubs paralysed; export economy crippled"},
            {"country": "🇸🇬 Singapore",        "score": 82, "reason": "World's 3rd-largest refining hub; entire crude supply chain disrupted; Jurong Island refinery at risk"},
            {"country": "🇮🇳 India",            "score": 72, "reason": "60%+ crude from Gulf; Reliance Jamnagar calibrated for Gulf crudes; Iran sanctions complicate sourcing"},
            {"country": "🇨🇳 China",            "score": 60, "reason": "~40% crude from Middle East; SPR buffer 90 days; Iran partnership = partial protection under selective regime"},
            {"country": "🇦🇪 UAE",              "score": 55, "reason": "Fujairah transshipment hub; ADCO domestic exports directly at exit of Hormuz; Abu Dhabi oil trapped"},
            {"country": "🇸🇦 Saudi Arabia",     "score": 50, "reason": "~6M bbl/day via Ras Tanura; partial bypass via East-West Pipeline to Yanbu (Red Sea) — limited capacity"},
            {"country": "🇵🇰 Pakistan",         "score": 45, "reason": "80%+ crude imports from Gulf; PARCO/NRL refineries dependent; economic reserves minimal"},
            {"country": "🇧🇩 Bangladesh",       "score": 62, "reason": "All petroleum products imported from Gulf; no strategic reserves; domestic gas cushions power sector slightly but transport + industry collapse within weeks"},
            {"country": "🇶🇦 Qatar",            "score": 85, "reason": "Ras Laffan LNG terminal is INSIDE the Gulf — 100% of LNG export revenue (60%+ of GDP) blocked; world's 3rd-largest LNG exporter goes to zero overnight"},
            {"country": "🇮🇶 Iraq",             "score": 82, "reason": "Basra Oil Terminal = 90% of Iraq's government revenue; all oil exports blocked = immediate state funding collapse; civil services and military pay cease within weeks"},
            {"country": "🇲🇾 Malaysia",         "score": 58, "reason": "~60% crude imports from Middle East; Petronas RAPID refinery (Johor, $27B investment) relies entirely on Gulf feedstock; domestic Sarawak/Sabah output insufficient to cover"},
            {"country": "🇹🇭 Thailand",         "score": 72, "reason": "~70% crude from Middle East; domestic output covers only ~20% of demand; Map Ta Phut industrial complex + Bangkok grid collapse within 2 weeks; no strategic petroleum reserve law enacted"},
            {"country": "🇵🇭 Philippines",      "score": 88, "reason": "ZERO domestic crude production; ~90% imports from Middle East; NO strategic reserve whatsoever; gas station closures already occur during minor supply delays — full Hormuz blockage = nationwide fuel collapse within days"},
            {"country": "🇻🇳 Vietnam",          "score": 55, "reason": "~60% crude from Gulf; Nghi Son + Binh Son refineries calibrated for Middle East crude grades; domestic Bach Ho field declining; no viable short-term substitute crude"},
            {"country": "🇮🇩 Indonesia",        "score": 45, "reason": "Net oil importer since 2004; ~50% crude from Middle East; domestic Pertamina refineries exposed; subsidy program means government absorbs price shock = fiscal crisis"},
            {"country": "🇱🇰 Sri Lanka",        "score": 78, "reason": "100% oil imported; virtually all from Middle East; 2022 economic collapse was partly triggered by fuel shortage — repeat scenario near-guaranteed; zero strategic reserve"},
        ],
    },
    "Strait of Malacca": {
        "lat": 2.5, "lon": 101.5,
        "bbox": [[0.0, 98.0, 5.0, 104.0]],
        "oil_flow_mbd": 16.0, "daily_vessels": 1000,
        "pct_global_oil": 25, "pct_global_lng": 0,
        "region": "Malaysia / Singapore / Indonesia",
        "status": "OPEN", "risk": "MEDIUM",
        "icon": "⚓",
        "controller": "Malaysia, Singapore, Indonesia (joint)",
        "description": (
            "Busiest shipping lane by tonnage — ~25% of global seaborne trade (~1,000 vessels/day). "
            "Currently open to all flags, no political restrictions. Piracy has declined sharply since 2010. "
            "VLCCs cannot transit fully laden — deepest navigable draft is ~25m."
        ),
        "access": {
            "free": ["All nations"],
            "restricted": [],
            "restriction_reason": (
                "No political restrictions. All three littoral states (MY/SG/ID) "
                "depend on open transit for economic growth. Piracy risk low but present near Myanmar coast."
            ),
        },
        "keywords": ["Strait of Malacca", "Malacca shipping", "South China Sea route", "Malacca piracy"],
        "affected_countries": [
            {"country": "🇸🇬 Singapore",        "score": 98, "reason": "Economy entirely built on this lane: port (PSA), bunkering, refining, trade finance — existential if blocked"},
            {"country": "🇨🇳 China",            "score": 92, "reason": "'Malacca Dilemma': ~80% energy imports transit here; Pearl River Delta manufacturing collapses without it"},
            {"country": "🇯🇵 Japan",            "score": 90, "reason": "All Middle East/Africa energy transits here; no viable VLCC alternative route; economy paralysed"},
            {"country": "🇰🇷 South Korea",      "score": 87, "reason": "Ulsan port (world's largest auto-exporter) + Yeosu petrochemical corridor fully dependent"},
            {"country": "🇹🇼 Taiwan",           "score": 85, "reason": "TSMC semiconductor fabs + entire energy supply chain depend on uninterrupted Malacca transit"},
            {"country": "🇲🇾 Malaysia",         "score": 75, "reason": "Port Klang + Penang port revenues collapse; Petronas refinery crude inputs disrupted; Ringgit crisis"},
            {"country": "🇹🇭 Thailand",         "score": 60, "reason": "Map Ta Phut petrochemical complex loses feedstock; Gulf of Thailand oil can offset only partially"},
            {"country": "🇻🇳 Vietnam",          "score": 55, "reason": "Hai Phong + HCMC ports disrupted; manufacturing exports (Samsung, Intel) face weeks-long delays"},
            {"country": "🇵🇭 Philippines",      "score": 52, "reason": "All oil imports transit Malacca or SCS; no strategic reserves; Luzon power grid at risk within days"},
            {"country": "🇦🇺 Australia",        "score": 55, "reason": "Iron ore + LNG + coal exports to NE Asia disrupted; ~45% of export revenue at risk"},
            {"country": "🇮🇩 Indonesia",        "score": 28, "reason": "Controls strait; coal/palm oil can reroute via Sunda/Lombok; but refined fuel imports disrupted"},
            {"country": "🇮🇳 India",            "score": 25, "reason": "Eastern port exports disrupted; western crude imports less exposed vs Hormuz"},
        ],
    },
    "Suez Canal": {
        "lat": 30.5, "lon": 32.3,
        "bbox": [[29.5, 31.8, 31.5, 33.0]],
        "oil_flow_mbd": 5.5, "daily_vessels": 52,
        "pct_global_oil": 9, "pct_global_lng": 8,
        "region": "Egypt",
        "status": "OPEN", "risk": "MEDIUM",
        "icon": "🚢",
        "controller": "Egypt (Suez Canal Authority)",
        "description": (
            "Critical shortcut between Mediterranean and Red Sea. ~9% oil + 8% LNG globally. "
            "Open to all commercial flags. Egypt earns ~$9–10B/year (2% GDP) — strong incentive "
            "to keep it open. Closure = +14 days via Cape of Good Hope."
        ),
        "access": {
            "free": ["All commercial vessels", "All national flags"],
            "restricted": ["🇮🇱 Israeli military vessels (Egypt reserves right under 1979 treaty)"],
            "restriction_reason": (
                "Commercial shipping universally open under international law. "
                "Egypt restricted to Israeli warships in 1967 war era; "
                "post-1979 peace treaty normalised but Egypt maintains discretion over military vessels."
            ),
        },
        "keywords": ["Suez Canal", "Egypt shipping", "Red Sea reroute", "Suez Canal traffic"],
        "affected_countries": [
            {"country": "🇪🇬 Egypt",            "score": 92, "reason": "Canal ~$10B/year revenue (2% GDP) + foreign currency lifeline; closure = immediate IMF crisis"},
            {"country": "🇮🇱 Israel",           "score": 75, "reason": "All Asia sea access via Suez or +3 weeks; Eilat port (Red Sea) becomes only viable alternative exit"},
            {"country": "🇮🇹 Italy",            "score": 65, "reason": "Mediterranean gateway; Middle East energy + Asian goods rerouted; Augusta/Taranto refinery inputs delayed"},
            {"country": "🇩🇪 Germany",          "score": 58, "reason": "Largest EU manufacturer; Asian component supply chains (China/Vietnam/Thailand) +2–3 weeks = factory slowdowns"},
            {"country": "🇳🇱 Netherlands",      "score": 58, "reason": "Rotterdam = Europe's main port; ARA hub throughput drops 30%+; European supply chain head disrupted"},
            {"country": "🇫🇷 France",           "score": 50, "reason": "Marseille + Le Havre ports disrupted; Total/TotalEnergies Middle East crude rerouted"},
            {"country": "🇬🇧 UK",               "score": 45, "reason": "Asian goods + energy imports rerouted via Cape; freight cost surge drives double-digit inflation"},
            {"country": "🇪🇸 Spain",            "score": 42, "reason": "Algeciras (3rd busiest EU port) traffic drops; Mediterranean trade hub status threatened"},
            {"country": "🇮🇳 India",            "score": 40, "reason": "Pharma + textile exports to EU rerouted via Cape — weeks of delay; JNPT/Nhava Sheva backed up"},
            {"country": "🇨🇳 China",            "score": 35, "reason": "EU-bound BRI goods +2 weeks; Yiwu–Madrid rail (trans-Siberian) gains but can't absorb full volume"},
            {"country": "🇯🇴 Jordan",           "score": 30, "reason": "Aqaba port (Jordan's only sea access) indirectly disrupted; Red Sea trade corridor collapses"},
            {"country": "🇸🇦 Saudi Arabia",     "score": 25, "reason": "Yanbu Red Sea oil exports partially affected; Egypt revenue loss destabilises regional partner"},
            {"country": "🇯🇵 Japan",            "score": 40, "reason": "Middle East energy imports via Suez add +14 days if rerouted; freight costs spike for all manufactured goods"},
            {"country": "🇰🇷 South Korea",      "score": 38, "reason": "Europe-bound auto/electronics exports + energy imports both rerouted; Hyundai/Samsung logistics extended"},
            {"country": "🇸🇬 Singapore",        "score": 35, "reason": "PSA port transshipment volumes drop as Europe-Asia route extends; bunkering demand shifts"},
            {"country": "🇲🇾 Malaysia",         "score": 28, "reason": "Palm oil + electronics exports to Europe rerouted; Port Klang throughput drops; freight margins collapse"},
        ],
    },
    "Bab-el-Mandeb Strait": {
        "lat": 12.6, "lon": 43.3,
        "bbox": [[11.0, 42.0, 14.5, 46.0]],
        "oil_flow_mbd": 3.8, "daily_vessels": 40,
        "pct_global_oil": 6, "pct_global_lng": 4,
        "region": "Yemen / Djibouti / Eritrea",
        "status": "HOSTILE_TARGETED", "risk": "VERY HIGH",
        "icon": "⚠️",
        "controller": "Houthi Movement (de facto Yemen coast)",
        "description": (
            "Southern Red Sea gateway. Since Oct 2023, Houthis launched 300+ attacks. "
            "SELECTIVE by design — US/UK/Israeli-linked ships targeted; Chinese + Russian vessels "
            "pass freely by agreement. 80%+ of major container lines rerouted via Cape of Good Hope."
        ),
        "access": {
            "free": ["🇨🇳 Chinese-flagged vessels", "🇷🇺 Russian-flagged vessels", "🇮🇷 Iranian vessels", "Non-US/UK/IL-linked ships"],
            "restricted": ["🇺🇸 US-affiliated ships", "🇬🇧 UK-linked vessels", "🇮🇱 Israeli cargo or port-of-call history"],
            "restriction_reason": (
                "Houthis explicitly exempted Chinese + Russian ships (diplomatic arrangement with Iran). "
                "MSC, Maersk, CMA CGM, Hapag-Lloyd suspended Red Sea service Dec 2023. "
                "Operation Prosperity Guardian (US/UK) escorts provide limited protection only."
            ),
        },
        "keywords": ["Bab el Mandeb", "Houthi attack Red Sea", "Red Sea shipping attack", "Yemen Houthi drone ship"],
        "affected_countries": [
            {"country": "🇩🇯 Djibouti",         "score": 95, "reason": "Port of Djibouti = 95% GDP; Horn of Africa trade hub existential threat; transit revenue collapsed 60%+"},
            {"country": "🇾🇪 Yemen",             "score": 90, "reason": "Humanitarian aid shipments blocked; Houthis control but civilian population starves without inflows"},
            {"country": "🇪🇬 Egypt",             "score": 85, "reason": "Suez Canal revenue fell 50%+ due to Bab-el-Mandeb rerouting; FX reserves crisis accelerating"},
            {"country": "🇪🇹 Ethiopia",          "score": 75, "reason": "Landlocked; all sea access via Djibouti; food + fuel imports blocked = humanitarian catastrophe"},
            {"country": "🇸🇴 Somalia",           "score": 65, "reason": "Berbera + Mogadishu port traffic collapses; aid shipments blocked; food security emergency"},
            {"country": "🇮🇱 Israel",            "score": 60, "reason": "Eilat port effectively closed by Houthi threat since Oct 2023; 90%+ drop in Eilat cargo volume"},
            {"country": "🇸🇦 Saudi Arabia",      "score": 52, "reason": "Yanbu terminal Red Sea exports at risk; conflict next door threatens Aramco operations"},
            {"country": "🇪🇺 EU",                "score": 60, "reason": "40% Asian goods + 30% energy rerouted via Cape; freight costs x3; visible inflation pressure"},
            {"country": "🇮🇳 India",             "score": 38, "reason": "Europe-bound pharma/textile exports rerouted; Indian Navy conducting active escort operations"},
            {"country": "🇬🇧 UK",                "score": 35, "reason": "UK-flagged vessels actively targeted; Red Sea shipping costs up 300%; Royal Navy engaged in defence"},
            {"country": "🇺🇸 USA",               "score": 30, "reason": "Military costs of Operation Prosperity Guardian; LNG export value chain disrupted via Red Sea"},
            {"country": "🇨🇳 China",             "score": 12, "reason": "Chinese vessels pass freely per Houthi agreement; BRI port investments (Djibouti) partially insulated"},
            {"country": "🇯🇵 Japan",             "score": 45, "reason": "Middle East LNG + crude rerouted via Cape; +14 days = energy cost spike; Toyota/Sony supply chains extended"},
            {"country": "🇰🇷 South Korea",       "score": 42, "reason": "Middle East crude + Europe exports both hit; Hyundai Heavy Industries (shipbuilder) orders drop"},
            {"country": "🇸🇬 Singapore",         "score": 38, "reason": "PSA hub loses Europe-Asia transshipment volume; MAS shipping finance sector impacted"},
            {"country": "🇹🇭 Thailand",          "score": 30, "reason": "Europe-bound electronics + auto parts exports rerouted; freight surcharge adds 15–20% to export costs"},
            {"country": "🇻🇳 Vietnam",           "score": 28, "reason": "Samsung/LG factory export routes to Europe extended by weeks; competitiveness vs nearshore rivals drops"},
        ],
    },
    "Turkish Straits (Bosphorus)": {
        "lat": 41.1, "lon": 29.0,
        "bbox": [[40.5, 28.5, 41.5, 29.8]],
        "oil_flow_mbd": 2.4, "daily_vessels": 130,
        "pct_global_oil": 3, "pct_global_lng": 0,
        "region": "Turkey",
        "status": "SELECTIVE", "risk": "MEDIUM",
        "icon": "🌊",
        "controller": "Turkey (1936 Montreux Convention)",
        "description": (
            "Only sea passage from Black Sea to Mediterranean. Turkey closed to warships "
            "of belligerent nations since Feb 2022 (Russia-Ukraine). Commercial shipping — "
            "including Russian/Kazakh oil tankers — continues normally."
        ),
        "access": {
            "free": ["All commercial vessels", "Non-Black Sea warships in peacetime"],
            "restricted": ["🇷🇺 Russian Navy warships (since Feb 2022)", "All belligerent warships (Montreux Art.19)"],
            "restriction_reason": (
                "Turkey closed to Russian Navy warships citing Montreux Convention wartime provisions — "
                "Russian Black Sea Fleet is effectively trapped. Commercial oil tankers (including Russia/Kazakhstan) "
                "continue to transit freely; Turkey avoids secondary sanctions risk."
            ),
        },
        "keywords": ["Bosphorus Strait", "Turkish Straits Montreux", "Black Sea oil export", "Russia tanker Bosphorus"],
        "affected_countries": [
            {"country": "🇷🇺 Russia",            "score": 68, "reason": "Black Sea Fleet locked in — can't reinforce Mediterranean; Baltic terminals absorb more oil load"},
            {"country": "🇰🇿 Kazakhstan",        "score": 65, "reason": "CPC pipeline ~1.5M bbl/day via Novorossiysk — only viable export route; closure = total revenue loss"},
            {"country": "🇺🇦 Ukraine",           "score": 60, "reason": "Russian fleet trapped = strategic benefit; but Odessa grain corridor still under Russian naval blockade threat"},
            {"country": "🇧🇬 Bulgaria",          "score": 52, "reason": "Burgas port Black Sea tanker traffic; historically high Russian crude dependency; refinery supply crisis"},
            {"country": "🇷🇴 Romania",           "score": 40, "reason": "Neptune Deep Black Sea gas project export blocked if full closure; Constanta port traffic drops 40%"},
            {"country": "🇬🇷 Greece",            "score": 35, "reason": "Thessaloniki port + Greek shipping companies (world's largest fleet) lose Black Sea route revenue"},
            {"country": "🇹🇷 Turkey",            "score": 30, "reason": "Transit toll revenue loss; but Turkey gains geopolitical leverage + energy discount deals with Russia"},
            {"country": "🇦🇿 Azerbaijan",        "score": 15, "reason": "BTC pipeline exports to Ceyhan (Mediterranean) bypass Bosphorus entirely — well insulated"},
        ],
    },
    "Panama Canal": {
        "lat": 9.1, "lon": -79.7,
        "bbox": [[8.0, -80.5, 10.5, -78.5]],
        "oil_flow_mbd": 1.0, "daily_vessels": 36,
        "pct_global_oil": 2, "pct_global_lng": 7,
        "region": "Panama",
        "status": "RESTRICTED", "risk": "MEDIUM",
        "icon": "🌧️",
        "controller": "Panama Canal Authority",
        "description": (
            "Critical for US LNG exports to Asia (~7% global LNG) and Pacific-Atlantic trade. "
            "Current restriction is CLIMATE-DRIVEN — El Niño drought cut daily transits from 36 to 22 vessels. "
            "Politically neutral: all flags equally affected. Cape Horn adds +21 days."
        ),
        "access": {
            "free": ["All nations (politically)"],
            "restricted": ["All large vessels (physically — water depth limits Neopanamax draft)"],
            "restriction_reason": (
                "Not geopolitical — Gatun Lake hit record low levels due to El Niño 2023–24. "
                "LNG tankers and VLCCs forced to reduce load or queue 6+ weeks. "
                "Expected to normalise with rainfall recovery but climate risk is structural long-term."
            ),
        },
        "keywords": ["Panama Canal drought", "Panama Canal restriction", "LNG tanker Panama delay", "Canal water level"],
        "affected_countries": [
            {"country": "🇵🇦 Panama",            "score": 92, "reason": "Canal = 6% direct GDP + services multiplier; toll revenue fell $200M+ during drought; existential climate risk"},
            {"country": "🇺🇸 USA",               "score": 55, "reason": "LNG export revenue at risk; East/West Coast shipping efficiency lost; Pacific military logistics extended"},
            {"country": "🇯🇵 Japan",             "score": 52, "reason": "US LNG (~20–25% of imports) rerouted via Cape Horn; spot market LNG prices spike sharply"},
            {"country": "🇰🇷 South Korea",       "score": 48, "reason": "US LNG contracts delayed; forced to buy expensive spot cargoes from Qatar/Australia at premium"},
            {"country": "🇨🇳 China",             "score": 35, "reason": "US agricultural imports (soy/corn) rerouted; LNG from alternative suppliers costlier on spot"},
            {"country": "🇨🇱 Chile",             "score": 32, "reason": "Copper + lithium exports to Atlantic markets rerouted; freight cost surge cuts export margins 15%+"},
            {"country": "🇵🇪 Peru",              "score": 28, "reason": "Copper + fishmeal Atlantic exports rerouted; Callao port volumes drop as freight economics worsen"},
            {"country": "🇦🇷 Argentina",         "score": 22, "reason": "Soy/beef exports to Asia rerouted via Cape; geographic position makes Cape Horn still viable but costly"},
            {"country": "🇨🇴 Colombia",          "score": 18, "reason": "Coal + banana exports to both oceans partially disrupted; Cartagena transshipment hub volumes fall"},
            {"country": "🇹🇼 Taiwan",            "score": 20, "reason": "US military logistics to Pacific impacted; Taiwan Strait remains primary strategic concern above Panama"},
        ],
    },
    "Danish Straits": {
        "lat": 55.8, "lon": 12.0,
        "bbox": [[54.5, 10.0, 57.5, 13.5]],
        "oil_flow_mbd": 1.5, "daily_vessels": 200,
        "pct_global_oil": 2, "pct_global_lng": 3,
        "region": "Denmark / Sweden",
        "status": "OPEN", "risk": "LOW",
        "icon": "🧊",
        "controller": "Denmark (Øresund / Great Belt authority)",
        "description": (
            "Baltic Sea gateway to global markets. Russian Baltic terminals (Primorsk ~1.5M bbl/day, "
            "Ust-Luga) depend on this passage. Formally open to all, but NATO pressure on Denmark "
            "to restrict Russian 'shadow fleet' tankers is increasing."
        ),
        "access": {
            "free": ["All commercial vessels (formally)"],
            "restricted": ["🇷🇺 Russian Navy (NATO political pressure, not formal closure)"],
            "restriction_reason": (
                "No formal closure. Denmark has declined to restrict Russian oil tanker transit "
                "citing international law (UNCLOS). 'Shadow fleet' of 600+ uninsured Russian tankers "
                "regularly transit. EU and NATO pushing for legal mechanism to restrict them."
            ),
        },
        "keywords": ["Danish Straits", "Baltic Sea shipping", "Russia oil Baltic", "shadow fleet Baltic", "Primorsk terminal"],
        "affected_countries": [
            {"country": "🇫🇮 Finland",           "score": 78, "reason": "All seaborne trade exits Baltic; Helsinki Vuosaari port = economic artery; no overland alternative to global markets"},
            {"country": "🇱🇹 Lithuania",         "score": 72, "reason": "Klaipeda LNG terminal (Baltic's only LNG import terminal) access blocked = gas security eliminated"},
            {"country": "🇪🇪 Estonia",           "score": 68, "reason": "Tallinn port = 35% of GDP; Muuga Oil Terminal transit revenue collapses; digital economy can't substitute"},
            {"country": "🇱🇻 Latvia",            "score": 65, "reason": "Riga port; Ventspils oil terminal historically critical; remaining hydrocarbon flows blocked"},
            {"country": "🇸🇪 Sweden",            "score": 58, "reason": "Gothenburg (Volvo) + Stockholm ports disrupted; Ericsson/SKF component exports stall in Baltic"},
            {"country": "🇵🇱 Poland",            "score": 45, "reason": "Gdansk Lotos refinery + Swinoujscie LNG terminal both directly Baltic-dependent — strategic assets at risk"},
            {"country": "🇷🇺 Russia",            "score": 42, "reason": "Primorsk + Ust-Luga = primary sanctions-evading export route; closure = major oil revenue collapse"},
            {"country": "🇩🇪 Germany",           "score": 22, "reason": "Kiel Canal + North Sea alternative; Rostock port disrupted but Hamburg/Bremen remain via North Sea"},
        ],
    },
    "Lombok Strait": {
        "lat": -8.7, "lon": 115.7,
        "bbox": [[-10.0, 114.5, -7.5, 117.0]],
        "oil_flow_mbd": 2.5, "daily_vessels": 180,
        "pct_global_oil": 4, "pct_global_lng": 0,
        "region": "Indonesia (Bali / Lombok)",
        "status": "OPEN", "risk": "LOW",
        "icon": "🌴",
        "controller": "Indonesia",
        "description": (
            "Deep-water VLCC fallback when Malacca is congested or blocked. "
            "Wide enough for fully laden VLCCs (Malacca cannot). +2–3 days vs Malacca. "
            "No political restrictions. Becomes critical if Malacca is disrupted."
        ),
        "access": {
            "free": ["All nations"],
            "restricted": [],
            "restriction_reason": (
                "No restrictions. Indonesia guarantees transit passage under UNCLOS archipelagic sea lane rights. "
                "Cannot absorb full Malacca volume — handles large tankers only; "
                "smaller bulk/container ships use Sunda Strait."
            ),
        },
        "keywords": ["Lombok Strait", "Indonesia VLCC tanker", "Sunda Strait", "Malacca alternative route"],
        "affected_countries": [
            {"country": "🇨🇳 China",            "score": 32, "reason": "Fallback route for VLCCs if Malacca blocked; closure = no deep-water Pacific alternative for full-laden tankers"},
            {"country": "🇯🇵 Japan",            "score": 28, "reason": "VLCCs already use Lombok; blockage = zero deep-water Pacific alternative for fully laden crude carriers"},
            {"country": "🇦🇺 Australia",        "score": 25, "reason": "LNG tankers (Woodside/INPEX/Chevron) to NE Asia route transits here; export revenue directly at risk"},
            {"country": "🇰🇷 South Korea",      "score": 20, "reason": "VLCC crude imports from Middle East via Lombok if Malacca full; alternate reroute adds cost + time"},
            {"country": "🇮🇩 Indonesia",        "score": 18, "reason": "Territorial waters sovereignty issue; Bali/Lombok tourism + Pertamina logistics secondarily affected"},
        ],
    },
}

# ── AIS Vessel Fetching ───────────────────────────────────────────────────────
def get_aisstream_key() -> str | None:
    try:
        return st.secrets.get("AISSTREAM_API_KEY")
    except Exception:
        import os
        return os.environ.get("AISSTREAM_API_KEY")

def _fetch_ais_ws(api_key: str, bbox: list, timeout: int = 12) -> tuple:
    """Fetch AIS vessels via WebSocket. Returns (vessels_list, error_str)."""
    import queue as _queue
    result_q = _queue.Queue()

    def _run():
        async def _inner():
            vessels = []
            error = ""
            msgs_received = 0
            try:
                import websockets
                async with websockets.connect(
                    "wss://stream.aisstream.io/v0/stream",
                    open_timeout=10,
                    ping_timeout=None,
                ) as ws:
                    # aisstream.io format: [[[lat_min, lon_min], [lat_max, lon_max]], ...]
                    formatted_bbox = [[[b[0], b[1]], [b[2], b[3]]] for b in bbox]
                    await ws.send(json.dumps({
                        "APIkey": api_key,
                        "BoundingBoxes": formatted_bbox,
                        # No FilterMessageTypes — accept all to diagnose
                    }))
                    deadline = time.time() + timeout
                    while time.time() < deadline:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
                            msgs_received += 1
                            try:
                                msg = json.loads(raw)
                            except Exception:
                                error = f"json_err:{raw[:80]}"
                                continue
                            # Check for API error response
                            if "Error" in msg or "error" in msg:
                                error = f"api_err:{msg.get('Error', msg.get('error', raw[:80]))}"
                                break
                            msg_type = msg.get("MessageType", "")
                            pos = msg.get("Message", {}).get("PositionReport", {})
                            meta = msg.get("MetaData", {})
                            lat = pos.get("Latitude")
                            lon = pos.get("Longitude")
                            if lat and lon and abs(lat) < 90 and abs(lon) < 180:
                                vessels.append({
                                    "lat": lat, "lon": lon,
                                    "name": meta.get("ShipName", "Unknown").strip() or "Unknown",
                                    "mmsi": meta.get("MMSI", ""),
                                    "speed": round(pos.get("Sog", 0), 1),
                                    "course": round(pos.get("Cog", 0), 0),
                                })
                        except asyncio.TimeoutError:
                            continue  # no message in 3s window, keep waiting
                        except Exception as e:
                            error = f"recv:{e}"
                            break
            except Exception as e:
                error = f"connect:{e}"
            if not error and msgs_received == 0:
                error = "connected_ok_but_0_msgs_in_12s — bbox may be empty or key has no coverage"
            elif not error and not vessels:
                error = f"connected_ok,{msgs_received}_msgs,no_position_data"
            return vessels, error

        loop = asyncio.new_event_loop()
        try:
            result_q.put(loop.run_until_complete(_inner()))
        finally:
            loop.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout + 8)
    try:
        return result_q.get_nowait()
    except Exception:
        return [], "thread timeout"

@st.cache_data(ttl=120)
def fetch_vessels(api_key: str, bbox_key: str, bbox: list) -> tuple:
    return _fetch_ais_ws(api_key, bbox)

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
def build_map(selected: str, vessels: list = None) -> go.Figure:
    fig = go.Figure()

    # Vessel layer
    if vessels:
        vlats = [v["lat"] for v in vessels]
        vlons = [v["lon"] for v in vessels]
        vtexts = [
            f"<b>{v['name']}</b><br>MMSI: {v['mmsi']}<br>Speed: {v['speed']:.1f} kn<br>Course: {v['course']:.0f}°"
            for v in vessels
        ]
        fig.add_trace(go.Scattergeo(
            lat=vlats, lon=vlons,
            mode="markers",
            marker=dict(size=5, color="#00ffff", symbol="triangle-up", opacity=0.75,
                        line=dict(width=0.5, color="#006688")),
            hovertext=vtexts,
            hoverinfo="text",
            name=f"Vessels ({len(vessels)})",
        ))

    # Chokepoint markers
    for name, cp in CHOKEPOINTS.items():
        sc = STATUS_CONFIG[cp["status"]]
        rc = RISK_CONFIG[cp["risk"]]
        is_sel = name == selected
        fig.add_trace(go.Scattergeo(
            lat=[cp["lat"]], lon=[cp["lon"]],
            mode="markers+text",
            marker=dict(
                size=28 if is_sel else 18,
                color=sc["color"],
                symbol="circle",
                line=dict(width=3 if is_sel else 1.5, color="white"),
                opacity=1.0,
            ),
            text=[cp["icon"]],
            textposition="middle center",
            textfont=dict(size=14),
            hovertext=(
                f"<b>{name}</b><br>"
                f"Controller: {cp['controller']}<br>"
                f"Status: {sc['emoji']} {sc['label']}<br>"
                f"Risk: {rc['emoji']} {cp['risk']}<br>"
                f"Oil: {cp['oil_flow_mbd']}M bbl/d ({cp['pct_global_oil']}% world)<br>"
                f"~{cp['daily_vessels']:,} vessels/day"
            ),
            hoverinfo="text",
            name=name,
            showlegend=False,
        ))

    # Labels
    fig.add_trace(go.Scattergeo(
        lat=[cp["lat"] + 3.2 for cp in CHOKEPOINTS.values()],
        lon=[cp["lon"] for cp in CHOKEPOINTS.values()],
        mode="text",
        text=list(CHOKEPOINTS.keys()),
        textfont=dict(size=8, color="rgba(210,220,255,0.75)"),
        hoverinfo="skip", showlegend=False,
    ))

    fig.update_layout(
        geo=dict(
            showland=True, landcolor="#1a2332",
            showocean=True, oceancolor="#0d1421",
            showcoastlines=True, coastlinecolor="#2a3a4a",
            showcountries=True, countrycolor="#1e2e3e",
            showframe=False,
            projection_type="natural earth",
            bgcolor="#0d1421",
        ),
        paper_bgcolor="#0d1421",
        margin=dict(l=0, r=0, t=0, b=0),
        height=480,
        legend=dict(
            bgcolor="#111",
            bordercolor="#333",
            font=dict(color="white", size=10),
            x=0.01, y=0.01,
        ),
    )
    return fig

# ── UI Helpers ────────────────────────────────────────────────────────────────
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
           f'<span style="color:#2a2a2a">{"░" * (10 - filled)}</span>')
    return f'{bar} <b style="color:{color}">{score}%</b>'

def render_legend():
    items = [
        ("🟢", "OPEN",             "All nations transit freely"),
        ("🔵", "SELECTIVE",        "Controller restricts specific nations"),
        ("🟠", "HOSTILE-TARGETED", "Active attacks on specific flags; others safe"),
        ("🟡", "RESTRICTED",       "Capacity reduced (non-political)"),
        ("🔴", "CLOSED",           "Full blockade / shutdown"),
        ("🔵 dot", "AIS Vessel",   "Real-time ship position (if API key set)"),
    ]
    html = '<div style="background:#111;border:1px solid #282828;border-radius:8px;padding:12px 16px;font-size:0.8em">'
    html += '<b style="color:#bbb">Status Legend</b><br><br>'
    for emoji, label, desc in items:
        html += f'<span style="font-size:0.9em">{emoji}</span> <b>{label}</b><br><span style="color:#777;font-size:0.9em">&nbsp;&nbsp;{desc}</span><br>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.markdown("""
    <div style="text-align:center;padding:8px 0 2px 0">
        <h1 style="color:#ff8800;margin:0;font-size:1.8em">🛢️ Global Energy Chokepoints Monitor</h1>
        <p style="color:#777;margin:3px 0;font-size:0.88em">
            Geopolitical access status · Real-time AIS vessels · Country impact analysis
        </p>
    </div>
    """, unsafe_allow_html=True)

    # KPI bar
    statuses = [cp["status"] for cp in CHOKEPOINTS.values()]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Chokepoints", len(CHOKEPOINTS))
    c2.metric("🟢 Open",             statuses.count("OPEN"))
    c3.metric("🔵 Selective",        statuses.count("SELECTIVE"))
    c4.metric("🟠 Hostile-Targeted", statuses.count("HOSTILE_TARGETED"))
    c5.metric("🟡 Restricted",       statuses.count("RESTRICTED"))
    c6.metric("🔴 Closed",           statuses.count("CLOSED"))
    st.divider()

    col_map, col_side = st.columns([3, 1])

    with col_side:
        st.markdown("### 🗺️ Chokepoint")
        selected = st.radio(
            "select", list(CHOKEPOINTS.keys()),
            format_func=lambda x: f"{CHOKEPOINTS[x]['icon']} {x}",
            label_visibility="collapsed",
        )
        cp = CHOKEPOINTS[selected]
        st.markdown("---")
        st.markdown(f"**Status:** {status_badge(cp['status'])}", unsafe_allow_html=True)
        st.markdown(f"**Risk:** {risk_badge(cp['risk'])}", unsafe_allow_html=True)
        st.markdown(f"**Controller:** `{cp['controller']}`")
        st.markdown(f"**Oil:** {cp['oil_flow_mbd']}M bbl/d ({cp['pct_global_oil']}% global)")
        if cp["pct_global_lng"]:
            st.markdown(f"**LNG:** {cp['pct_global_lng']}% global")
        st.markdown(f"**Traffic:** ~{cp['daily_vessels']:,} vessels/day")
        st.markdown("---")
        render_legend()

    # AIS vessels
    api_key = get_aisstream_key()
    vessels = []
    ais_error = ""
    if api_key:
        with st.spinner(f"Fetching live AIS vessels near {selected}..."):
            vessels, ais_error = fetch_vessels(api_key, selected, cp["bbox"])

    with col_map:
        fig = build_map(selected, vessels if vessels else None)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        if api_key and vessels:
            st.caption(
                f"🔵 {len(vessels)} vessels live near {selected} (AIS · updates every 2 min) — "
                f"Each dot = a real ship broadcasting its position via AIS (Automatic Identification System). "
                f"All commercial vessels >300 tons are legally required to transmit. "
                f"Military ships & sanctioned tankers may disable AIS to stay hidden."
            )
        elif api_key:
            detail = f" ({ais_error})" if ais_error else ""
            st.caption(f"⚠️ No AIS data received{detail}")
        else:
            st.caption("💡 Add `AISSTREAM_API_KEY` to Streamlit secrets to enable live vessel tracking")

    # Detail section
    st.markdown(f"## {cp['icon']} {selected}")
    st.markdown(f"*{cp['description']}*")

    tab_access, tab_impact, tab_news, tab_compare = st.tabs(
        ["🔐 Access Control", "🌍 Country Impact", "📰 News", "📊 Compare All"]
    )

    # ── Access Control ────────────────────────────────────────────────────────
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
                st.markdown("- *No current restrictions*")
        st.markdown(
            f'<div style="background:#161616;border-left:3px solid #ff8800;'
            f'padding:10px 14px;border-radius:4px;margin-top:10px">'
            f'<b style="color:#ff8800">📋 Reason / Context</b><br>'
            f'<span style="color:#bbb">{ac["restriction_reason"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Country Impact ────────────────────────────────────────────────────────
    with tab_impact:
        st.markdown(f"#### Full blockage of **{selected}** — country impact ranking:")
        st.markdown("")
        for item in sorted(cp["affected_countries"], key=lambda x: x["score"], reverse=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(
                    f'<div style="padding:5px 0">'
                    f'<b style="font-size:1.0em">{item["country"]}</b><br>'
                    f'{impact_bar(item["score"])}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                color = "#ff3333" if item["score"] >= 80 else "#ff8800" if item["score"] >= 50 else "#ffcc00"
                st.markdown(
                    f'<div style="background:#0f0f0f;border-left:3px solid {color};'
                    f'padding:8px 12px;border-radius:4px;margin-top:3px">'
                    f'<small style="color:#ccc">{item["reason"]}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("")

    # ── News ──────────────────────────────────────────────────────────────────
    with tab_news:
        st.markdown(f"#### Latest news — {selected}")
        with st.spinner("Fetching..."):
            news = fetch_news(cp["keywords"])
        if news:
            for item in news:
                src = f' — <span style="color:#777">{item["source"]}</span>' if item["source"] else ""
                pub = f'<span style="color:#444;font-size:0.78em">{item["published"][:25]}</span>'
                st.markdown(
                    f'<div style="background:#0f0f0f;border:1px solid #222;padding:10px 14px;'
                    f'border-radius:6px;margin-bottom:8px">'
                    f'<a href="{item["link"]}" target="_blank" style="color:#4da6ff;font-weight:500">'
                    f'{item["title"]}</a>{src}<br>{pub}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No recent news found.")
        if st.button("🔄 Refresh", key="refresh"):
            st.cache_data.clear()
            st.rerun()

    # ── Compare All ───────────────────────────────────────────────────────────
    with tab_compare:
        st.markdown("#### All Chokepoints")
        rows = []
        for name, data in CHOKEPOINTS.items():
            sc = STATUS_CONFIG[data["status"]]
            rc = RISK_CONFIG[data["risk"]]
            restricted = ", ".join(data["access"]["restricted"]) if data["access"]["restricted"] else "None"
            rows.append({
                "Chokepoint":        f'{data["icon"]} {name}',
                "Controller":        data["controller"],
                "Status":            f'{sc["emoji"]} {sc["label"]}',
                "Risk":              f'{rc["emoji"]} {data["risk"]}',
                "Oil (Mbbl/d)":      data["oil_flow_mbd"],
                "% World Oil":       f'{data["pct_global_oil"]}%',
                "% World LNG":       f'{data["pct_global_lng"]}%' if data["pct_global_lng"] else "—",
                "Vessels/day":       f'~{data["daily_vessels"]:,}',
                "Restricted To":     restricted,
                "Most Impacted (≥70%)": ", ".join(
                    item["country"] for item in sorted(data["affected_countries"], key=lambda x: x["score"], reverse=True)
                    if item["score"] >= 70
                ) or data["affected_countries"][0]["country"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Heatmap
        st.markdown("---")
        st.markdown("#### Country Exposure Heatmap — Full Blockage Scenario")
        st.caption("Shows impact score (0–100%) per country × chokepoint. Only countries with known exposure shown.")

        all_c: dict = {}
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

        # Short labels for x-axis
        short_labels = {
            "Strait of Hormuz":          "🛢️ Hormuz",
            "Strait of Malacca":         "⚓ Malacca",
            "Suez Canal":                "🚢 Suez",
            "Bab-el-Mandeb Strait":      "⚠️ Bab-el-M.",
            "Turkish Straits (Bosphorus)": "🌊 Bosphorus",
            "Panama Canal":              "🌧️ Panama",
            "Danish Straits":            "🧊 Danish",
            "Lombok Strait":             "🌴 Lombok",
        }

        fig_h = go.Figure(go.Heatmap(
            z=mdf.values,
            x=[short_labels.get(c, c) for c in mdf.columns],
            y=mdf.index.tolist(),
            colorscale=[[0, "#0d1421"], [0.2, "#1a2800"], [0.55, "#7a3300"], [1.0, "#ff2200"]],
            text=mdf.values.astype(int),
            texttemplate="%{text}",
            textfont={"size": 10, "color": "white"},
            showscale=True,
            zmin=0, zmax=100,
            colorbar=dict(
                title=dict(text="Impact %", font=dict(color="white", size=11)),
                tickfont=dict(color="white", size=10),
                len=0.9,
            ),
        ))
        fig_h.update_layout(
            paper_bgcolor="#0d1421", plot_bgcolor="#0d1421",
            font=dict(color="white"),
            xaxis=dict(tickangle=-30, tickfont=dict(size=11), side="bottom", gridcolor="#1a2332"),
            yaxis=dict(tickfont=dict(size=10), gridcolor="#1a2332", autorange="reversed"),
            height=max(400, len(mdf) * 26 + 100),
            margin=dict(l=10, r=20, t=20, b=80),
        )
        st.plotly_chart(fig_h, use_container_width=True)

    st.markdown("---")
    st.markdown(
        f'<p style="color:#333;text-align:center;font-size:0.75em">'
        f'Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")} · '
        f'AIS via aisstream.io · News via Google News RSS · '
        f'Status based on geopolitical analysis · Impact scores are analytical estimates</p>',
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
