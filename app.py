import streamlit as st
import pandas as pd
import numpy as np
import webbrowser
import urllib.parse
import time
import shutil
import os
import streamlit.components.v1 as components

st.set_page_config(page_title="Subsidiary Search Automation", page_icon="🔍", layout="centered")

st.title("🔍 Subsidiary Search Automation")
st.markdown("""
Upload your CSV file with columns **Account Name** and **Parent Name**. The application will generate Google search links for you.
""")

def create_search_query(account_name, parent_name):
    return f"Is {account_name} a subsidiary of the {parent_name}?"

def create_google_search_url(query):
    encoded_query = urllib.parse.quote_plus(query)
    return f"https://www.google.com/search?q={encoded_query}"

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    st.markdown("**Preview of uploaded file (first 10 lines):**")
    raw_lines = uploaded_file.getvalue().decode(errors='replace').splitlines()
    st.code("\n".join(raw_lines[:10]), language='text')

    sep = st.selectbox("Select the separator used in your CSV file:", options=[", (comma)", "; (semicolon)", "\t (tab)", "| (pipe)"], index=0)
    sep_map = {", (comma)": ",", "; (semicolon)": ";", "\t (tab)": "\t", "| (pipe)": "|"}
    actual_sep = sep_map[sep]

    # Reset file pointer before reading with pandas
    uploaded_file.seek(0)
    try:
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8', sep=actual_sep)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding='cp1252', sep=actual_sep)
        if df.empty or len(df.columns) < 2:
            raise ValueError("No columns to parse from file or file is empty.")
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
        st.warning("Check the file preview above and make sure you selected the correct separator and that the file is not empty.")
        st.stop()

    if not {'Account Name', 'Parent Name'}.issubset(df.columns):
        st.error("CSV must contain 'Account Name' and 'Parent Name' columns.")
        st.stop()

    # --- Data Cleaning ---
    # Strip whitespace from key columns
    df['Account Name'] = df['Account Name'].astype(str).str.strip()
    df['Parent Name'] = df['Parent Name'].astype(str).str.strip()

    # Replace empty strings with NaN for uniform handling
    df.replace('', np.nan, inplace=True)

    # Drop rows where 'Account Name' or 'Parent Name' is missing
    df.dropna(subset=['Account Name', 'Parent Name'], inplace=True)

    # Reset index after dropping rows, so iteration is clean
    df.reset_index(drop=True, inplace=True)
    
    # Check if DataFrame is empty after cleaning
    if df.empty:
        st.warning("No valid data found after cleaning. Please ensure your file has rows with both 'Account Name' and 'Parent Name' populated.")
        st.stop()
    # --- End of Data Cleaning ---

    search_queries = [create_search_query(row['Account Name'], row['Parent Name']) for _, row in df.iterrows()]
    search_urls = [create_google_search_url(q) for q in search_queries]
    total = len(search_urls)

    st.success(f"CSV loaded successfully! {total} queries found.")
    df['Search URL'] = search_urls
    st.dataframe(df[['Account Name', 'Parent Name', 'Search URL']].head(10), use_container_width=True)

    st.markdown("---")

    # Initialize session state for selections and range.
    # This block runs only when a new file is uploaded (total changes) or on first run.
    if 'selections' not in st.session_state or len(st.session_state.get('selections', [])) != total:
        st.session_state.selections = [False] * total
        st.session_state.start_range = 1
        st.session_state.end_range = min(10, total)

    def update_selections(select_all):
        st.session_state.selections = [select_all] * total

    st.subheader("Manage and Open Links")

    # --- Option 1: Open by individual selection ---
    with st.expander("Option 1: Open by Individual Selection", expanded=True):
        st.markdown("Use checkboxes below to select links, then open them here.")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.button("Select All", on_click=update_selections, args=(True,), use_container_width=True)
        with col2:
            st.button("Deselect All", on_click=update_selections, args=(False,), use_container_width=True)
        with col3:
            if st.button("Open Selected Links", use_container_width=True, type="primary"):
                selected_urls = [search_urls[i] for i, s in enumerate(st.session_state.selections) if s]
                if selected_urls:
                    js_code = "".join([f"window.open('{url}', '_blank');" for url in selected_urls])
                    components.html(f"<script>{js_code}</script>", height=0)
                    st.success(f"Attempting to open {len(selected_urls)} selected links.")
                    st.info("If new tabs did not open, please check if your browser is blocking pop-ups and allow them for this site.")
                else:
                    st.warning("No links were selected to open.")

    # --- Option 2: Open by range ---
    with st.expander("Option 2: Open a Range of Links"):
        st.markdown("Directly open a range of links without using checkboxes.")
        r_col1, r_col2, r_col3 = st.columns([1, 1, 1.5])
        with r_col1:
            st.number_input("From link #", min_value=1, max_value=total, step=1, key="start_range")
        with r_col2:
            st.number_input("To link #", min_value=1, max_value=total, step=1, key="end_range")
        with r_col3:
            st.write("&#8203;") # Vertical alignment hack
            if st.button("Open Range", use_container_width=True):
                # Adjust for 0-based indexing for slicing from session state
                start_idx = st.session_state.start_range - 1
                end_idx = st.session_state.end_range
                
                if start_idx >= end_idx:
                    st.warning("The 'From' value must be smaller than the 'To' value.")
                else:
                    range_urls = search_urls[start_idx:end_idx]
                    if range_urls:
                        js_code = "".join([f"window.open('{url}', '_blank');" for url in range_urls])
                        components.html(f"<script>{js_code}</script>", height=0)
                        st.success(f"Attempting to open links {st.session_state.start_range} through {st.session_state.end_range}.")
                        st.info("If pop-ups are blocked, please enable them for this site.")
                    else:
                        st.error("Could not find links for the specified range.")

    st.markdown("---")
    st.subheader("Generated Search Links")

    for i, (url, query) in enumerate(zip(search_urls, search_queries)):
        col1, col2 = st.columns([0.1, 3])
        with col1:
            st.session_state.selections[i] = st.checkbox(
                "select", 
                value=st.session_state.selections[i], 
                key=f"cb_{i}", 
                label_visibility="collapsed"
            )
        with col2:
            st.markdown(f"{i+1}. <a href='{url}' target='_blank'>Search for: {query}</a>", unsafe_allow_html=True)

else:
    st.info("Please upload a CSV file to begin.") 