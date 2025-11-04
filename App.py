import time
import streamlit as st
import pandas as pd
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError, TooManyRequestsError

@st.cache_data(show_spinner=False)
def fetch_trends(keywords, timeframe='today 12-m', geo='IN', max_retries=3, backoff_sec=5):
    # Validate keywords list
    if not keywords:
        raise ValueError("Keyword list is empty.")
    if len(keywords) > 5:
        raise ValueError("Maximum of 5 keywords allowed at once.")
    for kw in keywords:
        if not isinstance(kw, str) or not kw.strip():
            raise ValueError(f"Invalid keyword: '{kw}'")
        if len(kw) > 100:
            raise ValueError(f"Keyword too long (100 chars max): '{kw}'")
    # Validate geo
    geo = geo.strip().upper() or 'IN'
    if len(geo) != 2:
        raise ValueError(f"Invalid geo code '{geo}'. Use two-letter country code or leave blank.")
    # Validate timeframe
    if not (timeframe.startswith('now ') or timeframe.startswith('today ') or ' ' in timeframe and timeframe[0:4].isdigit()):
        raise ValueError(f"Invalid timeframe format '{timeframe}'. Examples: 'now 7-d', 'today 1-m', '2023-01-01 2023-12-31'")
    # Prepare pytrends
    pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25))
    # Retry logic
    attempt = 0
    while attempt < max_retries:
        try:
            pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            df = pytrends.interest_over_time()
            if df is None or df.empty:
                raise RuntimeError("Returned data is empty.")
            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])
            return df
        except TooManyRequestsError as e:
            attempt += 1
            if attempt >= max_retries:
                raise RuntimeError(f"Too many requests error after {attempt} attempts: {e}")
            time.sleep(backoff_sec * attempt)
            continue
        except ResponseError as e:
            raise RuntimeError(f"Google Trends API returned error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}") from e

def main():
    st.set_page_config(page_title="Keyword Trend Tracker", layout="wide")
    st.title("Keyword Trend Tracker")
    st.sidebar.header("Input parameters")
    raw_input = st.sidebar.text_input("Enter comma-separated keywords", "fancy number, another keyword")
    timeframe = st.sidebar.selectbox("Timeframe", ['now 7-d', 'today 1-m', 'today 12-m', 'YYYY-MM-DD YYYY-MM-DD'])
    geo = st.sidebar.text_input("Geo (2-letter country code)", "IN")

    if st.sidebar.button("Fetch Trends"):
        # Parse keywords (keep multi-word intact)
        keywords = [k.strip() for k in raw_input.split(',') if k.strip()]
        try:
            st.info(f"Fetching trends for: {keywords} | Timeframe: {timeframe} | Geo: {geo or 'IN'}")
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

        st.subheader("Trend Data")
        st.dataframe(df)

        st.subheader("Trend Chart")
        st.line_chart(df)

        st.subheader("Download Data as CSV")
        csv = df.to_csv(index=True).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name='keyword_trends.csv',
            mime='text/csv'
        )

if __name__ == "__main__":
    main()
