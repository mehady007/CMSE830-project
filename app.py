"""Growing Economies, Falling Emissions? — Energy Transition Explorer (Streamlit app).

Run with:  streamlit run app.py
The app is self-contained: the data-preparation functions below are the same as Section 0 of the analysis
notebook (notebooks/energy_transition_analysis.ipynb), so the app and the notebook show the same numbers.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# --------------------------------------------------------------------------- Data preparation
# Same settings and functions as Section 0 of the analysis notebook; change both together.
DATA_DIR = Path(__file__).resolve().parent / "data"
YEAR_MIN, YEAR_MAX = 1990, 2023  # years kept in the panel (the data checks look at all of them)
ANALYSIS_START = 2000            # first year any comparison may use
FLAT_BAND_PCT = 5                # CO2 changes within +/- this many percent count as "about flat"

CO2_COLS = ["country", "year", "iso_code", "population", "gdp", "co2", "co2_per_capita",
            "consumption_co2", "consumption_co2_per_capita", "primary_energy_consumption"]
ENERGY_COLS = ["iso_code", "year", "coal_share_elec", "oil_share_elec", "gas_share_elec",
               "nuclear_share_elec", "hydro_share_elec", "wind_share_elec", "solar_share_elec",
               "other_renewables_share_elec", "low_carbon_share_elec", "fossil_share_elec",
               "renewables_share_elec", "carbon_intensity_elec"]
CLASS_ORDER = ["Absolute decoupling", "CO₂ about flat", "Coupled growth", "GDP fell", "Insufficient data"]


def load_raw(data_dir=DATA_DIR):
    """Read the three raw CSV files exactly as downloaded."""
    co2 = pd.read_csv(data_dir / "owid-co2-data.csv")
    energy = pd.read_csv(data_dir / "owid-energy-data.csv")
    continents = pd.read_csv(data_dir / "owid-continents.csv")
    return co2, energy, continents


def build_panel(co2, energy, continents, year_min=YEAR_MIN, year_max=YEAR_MAX):
    """Return (panel, join_report).

    panel: one row per country-year, countries only, CO2 and energy data joined.
    join_report: counts of rows that matched / did not match in the join.
    """
    # 1. Aggregates ("World", "Africa", "High-income countries", ...) have no ISO code.
    c = co2[co2["iso_code"].notna() & co2["year"].between(year_min, year_max)][CO2_COLS]
    e = energy[energy["iso_code"].notna() & energy["year"].between(year_min, year_max)][ENERGY_COLS]

    # 2. Join on ISO code + year. Outer join first so unmatched rows can be reported.
    j = c.merge(e, on=["iso_code", "year"], how="outer", indicator=True)
    join_report = j["_merge"].map({"both": "matched", "left_only": "CO2 file only",
                                   "right_only": "energy file only"}).value_counts()
    # Keep every country-year that has CO2 data (energy columns may be NaN).
    panel = j[j["_merge"] != "right_only"].drop(columns="_merge").copy()

    # 3. Continent lookup (OWID's own classification).
    cont = continents.dropna(subset=["code"]).set_index("code")["owid_region"]
    panel["continent"] = panel["iso_code"].map(cont)

    # 4. Derived variable.
    panel["gdp_per_capita"] = panel["gdp"] / panel["population"]
    return panel.sort_values(["country", "year"]).reset_index(drop=True), join_report


def decoupling_table(panel, start, end, band=FLAT_BAND_PCT):
    """Compare each country between two years and label it.

    Absolute decoupling = GDP went up AND territorial CO2 fell by more than `band` %.
    CO2 about flat      = GDP went up and CO2 changed by `band` % or less (either way).
    Coupled growth      = GDP went up and CO2 rose by more than `band` %.
    Countries without GDP or CO2 in either year are labelled "Insufficient data"
    (GDP is NOT imputed - a verdict built on invented GDP would be misleading).
    """
    keep = ["gdp", "co2", "population", "low_carbon_share_elec", "coal_share_elec",
            "co2_per_capita", "consumption_co2"]
    a = panel[panel["year"] == start].set_index("iso_code")[keep]
    b = panel[panel["year"] == end].set_index("iso_code")[keep]
    info = panel.drop_duplicates("iso_code").set_index("iso_code")[["country", "continent"]]
    t = info.join(a.add_suffix("_start")).join(b.add_suffix("_end"))

    t["gdp_change_pct"] = (t["gdp_end"] / t["gdp_start"] - 1) * 100
    t["co2_change_pct"] = (t["co2_end"] / t["co2_start"] - 1) * 100
    t["cons_co2_change_pct"] = (t["consumption_co2_end"] / t["consumption_co2_start"] - 1) * 100
    t["low_carbon_change_pp"] = t["low_carbon_share_elec_end"] - t["low_carbon_share_elec_start"]
    t["coal_change_pp"] = t["coal_share_elec_end"] - t["coal_share_elec_start"]

    ok = t["gdp_change_pct"].notna() & t["co2_change_pct"].notna()
    grew = t["gdp_change_pct"] > 0
    t["decoupling"] = np.select(
        [~ok, ~grew, t["co2_change_pct"] < -band, t["co2_change_pct"] <= band],
        ["Insufficient data", "GDP fell", "Absolute decoupling", "CO₂ about flat"],
        default="Coupled growth")
    return t.reset_index()


def load_panel(data_dir=DATA_DIR):
    """Load the raw files and return (panel, join_report)."""
    co2, energy, continents = load_raw(data_dir)
    return build_panel(co2, energy, continents)


# --------------------------------------------------------------------------- App settings
st.set_page_config(page_title="Energy Transition Explorer", layout="wide")

GITHUB_URL = "https://github.com/mehady007/CMSE830-project"
GDP_LAST_YEAR = 2022  # Maddison GDP data end in 2022
DEC, CPL = "Absolute decoupling", "Coupled growth"

# Colour-blind-safe palettes (Okabe-Ito based), the same as in the notebook. Continents avoid the class
# colours, so a continent never reads as a decoupling group.
CLASS_COLORS = {DEC: "#009E73", "CO₂ about flat": "#E5C000", CPL: "#D55E00",
                "GDP fell": "#999999", "Insufficient data": "#DDDDDD"}
CONTINENT_COLORS = {"Africa": "#E69F00", "Asia": "#CC79A7", "Europe": "#0072B2",
                    "North America": "#56B4E9", "South America": "#B8A800", "Oceania": "#000000"}
# Electricity sources: fossil fuels in neutral greys/brown, low-carbon sources in Okabe-Ito hues.
MIX_COLORS = {"Coal": "#3A3A3A", "Oil": "#8C6D4F", "Gas": "#BDBDBD", "Nuclear": "#CC79A7",
              "Hydro": "#0072B2", "Wind": "#56B4E9", "Solar": "#E69F00", "Other renewables": "#009E73"}
MIX_COLS = {"Coal": "coal_share_elec", "Oil": "oil_share_elec", "Gas": "gas_share_elec",
            "Nuclear": "nuclear_share_elec", "Hydro": "hydro_share_elec", "Wind": "wind_share_elec",
            "Solar": "solar_share_elec", "Other renewables": "other_renewables_share_elec"}
CO2_KIND_COLORS = {"Territorial (produced here)": "#0072B2", "Consumption-based (consumed here)": "#E69F00"}
ROBUSTNESS_PAIRS = [(2000, 2022), (2005, 2022), (2010, 2019), (2010, 2022)]


@st.cache_data
def get_data():
    return load_panel()


@st.cache_data
def get_table(start, end, band=FLAT_BAND_PCT):
    """Decoupling labels for every country between two years (cached per year pair and margin)."""
    return decoupling_table(panel, start, end, band=band)


def github_link(text):
    """Markdown link to the repository, or plain text until the URL has been filled in."""
    return f"[{text}]({GITHUB_URL})" if GITHUB_URL.startswith("http") else text


def signed(v):
    """Whole number with a sign (+13, -4, 0, never "-0"), or "n/a" when there is no value."""
    if pd.isna(v):
        return "n/a"
    r = int(round(v))
    return f"{r:+d}" if r else "0"


def pct(v):
    """Percentage change for text: one decimal for small changes so -0.3% does not show as -0%."""
    if pd.isna(v):
        return "n/a"
    if round(v, 1) == 0:
        return "0%"
    return f"{v:+.1f}%" if abs(v) < 10 else f"{v:+.0f}%"


def median_pair(m):
    """'decouplers +14 vs 0 pts', or a plain note when one of the two groups is not in the selection."""
    d, c = m.get(DEC), m.get(CPL)
    if pd.notna(d) and pd.notna(c):
        return f"decouplers {signed(d)} vs {signed(c)} pts"
    if pd.notna(d):
        return f"decouplers {signed(d)} pts (no coupled-growth countries)"
    if pd.notna(c):
        return f"no decouplers (coupled growth {signed(c)} pts)"
    return "no decouplers or coupled-growth countries"


def and_list(items):
    """'A, B and C'."""
    items = list(items)
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else "".join(items)


panel, join_report = get_data()
countries = sorted(panel["country"].unique())
main = get_table(2005, GDP_LAST_YEAR)                 # the main comparison used for the headline numbers
main_known = main[main["decoupling"] != "Insufficient data"]
main_dec = main_known[main_known["decoupling"] == DEC]

st.title("Growing Economies, Falling Emissions?")
st.markdown(
    "Some countries now produce **more economic output while emitting clearly less CO₂**. This is called "
    "*absolute decoupling*. This app lets you check **which countries have done it, over which years, "
    "and whether their electricity became cleaner at the same time.**"
)

tab_home, tab_country, tab_compare, tab_counting, tab_data, tab_limits = st.tabs(
    ["Start here", "1 · One country", "2 · Compare countries", "3 · Made here or consumed here?",
     "Data & preparation", "Limitations & about"])

# --------------------------------------------------------------------------- Start here
with tab_home:
    st.subheader("How to use this app")
    st.markdown(
        f"""
