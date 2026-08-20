"""Tyre stints and stint-length vs mean pace."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.state import configure_page, get_bundle, show_fig
from src.viz import plot_strategy, plot_stint_pace

configure_page("Strategy")

session, tables, _drivers = get_bundle()
stints = tables["stints"]

st.title("Tyre strategy")
st.caption(
    "Stints are grouped from TimingAppData (compound + stint number) after "
    "FastF1 merges it onto lap timing. Bar colours use official compound colours."
)

if stints.empty:
    st.warning("No stint information for this session.")
    st.stop()

show_fig(plot_strategy(stints, session))
st.subheader("Stint length vs mean pace")
show_fig(plot_stint_pace(stints, session))

st.subheader("Stint table")
st.dataframe(stints, width="stretch", hide_index=True)
