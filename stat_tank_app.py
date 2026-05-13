import streamlit as st
import pandas as pd
from collections import Counter
import requests

# 1. 基础配置
st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率深度过滤器 (稳定版)")

# --- 2. 联网同步函数（加了保护，不会崩溃） ---
@st.cache_data(ttl=600)
def fetch_lotto_data():
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            raw_list = response.json().get('value', {}).get('list', [])
            return pd.DataFrame([{"期号": i['lotteryDrawNum'], "红球": " ".join(i['lotteryDrawResult'].split()[:5])} for i in raw_list])
    except:
        return pd.DataFrame()
    return pd.DataFrame()

# --- 3. 运行同步 ---
df_raw = fetch_lotto_data()

# 如果同步失败，给一个友好的提示，而不是报错
if df_raw.empty:
    st.error("🚨 官方接口暂时连接不上（可能是服务器维护）。")
    st.info("💡 请尝试刷新页面，或者稍后再试。您的‘坦克’依然安全！")
else:
    # 正常统计逻辑
    st.success(f"✅ 数据同步成功：最新第 {df_raw.iloc[0]['期号']} 期")
    num_p = st.sidebar.number_input("统计最近期数", value=29)
    
    recent = df_raw.head(num_p)
    all_reds = [int(n) for s in recent['红球'] for n in s.split()]
    counts = Counter(all_reds)
    
    # 按照频率从高到低显示
    max_f = max(counts.values()) if counts else 0
    for f in range(max_f, -1, -1):
        nums = [f"{i:02d}" for i in range(1, 36) if counts.get(i, 0) == f]
        if nums:
            color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
            st.markdown(f"""<div style="display:flex; align-items:center; margin-bottom:10px;">
                <div style="background-color:{color}; color:white; padding:5px 15px; border-radius:5px; font-weight:bold; width:80px; text-align:center;">{f} 次</div>
                <div style="margin-left:20px; font-size:20px; font-family:monospace; font-weight:bold;">{' '.join(nums)}</div>
            </div>""", unsafe_allow_html=True)