Click the tabs above, from left to right. Every chart responds to the controls just above it.

1. **One country:** pick a country and see whether its GDP and CO₂ moved together or apart since {ANALYSIS_START},
   and how its electricity mix changed.
2. **Compare countries:** choose two years and see every country on one chart. Countries in the green
   *lower-right* area grew their economy **and** cut CO₂ by more than {FLAT_BAND_PCT}%. You can highlight one
   country to find it quickly.
3. **Made here or consumed here?** check whether falling emissions are partly explained by importing
   goods that were made (and emitted) in other countries.
4. **Data & preparation** and **Limitations & about** explain where the numbers come from and what they cannot tell you.

Tip: hover over any chart to see exact values; click a legend entry to hide or show that group.

**Key terms**
- **GDP**: total economic output, adjusted for inflation (international dollars).
- **Territorial CO₂**: CO₂ emitted from fossil fuels and industry *inside* a country's borders.
- **Consumption-based CO₂**: territorial CO₂, plus CO₂ emitted abroad to make the goods a country imports,
  minus CO₂ emitted to make its exports.
- **Absolute decoupling**: GDP grew **and** territorial CO₂ fell by more than {FLAT_BAND_PCT}% between two years.
  If CO₂ changed by {FLAT_BAND_PCT}% or less, the country is shown as *CO₂ about flat*; if it rose by more,
  as *coupled growth*.
