import streamlit as st
import pandas as pd
from collections import Counter
import requests

st.set_page_config(page_title="数据频率演算终端", layout="wide")

# --- 1. 自动同步逻辑 ---
@st.cache_data(ttl=600)
def fetch_data():
    try:
        # 使用最稳的官方数据接口
        url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()['value']['list']
        return pd.DataFrame([{"期号": i['lotteryDrawNum'], "红球": " ".join(i['lotteryDrawResult'].split()[:5])} for i in data])
    except:
        return pd.DataFrame()

st.title("📊 大数据频率深度过滤器 (Pro版)")
st.markdown("---")

# 执行抓取
df = fetch_data()

# --- 2. 核心统计展示 ---
if not df.empty:
    st.success(f"✅ 联网同步成功：最新第 {df.iloc[0]['期号']} 期")
    
    num_p = st.sidebar.number_input("统计最近期数", value=29, min_value=1)
    recent_nums = [int(n) for s in df.head(num_p)['红球'] for n in s.split()]
    counts = Counter(recent_nums)
    
    # 按照频率分组显示
    for f in range(max(counts.values() or [0]), -1, -1):
        nums = [f"{i:02d}" for i in range(1, 36) if counts.get(i, 0) == f]
        if nums:
            color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <div style="background-color: {color}; color: white; padding: 5px 15px; border-radius: 5px; font-weight: bold; width: 80px; text-align: center;">{f} 次</div>
                <div style="margin-left: 20px; font-size: 20px; font-family: monospace; font-weight: bold;">{' '.join(nums)}</div>
            </div>""", unsafe_allow_html=True)
else:
    st.error("🚨 暂时没连上数据源，请稍后刷新。")
