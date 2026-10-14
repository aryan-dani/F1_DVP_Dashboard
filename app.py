"""F1 race-weekend dashboard. Navigation lives here; screens live in src/views."""

import streamlit as st

from src.state import configure_page, inject_css


configure_page("F1 Dashboard")
inject_css()

pages = st.navigation({
    "Weekend": [
        st.Page("src/views/home.py", title="Home", icon=":material/home:", default=True),
        st.Page("src/views/overview.py", title="Weekend", icon=":material/calendar_month:"),
        st.Page("src/views/results.py", title="Results", icon=":material/emoji_events:"),
        st.Page("src/views/pace.py", title="Pace", icon=":material/speed:"),
        st.Page("src/views/strategy.py", title="Strategy", icon=":material/route:"),
        st.Page("src/views/telemetry.py", title="Telemetry", icon=":material/show_chart:"),
        st.Page("src/views/track.py", title="Track map", icon=":material/map:"),
    ],
    "Compare": [
        st.Page("src/views/compare.py", title="Compare", icon=":material/compare_arrows:"),
    ],
    "Season": [
        st.Page("src/views/season.py", title="Season", icon=":material/leaderboard:"),
    ],
    "Data quality": [
        st.Page("src/views/quality.py", title="Data quality", icon=":material/fact_check:"),
    ],
})
pages.run()