- **Low-carbon electricity**: electricity from nuclear, hydro, wind, solar and other renewables.
"""
    )
    med_dec = main_dec["low_carbon_change_pp"].median()
    med_cpl = main_known.loc[main_known["decoupling"] == CPL, "low_carbon_change_pp"].median()
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Countries that decoupled, 2005→{GDP_LAST_YEAR}", f"{len(main_dec)} of {len(main_known)}")
    c2.metric("…of which in Europe", int((main_dec["continent"] == "Europe").sum()))
    c3.metric("Change in low-carbon electricity share (median)", f"{signed(med_dec)} pts",
              delta=f"vs {signed(med_cpl)} pts for coupled-growth countries", delta_color="off")
    st.caption("Countries without GDP for both years are not counted (see Data & preparation).")

# --------------------------------------------------------------------------- One country
with tab_country:
    st.subheader("Did GDP and CO₂ move together or apart?")
    col_a, col_b = st.columns([2, 1])
    country = col_a.selectbox("Country", countries, index=countries.index("United Kingdom"),
                              help="Type to search. Every country with CO₂ data is listed.")
    base_year = col_b.slider("Base year (= 100)", ANALYSIS_START, 2015, 2005,
                             help="All three lines are set to 100 in this year, so you can compare growth rates. "
                                  f"Years before {ANALYSIS_START} are not offered (see Data & preparation).")

    d = panel[(panel["country"] == country) & (panel["year"] >= base_year)].set_index("year")
    series = {"GDP": "gdp", "CO₂ (territorial)": "co2", "Population": "population"}
    idx = pd.DataFrame({name: d[col] / d[col].get(base_year) * 100 for name, col in series.items()
                        if pd.notna(d[col].get(base_year)) and d[col].get(base_year) > 0})
    if idx.empty or "GDP" not in idx or "CO₂ (territorial)" not in idx or idx.dropna().empty:
        st.warning(f"GDP for {country} is not available in {base_year}, so this comparison cannot be made. "
                   "GDP is missing for most very small countries and for a few larger ones affected by war or "
                   "crisis (see Data & preparation).")
    else:
        long = idx.reset_index().melt("year", var_name="Series", value_name="Index").dropna()
        fig = px.line(long, x="year", y="Index", color="Series",
                      color_discrete_map={"GDP": "#0072B2", "CO₂ (territorial)": "#D55E00",
                                          "Population": "#999999"},
                      labels={"year": "Year", "Index": f"Index ({base_year} = 100)"})
        fig.add_hline(y=100, line_dash="dot", line_color="grey")
        last = idx.dropna().index.max()
        g, c = idx.loc[last, "GDP"], idx.loc[last, "CO₂ (territorial)"]
        if g <= 100:
            verdict = "GDP did not grow"
        elif c < 100 - FLAT_BAND_PCT:
            verdict = "GDP grew while CO₂ fell — absolute decoupling"
        elif c <= 100 + FLAT_BAND_PCT:
            verdict = "GDP grew while CO₂ stayed about flat"
        else:
            verdict = "GDP and CO₂ both grew"
        fig.update_layout(title=f"{country}, {base_year}–{last}: {verdict}", legend_title=None,
                          hovermode="x unified")
        st.plotly_chart(fig, width="stretch")
        st.caption(f"In {last}, GDP index = {g:.0f} and CO₂ index = {c:.0f}. GDP data end in {GDP_LAST_YEAR}. "
                   "One country is shown at a time, so a plain (linear) axis is used.")

    st.subheader("How did the electricity mix change?")
    m = d[list(MIX_COLS.values())].rename(columns={v: k for k, v in MIX_COLS.items()}).dropna(how="all")
    if m.empty:
        st.info(f"No electricity-mix data for {country} after {base_year}.")
    else:
        lc = d["low_carbon_share_elec"].dropna()
        mix_title = (f"{country}: low-carbon sources went from {lc.iloc[0]:.0f}% of electricity in "
                     f"{lc.index[0]} to {lc.iloc[-1]:.0f}% in {lc.index[-1]}"
                     if len(lc) > 1 else f"{country}: where electricity comes from")
        ml = m.reset_index().melt("year", var_name="Source", value_name="Share (%)")
        fig2 = px.area(ml, x="year", y="Share (%)", color="Source", color_discrete_map=MIX_COLORS,
                       category_orders={"Source": list(MIX_COLS)},
                       labels={"year": "Year", "Share (%)": "Share of electricity (%)"},
                       title=mix_title)
        fig2.update_yaxes(range=[0, 100])
        fig2.update_layout(hovermode="x unified")
        st.plotly_chart(fig2, width="stretch")
        st.caption("Fossil fuels are shown in greys and brown, low-carbon sources in colour. "
                   "Shares are of electricity generation, not of all energy use.")

# --------------------------------------------------------------------------- Compare countries
with tab_compare:
    st.subheader("Which countries grew their economy and cut CO₂?")
    c1, c2, c3 = st.columns([2, 2, 3])
    start, end = c1.slider("Compare these two years", ANALYSIS_START, GDP_LAST_YEAR, (2005, GDP_LAST_YEAR),
                           help="GDP data end in 2022. Avoid 2020 as an end year: COVID lowered both GDP and CO₂.")
    band = c2.slider("Margin for 'CO₂ about flat' (±%)", 0, 10, FLAT_BAND_PCT,
                     help="A country counts as decoupled only if its CO₂ fell by more than this. Smaller changes are "
                          "within normal year-to-year swings and data uncertainty. 0 = any fall counts.")
    conts = c3.multiselect("Continents", list(CONTINENT_COLORS), default=list(CONTINENT_COLORS),
                           help="Remove continents to focus on the rest.")
    if 0 < end - start < 5:
        st.warning("Pick years at least 5 years apart; short periods mostly show year-to-year noise.")
    if 2020 in (start, end):
        st.info("2020 was a COVID year, so changes involving 2020 are unusual.")

    t = get_table(start, end, band)
    shown = t[(t["decoupling"] != "Insufficient data") & t["continent"].isin(conts)]
    if start == end:
        st.warning("The two years are the same. Move one end of the slider to compare two different years.")
    elif not conts:
        st.warning("No continent is selected. Choose at least one continent above.")
    elif shown.empty:
        st.warning("No countries match the current selection.")
    else:
        c4, c5 = st.columns([2, 2])
        highlight = c4.selectbox("Highlight a country (optional)", ["(none)"] + sorted(shown["country"]),
                                 help="Draws a ring and a label around one country so you can find it.")
        zoom = c5.checkbox("Zoom in on most countries", value=True,
                           help="A few countries more than tripled their CO₂ and squeeze everyone else "
                                "into a corner. Untick to see all countries.")

        fig3 = px.scatter(shown, x="gdp_change_pct", y="co2_change_pct", color="continent",
                          size="population_end", size_max=45, hover_name="country",
                          color_discrete_map=CONTINENT_COLORS,
                          category_orders={"continent": list(CONTINENT_COLORS)},
                          hover_data={"gdp_change_pct": ":.0f", "co2_change_pct": ":.1f",
                                      "population_end": ":,.0f", "continent": False},
                          labels={"gdp_change_pct": f"Change in GDP {start}→{end} (%)",
                                  "co2_change_pct": f"Change in territorial CO₂ {start}→{end} (%)",
                                  "population_end": "Population", "continent": "Continent"})
        if zoom:
            xr = (shown["gdp_change_pct"].min() - 10, shown["gdp_change_pct"].quantile(0.95) + 10)
            yr = (shown["co2_change_pct"].min() - 10, shown["co2_change_pct"].quantile(0.95) + 10)
        else:
            xr = (shown["gdp_change_pct"].min() - 10, shown["gdp_change_pct"].max() + 10)
            yr = (shown["co2_change_pct"].min() - 10, shown["co2_change_pct"].max() + 10)
        fig3.update_xaxes(range=xr)
        fig3.update_yaxes(range=yr)
        # Shaded areas: green = decoupling (GDP up, CO2 down by more than the margin), yellow = CO2 about flat.
        fig3.add_shape(type="rect", x0=0, x1=xr[1], y0=yr[0], y1=-band, layer="below", line_width=0,
                       fillcolor=CLASS_COLORS[DEC], opacity=0.10)
        if band > 0:
            fig3.add_shape(type="rect", x0=0, x1=xr[1], y0=-band, y1=band, layer="below", line_width=0,
                           fillcolor=CLASS_COLORS["CO₂ about flat"], opacity=0.30)
            fig3.add_annotation(x=1, y=band, xref="x domain", yref="y", yanchor="bottom", xanchor="right",
                                showarrow=False, text=f"CO₂ about flat (±{band}%)", font_color="#6b5a00")
        fig3.add_hline(y=0, line_color="#555555", line_width=1)
        fig3.add_vline(x=0, line_color="#555555", line_width=1)
        fig3.add_annotation(x=1, y=-band, xref="x domain", yref="y", yanchor="top", xanchor="right",
                            showarrow=False, font_color="#00704f",
                            text=f"<b>Grew GDP, cut CO₂ by more than {band}%</b> (absolute decoupling)")
        n_dec = (shown["decoupling"] == DEC).sum()
        fig3.update_layout(title=f"{n_dec} of {len(shown)} countries decoupled between {start} and {end}")
        hidden = (~shown["gdp_change_pct"].between(*xr) | ~shown["co2_change_pct"].between(*yr)).sum()
        note = ""
        if highlight != "(none)":
            h = shown[shown["country"] == highlight].iloc[0]
            fig3.add_trace(go.Scatter(
                x=[h["gdp_change_pct"]], y=[h["co2_change_pct"]], mode="markers", hoverinfo="skip",
                marker=dict(size=26, color="rgba(0,0,0,0)", line=dict(color="black", width=3)),
                showlegend=False))
            fig3.add_annotation(x=h["gdp_change_pct"], y=h["co2_change_pct"], text=f"<b>{highlight}</b>",
                                showarrow=True, arrowhead=0, ax=40, ay=-45, bgcolor="rgba(255,255,255,0.9)",
                                bordercolor="black", borderpad=3, font_color="black")
            note = (f" **{highlight}:** GDP {pct(h['gdp_change_pct'])}, CO₂ {pct(h['co2_change_pct'])} "
                    f"→ *{h['decoupling']}*.")
            if zoom and not (xr[0] <= h["gdp_change_pct"] <= xr[1] and yr[0] <= h["co2_change_pct"] <= yr[1]):
                note += " It is outside the zoomed view; untick *Zoom in* to see it."
        st.plotly_chart(fig3, width="stretch")
        st.caption("Bubble size = population in the end year. Hover for country names."
                   + (f" Zoomed view: {hidden} countries with very large changes are off the chart." if zoom else ""))
        if note:
            st.markdown(note)

        st.markdown("**Share of countries in each group, by continent** (n = number of countries with data)")
        tab = pd.crosstab(shown["continent"], shown["decoupling"])
        n = tab.sum(axis=1)
        share = (tab.div(n, axis=0) * 100).round(0)
        share.index = [f"{c} (n={n[c]})" for c in share.index]
        st.dataframe(share[[c for c in CLASS_ORDER if c in share]].style.format("{:.0f}%"),
                     width="stretch")
        if "Oceania" in conts and n.get("Oceania", 0) < 5:
            st.caption(f"Oceania has only {n.get('Oceania', 0)} countries with GDP data, "
                       "so its shares are not reliable.")

        st.markdown("**Did decoupling countries also make their electricity cleaner?**")
        split = st.checkbox("Compare Europe with the rest of the world",
                            help="Most decouplers are European. Tick this to check whether the pattern also "
                                 "holds outside Europe.")
        box = shown.dropna(subset=["low_carbon_change_pp"]).copy()
        if box.empty:
            st.info("No electricity-mix data for these years.")
        else:
            box["region"] = np.where(box["continent"] == "Europe", "Europe", "Rest of the world")
            groups = ([(r, box[box["region"] == r]) for r in ["Europe", "Rest of the world"]
                       if (box["region"] == r).any()] if split else [("All selected countries", box)])
            fig4 = make_subplots(rows=1, cols=len(groups), shared_yaxes=True,
                                 subplot_titles=[g for g, _ in groups] if split else None)
            medians = {}
            for col, (gname, gdata) in enumerate(groups, start=1):
                medians[gname] = gdata.groupby("decoupling")["low_carbon_change_pp"].median()
                for cls in [c for c in CLASS_ORDER if c in set(gdata["decoupling"])]:
                    cd = gdata[gdata["decoupling"] == cls]
                    fig4.add_trace(go.Box(x=[f"{cls}<br>(n={len(cd)})"] * len(cd), y=cd["low_carbon_change_pp"],
                                          name=cls, marker_color=CLASS_COLORS[cls], boxpoints="all", jitter=0.4,
                                          pointpos=0, hovertext=cd["country"], showlegend=False,
                                          hovertemplate="%{hovertext}: %{y:+.1f} pts<extra></extra>"),
                                   row=1, col=col)
            fig4.add_hline(y=0, line_dash="dot", line_color="grey")
            fig4.update_yaxes(title_text="Change in low-carbon electricity share (% pts)", row=1, col=1)
            m = medians[groups[0][0]]
            if not split and pd.notna(m.get(DEC)) and pd.notna(m.get(CPL)):
                title = (f"Decouplers changed their low-carbon electricity share by a median of {signed(m[DEC])} "
                         f"pts vs {signed(m[CPL])} pts for coupled-growth countries")
            else:
                title = "Median change in low-carbon share: " + " · ".join(
                    (f"{g}: " if split else "") + median_pair(m) for g, m in medians.items())
            fig4.update_layout(title=title, height=480)
            st.plotly_chart(fig4, width="stretch")
            caption = (f"Change in the share of electricity from low-carbon sources, {start} to {end}. "
                       "Each dot is a country; the box shows the middle half and the line the median. "
                       "Groups have very different sizes, so compare medians rather than counts. "
                       "Power-sector CO₂ is part of total CO₂, so this shows *which lever moved* (cleaner power), "
                       "not a separate cause.")
            if split:
                n_rest = int(((box["region"] == "Rest of the world") & (box["decoupling"] == DEC)).sum())
                caption += (f" Outside Europe there are only {n_rest} decouplers here, so that comparison is "
                            "much less certain.")
            st.caption(caption)

# --------------------------------------------------------------------------- Made here or consumed here?
with tab_counting:
    st.subheader("Did emissions really fall, or did they move abroad?")
    st.markdown(
        "Territorial CO₂ counts emissions where goods are **made**. Consumption-based CO₂ counts them where "
        "goods are **used**. If a country's territorial CO₂ falls but its consumption-based CO₂ does not, part of "
        "its \"decoupling\" may come from importing goods made elsewhere. Consumption-based data exist for "
        "about 120 countries."
    )
    has_cons = sorted(panel.loc[panel["consumption_co2"].notna(), "country"].unique())
    defaults = [c for c in ["United Kingdom", "Germany", "United States", "France", "Sweden", "China", "India"]
                if c in has_cons]
    c1, c2 = st.columns([3, 2])
    picked = c1.multiselect("Countries (only those with consumption-based data)", has_cons, default=defaults)
    q4_start, q4_end = c2.slider("Compare these two years", ANALYSIS_START, GDP_LAST_YEAR, (2005, GDP_LAST_YEAR),
                                 key="q4_years", help="Consumption-based data end in 2022/2023.")
    view = st.radio("Show", ["% change between the two years", "Tonnes of CO₂ per person (in the end year)"],
                    horizontal=True,
                    help="% change answers 'did it fall?'. Tonnes per person shows whether a country is a net "
                         "importer of emissions (orange dot to the right of the blue dot).")
    pct_view = view.startswith("%")

    if not picked:
        st.warning("Select at least one country above.")
    elif pct_view and q4_start == q4_end:
        st.warning("The two years are the same. Move one end of the slider to compare two different years.")
    else:
        if pct_view:
            sel = get_table(q4_start, q4_end).set_index("country")
            sel = sel.loc[[c for c in picked if c in sel.index]]
            vals = pd.DataFrame({"Territorial (produced here)": sel["co2_change_pct"],
                                 "Consumption-based (consumed here)": sel["cons_co2_change_pct"]})
            axis_label = f"Change in CO₂ {q4_start}→{q4_end} (%)"
        else:
            p_end = panel[panel["year"] == q4_end].set_index("country")
            p_end = p_end.loc[[c for c in picked if c in p_end.index]]
            vals = pd.DataFrame({"Territorial (produced here)": p_end["co2_per_capita"],
                                 "Consumption-based (consumed here)": p_end["consumption_co2_per_capita"]})
            axis_label = f"CO₂ per person in {q4_end} (tonnes)"
        missing = [c for c in picked if c not in vals.dropna().index]
        vals = vals.dropna()
        if vals.empty:
            st.warning("None of the selected countries has both measures for these years.")
        else:
            vals = vals.sort_values("Territorial (produced here)")
            if pct_view:
                both_fell = ((vals < 0).all(axis=1)).sum()
                title = (f"{both_fell} of {len(vals)} selected countries cut both territorial and "
                         f"consumption-based CO₂, {q4_start}→{q4_end}")
            else:
                importers = (vals["Consumption-based (consumed here)"] > vals["Territorial (produced here)"]).sum()
                title = (f"{importers} of {len(vals)} selected countries consumed more CO₂ than they "
                         f"produced in {q4_end} (net importers of emissions)")
            fig6 = go.Figure()
            for name, row in vals.iterrows():
                fig6.add_trace(go.Scatter(x=row.values, y=[name, name], mode="lines",
                                          line=dict(color="#BBBBBB", width=3), showlegend=False,
                                          hoverinfo="skip"))
            for kind, color in CO2_KIND_COLORS.items():
                fig6.add_trace(go.Scatter(x=vals[kind], y=vals.index, mode="markers", name=kind,
                                          marker=dict(color=color, size=13, line=dict(color="white", width=1.5)),
                                          hovertemplate="%{y}: %{x:.1f}<extra>" + kind + "</extra>"))
            if pct_view:
                fig6.add_vline(x=0, line_color="black", line_width=1)
            fig6.update_layout(title=title, xaxis_title=axis_label, yaxis_title=None,
                               height=max(380, 120 + 45 * len(vals)),
                               legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None))
            st.plotly_chart(fig6, width="stretch")
            st.caption("Each row is one country: blue = territorial CO₂, orange = consumption-based CO₂. "
                       "A long grey bar means the two ways of counting disagree. Consumption-based CO₂ is "
                       "estimated from trade data, so it is least reliable for small trading economies "
                       "(e.g. Malta, Cyprus, Hong Kong).")
        if missing:
            st.caption("No data for both measures in these years: " + ", ".join(missing) + ".")

    # Overall answer for all decouplers (not only the selected countries).
    if q4_start != q4_end:
        all_t = get_table(q4_start, q4_end)
        dec4 = all_t[(all_t["decoupling"] == DEC) & all_t["cons_co2_change_pct"].notna()]
        if len(dec4):
            n_both = int((dec4["cons_co2_change_pct"] < 0).sum())
            verdict = ("So for most decouplers the fall is not only an effect of imports."
                       if n_both > len(dec4) / 2 else
                       "So for many decouplers, imports may explain part of the fall.")
            st.info(f"**All countries, {q4_start}→{q4_end}:** of the {len(dec4)} decoupling countries that have "
                    f"consumption-based data, {n_both} also cut their consumption-based CO₂. {verdict}")

# --------------------------------------------------------------------------- Data & preparation
with tab_data:
    st.subheader("Where the data come from")
    st.markdown(
        f"""
