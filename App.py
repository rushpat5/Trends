import streamlit as st
import pandas as pd
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError

@st.cache_data(show_spinner=False)
def fetch_trends(keywords, timeframe='today 12-m', geo=''):
    # Validate input
    if not keywords:
        raise ValueError("Keyword list is empty.")
    if len(keywords) > 5:
        raise ValueError("Maximum of 5 keywords allowed at once.")
    for kw in keywords:
        if len(kw) > 100:
            raise ValueError(f"Keyword too long (100 chars max): {kw}")
    geo = geo.strip().upper()
    if geo == '':  # treat empty as worldwide
        geo = ''
    pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
    try:
        pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
    except ResponseError as e:
        raise RuntimeError(f"Error from Google Trends API: {e}") from e
    df = pytrends.interest_over_time()
    if df is None or df.empty:
        raise RuntimeError("Returned data is empty.")
    if 'isPartial' in df.columns:
        df = df.drop(columns=['isPartial'])
    return df

def main():
    st.set_page_config(page_title="Keyword Trend Tracker", layout="wide")
    st.title("Keyword Trend Tracker")

    st.sidebar.header("Input parameters")
    raw_input = st.sidebar.text_input("Enter comma-separated keywords", "keyword1, keyword2")
    timeframe = st.sidebar.selectbox("Timeframe", ['today 7-d', 'today 1-m', 'today 12-m', 'all'])
    geo = st.sidebar.text_input("Geo (country code, e.g., IN, US)", "")

    if st.sidebar.button("Fetch Trends"):
        keywords = [k.strip() for k in raw_input.split(',') if k.strip()]
        try:
            st.info(f"Fetching trends for: {keywords} | Timeframe: {timeframe} | Geo: {geo or 'Worldwide'}")
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
