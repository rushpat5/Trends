import time
import streamlit as st
import pandas as pd
from datetime import date
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError, TooManyRequestsError

# --- UI Style (Dark Mode) ---
def inject_dark_theme():
    st.markdown(
        """
        <style>
        :root {
            --bg-color: #121212;
            --sidebar-bg: #1e1e1e;
            --text-color: #e0e0e0;
            --accent-color: #bb86fc;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
        }
        .stSidebar {
            background-color: var(--sidebar-bg);
            color: var(--text-color);
        }
        .stSidebar .stTextInput>div>div>input {
            background-color: #2a2a2a;
            color: var(--text-color);
        }
        .stButton>button {
            background-color: var(--accent-color);
            color: #000;
            font-weight: bold;
            padding: 0.6em 1.2em;
            border-radius: 0.3em;
        }
        .stButton>button:hover {
            background-color: #9a54d6;
        }
        .css-1d391kg { /* Streamlit main container */
            background-color: var(--bg-color);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Data Fetching ---
@st.cache_data(show_spinner=False)
def fetch_trends(keywords, timeframe_label, geo='IN', max_retries=4, initial_backoff=10):
    if not keywords:
        raise ValueError("Enter at least one keyword.")
    if len(keywords) > 5:
        raise ValueError("Maximum 5 keywords allowed.")
    for kw in keywords:
        if len(kw) > 100:
            raise ValueError(f"Keyword too long (100 chars max): {kw}")
    geo_code = geo.strip().upper() or 'IN'
    if len(geo_code) != 2:
        raise ValueError("Geo must be two-letter country code (e.g., IN, US).")

    # Map label → pytrends timeframe string
    tf_map = {
        'Last 7 days': 'now 7-d',
        'Last 1 month': 'today 1-m',
        'Last 12 months': 'today 12-m'
    }
    if timeframe_label not in tf_map:
        raise ValueError(f"Invalid timeframe choice: {timeframe_label}")
    timeframe = tf_map[timeframe_label]

    pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25))
    attempt = 0
    while attempt < max_retries:
        try:
            pytrends.build_payload(keywords, timeframe=timeframe, geo=geo_code)
            df = pytrends.interest_over_time()
            if df is None or df.empty:
                raise RuntimeError("No data returned for given inputs.")
            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])
            return df
        except TooManyRequestsError as e:
            attempt += 1
            delay = initial_backoff * (2 ** (attempt - 1))
            time.sleep(delay)
            continue
        except ResponseError as e:
            raise RuntimeError(f"Google Trends API error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}") from e
    raise RuntimeError(f"Too many requests. Aborted after {max_retries} attempts.")

# --- Main App ---
def main():
    st.set_page_config(page_title="Keyword Trend Tracker", layout="wide")
    inject_dark_theme()
    st.markdown("<h1 style='text-align:center;color:#bb86fc;'>Keyword Trend Tracker</h1>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("Input Parameters")
        raw = st.text_input("Keywords (comma-separated)", value="fancy number, another phrase")
        timeframe_choice = st.selectbox("Select Timeframe", ['Last 7 days', 'Last 1 month', 'Last 12 months'], index=2)
        geo = st.text_input("Geo (2-letter country code)", value="IN")
        if st.button("Fetch Trends"):
            keywords = [k.strip() for k in raw.split(',') if k.strip()]
            try:
                st.info(f"Fetching trends for: {keywords} | Timeframe: {timeframe_choice} | Geo: {geo.strip().upper() or 'IN'}")
                df = fetch_trends(keywords, timeframe_choice, geo)
            except ValueError as ve:
                st.error(f"Input error: {ve}")
                return
            except RuntimeError as re:
                st.error(f"API error: {re}")
                return
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                return

            st.subheader("Trend Data Table")
            st.dataframe(df)
            st.subheader("Trend Chart")
            st.line_chart(df)
            csv = df.to_csv(index=True).encode('utf-8')
            st.download_button(label="Download CSV", data=csv, file_name='keyword_trends.csv', mime='text/csv')

if __name__ == "__main__":
    main()