| Source | What it gives | Licence | Link |
|---|---|---|---|
| Our World in Data — CO₂ and Greenhouse Gas Emissions | CO₂ (million tonnes and tonnes per person), GDP (international $, 2011 prices), population (Global Carbon Project, Maddison Project, UN) | CC BY 4.0 | github.com/owid/co2-data |
| Our World in Data — Energy | Electricity mix shares, % of generation (Energy Institute, Ember) | CC BY 4.0 | github.com/owid/energy-data |
| Our World in Data — Continents | Continent of each country | CC BY 4.0 | ourworldindata.org |

**One row = one country in one year ({YEAR_MIN}–{YEAR_MAX}).** The files are joined on the 3-letter ISO country code
and year. The data checks on this page use all years; the comparisons in the app start in {ANALYSIS_START}.
"""
    )
    p22 = panel[panel["year"] <= GDP_LAST_YEAR]  # GDP ends in 2022, so 2023 would inflate GDP missingness
    early = p22["year"] < ANALYSIS_START
    elec_early = p22.loc[early, "low_carbon_share_elec"].isna().mean() * 100
    elec_late = p22.loc[~early, "low_carbon_share_elec"].isna().mean() * 100
    t90 = get_table(YEAR_MIN, GDP_LAST_YEAR).set_index("country")
    post_soviet = [c for c in ["Russia", "Belarus", "Romania", "Azerbaijan"] if t90.loc[c, "decoupling"] == DEC]
    big_missing = main.loc[(main["decoupling"] == "Insufficient data") & (main["population_end"] > 5e6), "country"]
    aus = main.set_index("country").loc["Australia", "co2_change_pct"]

    st.subheader("Preparation decisions")
    st.markdown(
        f"""
