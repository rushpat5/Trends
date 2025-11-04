import time
import streamlit as st
import pandas as pd
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError, TooManyRequestsError

@st.cache_data(show_spinner=False)
def fetch_trends(keywords, timeframe='today 12-m', geo='IN',
                 max_retries=5, initial_backoff=10, proxies=None):
    # Input validation
    if not keywords:
        raise ValueError("Keyword list is empty.")
    if len(keywords) > 5:
        raise ValueError("Maximum of 5 keywords allowed at once.")
    for kw in keywords:
        if not isinstance(kw, str) or not kw.strip():
            raise ValueError(f"Invalid keyword: '{kw}'")
        if len(kw) > 100:
            raise ValueError(f"Keyword too long (100 chars max): '{kw}'")
    geo = geo.strip().upper() or 'IN'
    if len(geo) != 2:
        raise ValueError(f"Invalid geo code '{geo}'. Use two-letter country code or leave blank.")
    if not (timeframe.startswith('now ') or timeframe.startswith('today ') or ' ' in timeframe and timeframe[0:4].isdigit()):
        raise ValueError(f"Invalid timeframe format '{timeframe}'. Examples: 'now 7-d', 'today 1-m', 'YYYY-MM-DD YYYY-MM-DD'")
    # Setup TrendReq
    if proxies:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25), proxies=proxies, retries=max_retries, backoff_factor=initial_backoff)
    else:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25), retries=max_retries, backoff_factor=initial_backoff)
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
            delay = initial_backoff * (2 ** (attempt - 1))
            time.sleep(delay)
            continue
        except ResponseError as e:
            raise RuntimeError(f"Google Trends API returned error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}") from e
    raise RuntimeError(f"Too many requests error after {max_retries} attempts.")

def main():
    st.set_page_config(page_title="Keyword Trend Tracker", layout="wide")
    st.title("Keyword Trend Tracker")

    st.sidebar.header("Input parameters")
    raw_input = st.sidebar.text_input("Enter comma-separated keywords", "fancy number, another keyword")
    timeframe = st.sidebar.selectbox("Timeframe", ['now 7-d', 'today 1-m', 'today 12-m', 'YYYY-MM-DD YYYY-MM-DD'])
    geo = st.sidebar.text_input("Geo (2-letter country code)", "IN")
    use_proxy = st.sidebar.checkbox("Use proxy (advanced)", value=False)
    proxy_input = st.sidebar.text_input("Proxy (https://user:pass@host:port) – if used", "")

    if st.sidebar.button("Fetch Trends"):
        keywords = [k.strip() for k in raw_input.split(',') if k.strip()]
        proxies = None
        if use_proxy:
            if not proxy_input.strip():
                st.error("Proxy enabled but no proxy provided.")
                return
            proxies = {
                'https': proxy_input.strip()
            }
        try:
            st.info(f"Fetching trends for: {keywords} | Timeframe: {timeframe} | Geo: {geo}")
            df = fetch_trends(keywords, timeframe=timeframe, geo=geo, proxies=proxies)
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
