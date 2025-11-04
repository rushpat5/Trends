import time
import streamlit as st
import pandas as pd
from datetime import datetime
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError, TooManyRequestsError

def inject_style():
    st.markdown(
        """
        <style>
        body {
            color: var(--text-color);
            font-family: var(--font);
        }
        .stSidebar {
            background-color: var(--secondary-background-color);
        }
        .stButton>button {
            background-color: var(--primary-color);
            color: white;
            font-weight: bold;
            padding: 0.6em 1.2em;
            border-radius: 0.3em;
        }
        .stButton>button:hover {
            background-color: #155a8a;
        }
        .app-header {
            text-align: center;
            padding: 1em 0;
        }
        .footer {
            text-align: center;
            font-size: 0.8em;
            color: #666;
            margin-top: 2em;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

@st.cache_data(show_spinner=False)
def fetch_trends(keywords, timeframe='last 12 months', geo='IN', max_retries=4, initial_backoff=15):
    if not keywords:
        raise ValueError("Enter at least one keyword.")
    if len(keywords) > 5:
        raise ValueError("Max 5 keywords allowed.")
    for kw in keywords:
        if len(kw) > 100:
            raise ValueError(f"Keyword too long (max 100 chars): '{kw}'")
    geo_clean = geo.strip().upper() or 'IN'
    if len(geo_clean) != 2:
        raise ValueError("Geo must be a 2-letter country code (e.g., IN, US).")
    # Map friendly timeframe labels to pytrends format
    tf_map = {
        'Last 7 days': 'now 7-d',
        'Last 1 month': 'today 1-m',
        'Last 12 months': 'today 12-m',
        'Custom date range': None
    }
    payload_tf = tf_map.get(timeframe)
    if timeframe == 'Custom date range':
        # Expect user to enter dates
        raise ValueError("For custom date range please use the 'Start date' and 'End date' fields.")
    pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25))
    attempt = 0
    while attempt < max_retries:
        try:
            pytrends.build_payload(keywords, timeframe=payload_tf, geo=geo_clean)
            df = pytrends.interest_over_time()
            if df is None or df.empty:
                raise RuntimeError("No data returned.")
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

def main():
    st.set_page_config(page_title="Keyword Trend Tracker", layout="wide")
    inject_style()
    st.markdown('<div class="app-header"><h1>Keyword Trend Tracker</h1></div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("Input Parameters")
        raw_input = st.text_input("Keywords (comma-separated)", value="fancy number, another phrase")
        timeframe = st.selectbox("Select Timeframe",
                                 options=['Last 7 days', 'Last 1 month', 'Last 12 months', 'Custom date range'],
                                 index=2)
        geo = st.text_input("Geo (2-letter country code)", value="IN")
        if timeframe == 'Custom date range':
            start_date = st.date_input("Start date", value=datetime.now().date().replace(year=datetime.now().year-1))
            end_date = st.date_input("End date", value=datetime.now().date())
        else:
            start_date = end_date = None
        btn = st.button("Fetch Trends")

    if btn:
        keywords = [k.strip() for k in raw_input.split(',') if k.strip()]
        try:
            if timeframe == 'Custom date range':
                tf_label = f"{start_date} to {end_date}"
                raise ValueError("Custom date range not yet implemented.")
            else:
                tf_label = timeframe
            st.info(f"Fetching trends for: {keywords} | Timeframe: {tf_label} | Geo: {geo.strip().upper() or 'IN'}")
            df = fetch_trends(keywords, timeframe=timeframe, geo=geo)
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

        st.markdown('<div class="footer">Built with Streamlit · © 2025</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