1. **Removed region/group rows.** "World", "Africa", "High-income countries" and similar rows have no ISO code.
   Keeping them would double-count emissions.
2. **Comparisons start in {ANALYSIS_START}.** Electricity-mix data are missing for {elec_early:.0f}% of country-years
   in the 1990s but only {elec_late:.0f}% from {ANALYSIS_START} on (chart below). The early 1990s also include the
   collapse of the Soviet economy: a {YEAR_MIN}→{GDP_LAST_YEAR} comparison would label {and_list(post_soviet)} as
   "decouplers" just because their heavy industry collapsed first.
3. **Did not fill in (impute) missing GDP.** GDP is missing for most very small countries, for a few larger ones
   affected by war or crisis ({and_list(sorted(big_missing))}), and after {GDP_LAST_YEAR}. A "decoupling" label
   based on made-up GDP would be misleading, so those countries are shown as *Insufficient data*.
4. **Kept extreme values.** Kuwait 1991 (365 t CO₂ per person, from the Gulf War oil fires) is real, not an error.
   The chart below uses a log scale so it does not hide everyone else.
5. **A ±{FLAT_BAND_PCT}% margin for "about flat".** A country counts as decoupled only if GDP grew and CO₂ fell by more
   than {FLAT_BAND_PCT}%. Smaller changes (for example Australia, {pct(aus)} between 2005 and {GDP_LAST_YEAR}) are
   within normal year-to-year swings and the uncertainty of CO₂ estimates, so they are labelled *CO₂ about flat*.
   You can change the margin on the *Compare countries* tab.
