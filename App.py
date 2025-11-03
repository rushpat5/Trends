import streamlit as st
import pandas as pd
from pytrends.request import TrendReq

# Cache the trend fetching
@st.cache_data
def fetch_trends(keywords, timeframe='today 12-m', geo=''):
    pytrends = TrendReq(hl='en-US', tz=360)
    pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
    df = pytrends.interest_over_time()
    if 'isPartial' in df.columns:
        df = df.drop(columns=['isPartial'])
    return df

def main():
    st.set_page_config(page_title="Keyword Trend Tracker", layout="wide")
    st.title("Keyword Trend & Ranking Tracker")

    st.sidebar.header("Input parameters")
    raw = st.sidebar.text_input("Enter comma-separated keywords", "keyword1, keyword2")
    timeframe = st.sidebar.selectbox("Timeframe", ['today 7-d', 'today 1-m', 'today 12-m', 'all'])
    geo = st.sidebar.text_input("Geo (country code, e.g., US, IN)", "")

    if st.sidebar.button("Retrieve Trends"):
        keywords = [k.strip() for k in raw.split(',') if k.strip()]
        if not keywords:
            st.error("Enter at least one keyword.")
            return

        st.info(f"Fetching trends for: {keywords} | Timeframe: {timeframe} | Geo: {geo or 'Worldwide'}")
        df = fetch_trends(keywords, timeframe=timeframe, geo=geo)
        if df.empty:
            st.warning("No data returned. Try different timeframe or keywords.")
        else:
            st.subheader("Trend Data")
            st.dataframe(df)

            st.subheader("Trend Chart")
            st.line_chart(df)

            st.subheader("Download Data")
            csv = df.to_csv().encode('utf-8')
            st.download_button(
                label="Download trends as CSV",
                data=csv,
                file_name='keyword_trends.csv',
                mime='text/csv'
            )

if __name__ == "__main__":
    main()