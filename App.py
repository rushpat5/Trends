import time
import streamlit as st
import pandas as pd
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError, TooManyRequestsError

def apply_styles():
    st.markdown(
        """
        <style>
        :root {
            --bg: #121212;
            --sidebar-bg: #1e1e1e;
            --text: #e0e0e0;
            --accent: #bb86fc;
        }
        body {
            background-color: var(--bg);
            color: var(--text);
        }
        .stSidebar {
            background-color: var(--sidebar-bg);
            color: var(--text);
        }
        .stSidebar .stTextInput>div>div>input {
            background-color: #2a2a2a;
            color: var(--text);
        }
        .stButton>button {
            background-color: var(--accent);
            color: #000;
            font-weight: bold;
            padding: 0.6em 1.0em;
            border-radius: 0.4em;
        }
        .stButton>button:hover {
            background-color: #9a54d6;
        }
        .main-title { text-align:center; font-size:2.5rem; margin-top:1.5rem; color:var(--accent); }
        .subtitle { text-align:center; font-size:1.1rem; color:#a0a0a0; margin-bottom:2rem; }
        .card {
            background-color:#1e1e1e;
            padding:1.4rem;
            border-radius:0.6rem;
            margin-bottom:1.8rem;
        }
        .footer { text-align:center; margin-top:3rem; color:#777777; font-size:0.9rem; }
        .error { color:#ff5555; font-weight:bold; }
        </style>
        """, unsafe_allow_html=True
    )

@st.cache_data(show_spinner=False)
def fetch_trends(keywords, timeframe_label, geo='IN', proxy_list=None,
                 max_retries=5, initial_backoff=15):
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

    # Setup TrendReq with optional proxies
    if proxy_list:
        # user supplies one or multiple proxies e.g. ["https://ip:port", ...]
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25),
                            retries=0, backoff_factor=0,
                            proxies=proxy_list)
    else:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25),
                            retries=max_retries, backoff_factor=initial_backoff)

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

def main():
    st.set_page_config(page_title="Keyword Trend Tracker", layout="wide")
    apply_styles()
    st.markdown("<div class='main-title'>Keyword Trend Tracker</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Track & compare search interest trends effortlessly.</div>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("🔧 Input Settings")
        raw = st.text_input("Keywords (comma-separated)", value="fancy number, another phrase",
                            help="Enter up to 5 keywords separated by commas. Multi-word keywords allowed.")
        timeframe_choice = st.selectbox("Select Timeframe",
                                        ['Last 7 days', 'Last 1 month', 'Last 12 months'],
                                        index=2,
                                        help="Choose timeframe for trend data.")
        geo = st.text_input("Geo (2-letter country code)", value="IN",
                            help="Default is IN (India).")
        use_proxy = st.checkbox("Use proxy", value=False,
                                help="Enable only if you have one or more HTTPS proxies to use.")
        proxy_input = st.text_area("Proxy list (one per line)", value="",
                                   help="Enter one or more proxies (HTTPS) if 'Use proxy' is enabled.")
        fetch_btn = st.button("🔍 Fetch Trends", use_container_width=True)

    if fetch_btn:
        keywords = [k.strip() for k in raw.split(',') if k.strip()]
        proxy_list = None
        if use_proxy:
            raw_proxies = [p.strip() for p in proxy_input.splitlines() if p.strip()]
            if not raw_proxies:
                st.error("Proxy enabled but no valid proxies provided.", icon="⚠️")
                return
            proxy_list = raw_proxies

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        try:
            st.info(f"Fetching: {keywords} | Timeframe: {timeframe_choice} | Geo: {geo.strip().upper()}")
            df = fetch_trends(keywords, timeframe_choice, geo, proxy_list)
        except ValueError as ve:
            st.error(f"Input error: {ve}", icon="🚫")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        except RuntimeError as re:
            st.error(f"API error: {re}", icon="🚫")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        except Exception as e:
            st.error(f"Unexpected error: {e}", icon="🚫")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📊 Trend Chart")
        st.line_chart(df)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📋 Raw Data Table")
        st.dataframe(df.reset_index())
        csv = df.to_csv(index=True).encode('utf-8')
        st.download_button(label="Download CSV", data=csv, file_name='keyword_trends.csv',
                           mime='text/csv', use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='footer'>© 2025 Keyword Trend Tracker</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
