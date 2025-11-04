import time
import streamlit as st
import pandas as pd
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError, TooManyRequestsError

@st.cache_data(show_spinner=False)
def fetch_trends(keywords, timeframe='today 12-m', geo='IN', max_retries=4, initial_backoff=15):
    # Validate keywords
    if not keywords:
        raise ValueError("Please enter at least one keyword.")
    if len(keywords) > 5:
        raise ValueError("A maximum of 5 keywords is allowed.")
    for kw in keywords:
        if len(kw) > 100:
            raise ValueError(f"Keyword too long (max 100 characters): {kw}")
    # Geo
    geo_clean = geo.strip().upper() or 'IN'
    if len(geo_clean) != 2:
        raise ValueError("Geo must be a two-letter country code (e.g., IN, US).")
    # Timeframe validation
    valid_prefixes = ('now ', 'today ')
    if not (timeframe.startswith(valid_prefixes) or (len(timeframe.split()) == 2 and timeframe.split()[0].isdigit())):
        raise ValueError("Timeframe format invalid. Use e.g., 'now 7-d', 'today 1-m', or 'YYYY-MM-DD YYYY-MM-DD'.")
    # Setup pytrends
    pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25))
    attempt = 0
    while attempt < max_retries:
        try:
            pytrends.build_payload(keywords, timeframe=timeframe, geo=geo_clean)
            df = pytrends.interest_over_time()
            if df is None or df.empty:
                raise RuntimeError("No data returned for those parameters.")
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
    st.title("Keyword Trend Tracker")

    with st.sidebar:
        st.header("Input parameters")
        raw_input = st.text_input("Enter comma-separated keywords", value="fancy number, another phrase")
        timeframe = st.selectbox("Timeframe", options=['now 7-d', 'today 1-m', 'today 12-m', 'YYYY-MM-DD YYYY-MM-DD'], index=1)
        geo = st.text_input("Geo (2-letter country code)", value="IN")
        if st.button("Fetch Trends"):
            keywords = [k.strip() for k in raw_input.split(',') if k.strip()]
            try:
                st.info(f"Fetching trends for: {keywords} | Timeframe: {timeframe} | Geo: {geo.strip().upper() or 'IN'}")
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

            st.subheader("Download Data as CSV")
            csv = df.to_csv(index=True).encode('utf-8')
            st.download_button(label="Download CSV", data=csv, file_name='keyword_trends.csv', mime='text/csv')

if __name__ == "__main__":
    main()