"""
    )
    c1, c2 = st.columns(2)
    c1.markdown("**Join result**")
    c1.dataframe(join_report.rename_axis("Join result").rename("rows").to_frame(), width="stretch")
    c1.caption("CO₂-only rows are micro-states missing from the energy file (e.g. Monaco); they are kept. "
               "Energy-only rows are territories without CO₂ data (e.g. Puerto Rico); they are dropped.")
    miss = (p22[["co2", "gdp", "low_carbon_share_elec", "consumption_co2"]].isna().mean() * 100).round(1)
    miss.index = ["Territorial CO₂", "GDP", "Low-carbon share of electricity", "Consumption-based CO₂"]
    c2.markdown(f"**% missing (country-years, {YEAR_MIN}–{GDP_LAST_YEAR})**")
    c2.dataframe(miss.rename("% missing").to_frame(), width="stretch")

    by_year = (p22.groupby("year")["low_carbon_share_elec"].apply(lambda s: s.isna().mean() * 100)
               .rename("missing").reset_index())
    fig8 = px.line(by_year, x="year", y="missing", markers=True, color_discrete_sequence=["#0072B2"],
                   title=f"Electricity-mix data are missing for most countries before {ANALYSIS_START}, "
                         "so comparisons start there",
                   labels={"year": "Year", "missing": "Countries with no electricity-mix data (%)"})
    fig8.add_vrect(x0=YEAR_MIN - 0.5, x1=ANALYSIS_START - 0.5, fillcolor="#BBBBBB", opacity=0.3, line_width=0,
                   annotation_text="not used for comparisons", annotation_position="top left")
    fig8.update_yaxes(range=[0, 100])
    st.plotly_chart(fig8, width="stretch")

    sizes = pd.cut(p22["population"], [0, 1e6, 1e7, 1e8, 2e9], labels=["< 1 M", "1–10 M", "10–100 M", "> 100 M"])
    gm = (p22.groupby(sizes, observed=True)["gdp"].apply(lambda s: s.isna().mean() * 100)
          .rename("GDP missing (%)").reset_index().rename(columns={"population": "Country population"}))
    fig5 = px.bar(gm, x="Country population", y="GDP missing (%)", text_auto=".0f",
                  title=f"GDP is missing mainly for very small countries (country-years, {YEAR_MIN}–{GDP_LAST_YEAR})",
                  color_discrete_sequence=["#0072B2"],
                  labels={"GDP missing (%)": "Country-years with no GDP (%)"})
    fig5.update_yaxes(range=[0, 100])
    fig5.update_traces(textposition="outside", texttemplate="%{y:.0f}%")
    st.plotly_chart(fig5, width="stretch")

    pc = panel.dropna(subset=["co2_per_capita"])
    pc = pc[pc["co2_per_capita"] > 0].assign(log_pc=lambda x: np.log10(x["co2_per_capita"]))
    kw = pc.loc[pc["co2_per_capita"].idxmax()]
    q05, q95 = pc["co2_per_capita"].quantile([0.05, 0.95])
    # Bin on log10(CO2 per person) so the bins are even on the log axis; label ticks in tonnes.
    fig7 = px.histogram(pc, x="log_pc", nbins=60, color_discrete_sequence=["#0072B2"],
                        title=f"90% of country-years emit {q05:.1f}–{q95:.0f} t CO₂ per person; "
                              f"{kw['country']} {int(kw['year'])} ({kw['co2_per_capita']:.0f} t) is a real outlier")
    ticks = [0.01, 0.1, 1, 10, 100]
    fig7.update_xaxes(tickvals=np.log10(ticks), ticktext=[f"{v:g}" for v in ticks],
                      title="CO₂ per person (tonnes, log scale)")
    fig7.update_traces(hovertemplate="Count: %{y}<extra></extra>")
    fig7.update_layout(yaxis_title=f"Number of country-years ({YEAR_MIN}–{YEAR_MAX})", bargap=0.05)
    fig7.add_annotation(x=kw["log_pc"], y=0, yanchor="bottom", ax=0, ay=-50,
                        text=f"{kw['country']} {int(kw['year'])}<br>(oil-well fires)", showarrow=True)
    st.plotly_chart(fig7, width="stretch")

    if st.checkbox("Show the cleaned data table"):
        st.dataframe(panel, width="stretch")

# --------------------------------------------------------------------------- Limitations & about
with tab_limits:
    n_eu = int((main_dec["continent"] == "Europe").sum())
    pop_share = main_dec["population_end"].sum() / main_known["population_end"].sum() * 100
    cons = main_dec.dropna(subset=["cons_co2_change_pct"])
    n_cut = int((cons["cons_co2_change_pct"] < 0).sum())
    labels = pd.concat({f"{s}-{e}": get_table(s, e).set_index("iso_code")["decoupling"]
                        for s, e in ROBUSTNESS_PAIRS}, axis=1)
    labels = labels[labels[f"2005-{GDP_LAST_YEAR}"] != "Insufficient data"]
    switch_pct = (labels.nunique(axis=1) > 1).mean() * 100
    pairs_text = ", ".join(f"{s}→{e}" for s, e in ROBUSTNESS_PAIRS)

    st.subheader("What this app can and cannot tell you")
    st.markdown(
        f"""
