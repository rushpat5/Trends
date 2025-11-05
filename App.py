import time
import streamlit as st
import pandas as pd
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError, TooManyRequestsError

def apply_styles():
    st.markdown(
        """
        <style>
        .main-title { text-align: center; font-size: 3rem; margin-top: 1rem; color: #BB86FC; }
        .subtitle { text-align: center; font-size: 1.2rem; color: #E0E0E0; margin-bottom:2rem; }
        .card {
            background-color: #1E1E1E;
            padding: 1.5rem;
            border-radius: 0.6rem;
            margin-bottom: 2rem;
        }
        .input-area {
            background-color: #1E1E1E;
            padding: 2rem;
            border-radius: 0.6rem;
        }
        .footer { text-align: center; margin-top:3rem; color:#888888; font-size:0.9rem; }
        </style>
        """,
        unsafe_allow_html=True
    )

@st.cache_data(show_spinner=False)
def fetch_trends(keywords, timeframe_label, geo='IN', max_retries=4, initial_backoff=10):
    if not keywords:
        raise ValueError("Enter at least one keyword.")
    if len(keywords) > 5:
        raise ValueError("Maximum of 5 keywords allowed.")
    for kw in keywords:
        if len(kw) > 100:
            raise ValueError(f"Keyword too long (max 100 chars): '{kw}'")
    geo_code = geo.strip().upper() or 'IN'
    if len(geo_code) != 2:
        raise ValueError("Geo must be a 2-letter country code (e.g., IN, US).")

    tf_map = {
        'Last 7 days': 'now 7-d',
        'Last 1 month': 'today 1-m',
        'Last 12 months': 'today 12-m'
    }
    if timeframe_label not in tf_map:
        raise ValueError("Invalid timeframe selection.")
    timeframe = tf_map[timeframe_label]

    pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25))
    attempt = 0
    while attempt < max_retries:
        try:
            pytrends.build_payload(keywords, timeframe=timeframe, geo=geo_code)
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
        except ResponseError as e:
            raise RuntimeError(f"Google Trends API error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}") from e
    raise RuntimeError(f"Too many requests. Aborted after {max_retries} attempts.")

def main():
    st.set_page_config(page_title="Keyword Trend Tracker", layout="wide")
    apply(styles=True)
    st.markdown("<div class='main-title'>Keyword Trend Tracker</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Enter keywords to see search interest trends.</div>", unsafe_allow_html=True)

    with st.container():
        with st.sidebar:
            st.markdown("<div class='input-area'>", unsafe_allow_html=True)
            st.header("Input Settings")
            raw = st.text_input("Keywords (comma-separated)", value="fancy number, another phrase", help="Enter up to 5 keywords separated by commas.")
            timeframe_choice = st.selectbox("Select Timeframe", ['Last 7 days', 'Last 1 month', 'Last 12 months'], index=2, help="Choose how far back to fetch data.")
            geo = st.text_input("Geo (2-letter country code)", value="IN", help="Default is IN (India).")
            fetch_btn = st.button("🔍 Fetch Trends", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if fetch_btn:
            keywords = [k.strip() for k in raw.split(',') if k.strip()]
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            try:
                st.info(f"Fetching trends for: {keywords} | Timeframe: {timeframe_choice} | Geo: {geo.strip().upper() or 'IN'}")
                df = fetch_trends(keywords, timeframe_choice, geo)
            except ValueError as ve:
                st.error(f"Input error: {ve}")
                st.markdown("</div>", unsafe_allow_html=True)
                return
            except RuntimeError as re:
                st.error(f"API error: {re}")
                st.markdown("</div>", unsafe_allow_html=True)
                return
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.markdown("</div>", unsafe_allow_html=True)
                return

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("📊 Trend Chart")
            st.line_chart(df)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("📋 Raw Data")
            st.dataframe(df)
            csv = df.to_csv(index=True).encode('utf-8')
            st.download_button(label="Download CSV", data=csv, file_name='keyword_trends.csv', mime='text/csv', use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='footer'>© 2025 Keyword Trend Tracker</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()

