"""
app.py

Databricks Apps entrypoint. The platform runs `streamlit run app.py`, so this file
MUST keep this name and stay the entrypoint.

It is a thin Streamlit multipage launcher that wires the two pages with custom
sidebar labels via st.navigation:

  * Family Navigator         -> family_navigator.py  (the family-facing flow)
  * Program Leader Dashboard -> pages/1_Program_Leader_Dashboard.py

Each page owns its own st.set_page_config (they use different layouts), so
set_page_config is intentionally NOT called here. That keeps exactly one
set_page_config per page run and avoids duplicate/invalid calls.
"""

import streamlit as st

_pages = [
    st.Page("family_navigator.py", title="Family Navigator", icon="🧭", default=True),
    st.Page(
        "pages/1_Program_Leader_Dashboard.py",
        title="Program Leader Dashboard",
        icon="🏛️",
    ),
]

st.navigation(_pages).run()
