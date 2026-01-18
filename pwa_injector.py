import streamlit as st
import streamlit.components.v1 as components

# --- PWA設定の埋め込み (ここから) ---
# pwa_injector.py の冒頭部分を以下に書き換え
def enable_pwa():
    pwa_js = """
    <script>
    // 1. Manifestを動的に生成して注入
    const manifest = {
      "name": "株価分析アプリ",
      "short_name": "株価分析",
      "start_url": "/",
      "display": "standalone",
      "background_color": "#ffffff",
      "theme_color": "#ff4b4b",
      "icons": [{
        "src": "https://raw.githubusercontent.com/kidsmindjp/stock-analysis-app/main/icon.png",
        "sizes": "512x512",
        "type": "image/png",
        "purpose": "any"
      }]
    };
    const stringManifest = JSON.stringify(manifest);
    const blob = new Blob([stringManifest], {type: 'application/json'});
    const manifestURL = URL.createObjectURL(blob);
    const linkTag = document.createElement('link');
    linkTag.rel = 'manifest';
    linkTag.href = manifestURL;
    document.head.appendChild(linkTag);

    // 2. Apple用（iOS）アイコンの設定
    const appleLink = document.createElement('link');
    appleLink.rel = 'apple-touch-icon';
    appleLink.href = 'https://raw.githubusercontent.com/kidsmindjp/stock-analysis-app/main/icon.png';
    document.head.appendChild(appleLink);

    // 3. 一般的なfaviconの設定
    const faviconLink = document.createElement('link');
    faviconLink.rel = 'icon';
    faviconLink.href = 'https://raw.githubusercontent.com/kidsmindjp/stock-analysis-app/main/icon.png';
    document.head.appendChild(faviconLink);

    // 4. Service Workerの登録（エラーを無視するように設定）
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/service-worker.js').catch(function(err) {
        console.log('SW registration skipped or failed: ', err);
      });
    }
    </script>
    """
    components.html(pwa_js, height=0, width=0)

enable_pwa()
# --- PWA設定の埋め込み (ここまで) ---

# 画像のデザインを再現するヘッダー部分
#col1, col2 = st.columns([3, 1])

#with col1:
#    st.markdown("# 株価分析アプリ")

#with col2:
    # 右側の「streamlitApp」バッジのような表示
#    st.code("streamlitApp")

# 今後ここに株価分析のロジックを追加していきます
# ...残りのコード
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date, timedelta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 基本設定 ---
st.set_page_config(page_title="株価分析ツール | Logic Edition", layout="wide")

st.markdown("""
    <style>
    .logic-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 20px; }
    .price-card { font-size: 1.2em; font-weight: bold; padding: 10px; border-radius: 5px; text-align: center; color: white; }
    </style>
    """, unsafe_allow_html=True)

MARKET_MAP = {
    "日本 (東証)": ".T",
    "米国 (NYSE/NASDAQ)": "",
    "直接入力": ""
}

# --- 2. データ取得とテクニカル計算 ---
@st.cache_data(ttl=timedelta(hours=6))
def get_logic_stock_data(ticker_code):
    try:
        ticker = yf.Ticker(ticker_code)
        hist = ticker.history(period="2y")
        if hist.empty: return None, None

        df = hist.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 指標計算
        df['EMA25'] = df['Close'].ewm(span=25, adjust=False).mean()
        df['EMA75'] = df['Close'].ewm(span=75, adjust=False).mean()

        # ATR (14日間) の計算
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR'] = true_range.rolling(14).mean()

        info = ticker.info
        f_data = {
            "名前": info.get("longName") or ticker_code,
            "通貨": info.get("currency", "JPY")
        }
        return df.dropna(), f_data
    except:
        return None, None

# --- 3. メインUI ---
st.title("📊 Logic-Based Strategy")

with st.sidebar:
    market_choice = st.selectbox("市場", list(MARKET_MAP.keys()))
    ticker_input = st.text_input("コード", placeholder="7203 / AAPL").upper()
    ticker_code = f"{ticker_input}{MARKET_MAP[market_choice]}" if ticker_input else ""
    submit_btn = st.button("ロジック分析実行", type="primary")

if submit_btn and ticker_code:
    df, f_data = get_logic_stock_data(ticker_code)

    if df is not None:
        # --- ロジック計算部 ---
        last_row = df.iloc[-1]
        entry_price = round(last_row['Close'], 2)
        atr_val = last_row['ATR']

        # ロジック: 損切は2×ATR、利確はリスクの1.5倍（リスクリワード 1:1.5）
        risk_amount = atr_val * 2
        sl_price = round(entry_price - risk_amount, 2)
        tp_price = round(entry_price + (risk_amount * 1.5), 2)

        # --- 表示エリア ---
        st.subheader(f"🔍 {f_data['名前']} 戦略シミュレーション")

        # 数値カード表示
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div class='price-card' style='background-color:#007bff'>エントリー目安<br>{entry_price}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='price-card' style='background-color:#28a745'>利確目標 (TP)<br>{tp_price}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='price-card' style='background-color:#dc3545'>損切目安 (SL)<br>{sl_price}</div>", unsafe_allow_html=True)

        st.info(f"💡 **算出ロジック**: ボラティリティ指標ATR({atr_val:.2f})に基づき、リスクリワード比 1:1.5 で機械的に算出しています。")

        # --- チャート描画 ---
        plot_df = df.tail(100)
        fig = go.Figure()

        # ローソク足
        fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='株価'))

        # ロジックラインの描画
        fig.add_hline(y=entry_price, line_dash="dash", line_color="blue", annotation_text="Entry")
        fig.add_hline(y=tp_price, line_dash="dash", line_color="green", annotation_text="Target")
        fig.add_hline(y=sl_price, line_dash="dash", line_color="red", annotation_text="StopLoss")

        # 予測ゾーン（背景色）
        fig.add_hrect(y0=entry_price, y1=tp_price, fillcolor="green", opacity=0.1, line_width=0)
        fig.add_hrect(y0=sl_price, y1=entry_price, fillcolor="red", opacity=0.1, line_width=0)

        fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("データが取得できませんでした。")

st.divider()
st.caption("免責事項：本アプリは投資助言を行うものではありません。実際の投資判断はご自身の責任で行ってください。")
