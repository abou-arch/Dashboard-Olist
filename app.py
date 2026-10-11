"""Point d'entrée du dashboard : streamlit run app.py"""

import streamlit as st

st.set_page_config(page_title="Dashboard Olist", page_icon=":material/storefront:", layout="wide")

navigation = st.navigation(
    [
        st.Page("views/overview.py", title="Vue d'ensemble", icon=":material/dashboard:", default=True),
        st.Page("views/logistics.py", title="Logistique", icon=":material/local_shipping:"),
        st.Page("views/satisfaction.py", title="Satisfaction", icon=":material/star_half:"),
    ]
)
navigation.run()