- **Mostly a European story.** {n_eu} of the {len(main_dec)} countries that decoupled between 2005 and
  {GDP_LAST_YEAR} are in Europe. The link with cleaner electricity is clear there, but outside Europe there are too
  few decouplers to tell (tick *Compare Europe with the rest of the world* on tab 2).
- **Counted by country, not by people.** Every country counts once, whatever its size. Decouplers are
  {len(main_dec) / len(main_known) * 100:.0f}% of the countries but hold only {pop_share:.0f}% of their people.
- **Territorial vs. consumption CO₂.** A country can cut its own emissions by importing goods made elsewhere.
  Of the {len(main_dec)} decouplers, {len(cons)} have consumption-based data and {n_cut} of those also cut
  consumption-based CO₂ (see tab 3). Consumption-based figures are estimates from trade data.
- **Association, not cause.** Cleaner electricity goes together with decoupling, but this app does not prove that
  it *caused* the decoupling. Power-sector CO₂ is part of total CO₂, so the charts show which lever moved;
  economic structure, efficiency and policy also matter, and a few countries cut CO₂ during an economic crisis
  (e.g. Lebanon).
- **The years and the margin you pick matter.** About {switch_pct:.0f}% of countries change group when the
  comparison years change ({pairs_text}), and changing the ±{FLAT_BAND_PCT}% margin moves a few borderline countries.
- **Missing data.** Many small countries (especially in the Caribbean and Pacific) and a few larger countries affected
  by war or crisis have no GDP data and are not classified. Europe has many more countries with full data than Africa
  or Oceania, so group comparisons are uneven.
- **Data years:** comparisons start in {ANALYSIS_START}; GDP ends in {GDP_LAST_YEAR}; CO₂ ends in {YEAR_MAX} in this app.
"""
    )
    st.subheader("About")
    st.markdown(
        f"""
Built by Mehady Hassan for CMSE 830 (Michigan State University, Fall 2026). Code, data-preparation steps
and the full analysis notebook are in the {github_link("GitHub repository")}.

**AI use.** Generative AI (Claude, Anthropic) helped draft code, documentation and text for this app.
The app and the analysis notebook use the same data-preparation functions, so their numbers match.
The tool used, representative prompts, how outputs were checked and my own contribution are listed in
`AI_DISCLOSURE.md` in the repository.

Data: Our World in Data (CC BY 4.0).
"""
    )
