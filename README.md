# 🛢️ Global Energy Chokepoints Monitor

An interactive dashboard tracking the world's critical maritime energy passages — their **geopolitical access status**, which countries are restricted, and which nations are most exposed if a chokepoint is blocked.

## Live Demo

> Deploy free on [Streamlit Community Cloud](https://streamlit.io/cloud) by forking this repo.

## Features

- **Interactive world map** — 8 chokepoints plotted with real-time status colours
- **5-tier status system** — goes beyond simple Open/Closed:
  - 🟢 **OPEN** — All nations transit freely
  - 🔵 **SELECTIVE** — Open in name; controller restricts specific nations (e.g. Hormuz under Iran)
  - 🟠 **HOSTILE-TARGETED** — Active attacks on specific flags; others pass safely (e.g. Bab-el-Mandeb / Houthis)
  - 🟡 **RESTRICTED** — Capacity reduced for non-political reasons (e.g. Panama Canal drought)
  - 🔴 **CLOSED** — Full blockade
- **Access Control tab** — who can transit freely vs. who is at risk, and why
- **Country Impact tab** — ranked list of most-affected nations with reasoning
- **Live news feed** — Google News RSS, refreshed every 15 minutes
- **Cross-chokepoint heatmap** — which countries are exposed across all 8 chokepoints simultaneously

## Chokepoints Covered

| Chokepoint | Oil Flow | Status |
|---|---|---|
| Strait of Hormuz | 17M bbl/day (20% world) | 🔵 Selective |
| Strait of Malacca | 16M bbl/day (25% trade) | 🟢 Open |
| Suez Canal | 5.5M bbl/day (9% world) | 🟢 Open |
| Bab-el-Mandeb | 3.8M bbl/day (6% world) | 🟠 Hostile-Targeted |
| Turkish Straits (Bosphorus) | 2.4M bbl/day (3% world) | 🔵 Selective |
| Panama Canal | 1M bbl/day (7% LNG) | 🟡 Restricted |
| Danish Straits | 1.5M bbl/day (2% world) | 🟢 Open |
| Lombok Strait | 2.5M bbl/day (4% world) | 🟢 Open |

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud (Free)

1. Fork this repo
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud) → New app
3. Point to your fork → `app.py`
4. Deploy — done

## Data Sources & Methodology

- Oil flow data: EIA, IEA, BP Statistical Review
- Geopolitical access status: Analyst assessment based on UN/IMO reports, Reuters, Bloomberg
- Country impact scores: Analytical estimates based on IEA import dependency data
- News: Google News RSS (live)

> **Disclaimer:** Status and impact scores are analytical estimates for informational purposes only. Not financial or geopolitical advice.

## License

MIT
