import streamlit as st

st.text_input("Starting destination")
st.number_input("Budget (e.g., in USD)", min_value=0)
st.date_input("Time frame (Start Date)")
st.date_input("Time frame (End Date)")
st.number_input("Number of adults", min_value=1, step=1)
st.number_input("Number of children", min_value=0, step=1)
st.selectbox("Type of trip (Initial Idea)", ["e.g., Beach holiday", "Relaxing family holiday", "Adventure trip", "Cultural exploration", "City break", "Other"])
st.text_area("Cities you already want to visit (optional, comma-separated)")
st.text_area("Attractions you already want to visit (optional, comma-separated)")
st.button("Get Initial Suggestions")