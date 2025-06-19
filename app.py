import streamlit as st
import pandas as pd
import webbrowser
import urllib.parse
import time
import shutil
import os

st.set_page_config(page_title="Subsidiary Search Automation", page_icon="🔍", layout="centered")

st.title("🔍 Subsidiary Search Automation")
st.markdown("""
Upload your CSV file with columns **Account Name** and **Parent Name**. Select the range of queries you want to open in Chrome tabs.
""")

# Try to register Chrome as the browser
CHROME_PATHS = [
    shutil.which('chrome'),
    shutil.which('chrome.exe'),
    r'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    r'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\\Google\\Chrome\\Application\\chrome.exe'),
]
chrome_path = next((p for p in CHROME_PATHS if p and shutil.which(p) or (p and os.path.exists(p))), None)
if chrome_path:
    webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
    BROWSER = 'chrome'
else:
    BROWSER = None

def create_search_query(account_name, parent_name):
    return f"Is {account_name} a subsidiary of the {parent_name}?"

def create_google_search_url(query):
    encoded_query = urllib.parse.quote_plus(query)
    return f"https://www.google.com/search?q={encoded_query}"

def open_search_in_browser(url, delay=1):
    try:
        if BROWSER:
            webbrowser.get(BROWSER).open_new_tab(url)
        else:
            webbrowser.open_new_tab(url)
        time.sleep(delay)
        return True
    except Exception as e:
        st.error(f"Failed to open URL: {url}. Error: {e}")
        return False

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

    search_queries = [create_search_query(row['Account Name'], row['Parent Name']) for _, row in df.iterrows()]
    search_urls = [create_google_search_url(q) for q in search_queries]
    total = len(search_urls)

    st.success(f"CSV loaded successfully! {total} queries found.")
    st.dataframe(df[['Account Name', 'Parent Name']].head(10), use_container_width=True)

    st.markdown("---")
    st.subheader("Select Range to Open in Chrome Tabs")
    col1, col2 = st.columns(2)
    with col1:
        start = st.number_input("Start Index (1-based)", min_value=1, max_value=total, value=1, step=1)
    with col2:
        end = st.number_input("End Index (inclusive, 1-based)", min_value=1, max_value=total, value=min(10, total), step=1)

    if start > end:
        st.warning("Start index cannot be greater than end index.")
    else:
        if st.button(f"Open Searches {start} to {end} in Chrome Tabs", type="primary"):
            with st.spinner(f"Opening searches {start} to {end} in Chrome tabs..."):
                for i, url in enumerate(search_urls[start-1:end], start):
                    open_search_in_browser(url, delay=1)
                st.success(f"Opened searches {start} to {end} in Chrome tabs!")
                st.info("If tabs did not open, make sure Chrome is installed and set as your default browser.")
else:
    st.info("Please upload a CSV file to begin.") 