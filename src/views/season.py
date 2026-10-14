"""Championship standings from Jolpica. Does not download race telemetry."""

import streamlit as st

from src.charts import plot_points, plot_position_heatmap, plot_standings
from src.season import load_season
from src.state import render_sidebar, show_fig, show_table


year, _gp, _identifier, _schedule, _clicked = render_sidebar()

st.title(f"{year} season")
st.caption("Standings and results come from Jolpica. Opening a round only updates the weekend sidebar. It does not download the race.")

try:
    season = load_season(int(year))
except Exception as exc:
    st.error("Could not load this season from Jolpica.")
    with st.expander("Error detail"):
        st.exception(exc)
    st.stop()

drivers = season["drivers"]
constructors = season["constructors"]
results = season["results"]
points = season["points"]

if drivers.empty and results.empty:
    st.warning("Jolpica returned no standings or results for this year.")
    st.stop()

left, right = st.columns(2)
with left:
    st.subheader("Drivers")
    show_fig(plot_standings(drivers, "Code", "Points", "Driver standings"))
    if not drivers.empty:
        show_table(
            drivers[["Position", "Code", "Driver", "Team", "Points", "Wins"]],
            hide_index=True,
            height=360,
        )
with right:
    st.subheader("Constructors")
    show_fig(plot_standings(constructors, "Team", "Points", "Constructor standings"))
    if not constructors.empty:
        show_table(constructors, hide_index=True, height=360)

st.subheader("Points")
st.caption("Running total for the eight drivers with the most points at the end of the data Jolpica returned.")
show_fig(plot_points(points))

st.subheader("Race results")
st.caption("Each cell is the finishing position. Green is the front, red is the back.")
order = drivers["Code"].astype(str).tolist() if not drivers.empty else None
show_fig(plot_position_heatmap(results, order))

races = (
    results.sort_values("Round")[["Round", "Race"]]
    .drop_duplicates()
    .reset_index(drop=True)
    if not results.empty else results
)
if not races.empty:
    st.subheader("Open a round")
    labels = [f"R{int(row.Round)}  {row.Race}" for row in races.itertuples(index=False)]
    choice = st.selectbox("Round", labels, index=len(labels) - 1)
    selected = races.iloc[labels.index(choice)]
    if st.button("Use this round in the weekend sidebar", type="primary"):
        st.session_state["pending_round"] = {
            "year": int(year),
            "gp": str(selected["Race"]),
            "session": "Race",
        }
        st.switch_page("src/views/overview.py")
