import streamlit as st
import pandas as pd
from collections import Counter
import requests
import os

# --- 1. 坦克配置 ---
st.set_page_config(page_title="数据频率演算终端", layout="wide")
st.title("📊 大数据频率深度过滤器 (Pro自动版)")

# --- 2. 联网同步引擎 ---
@st.cache_data(ttl=3600)
def fetch_data():
    try:
        url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1"
        res = requests.get(url, timeout=10).json()
        raw = res['value']['list']
        return pd.DataFrame([{"期号": i['lotteryDrawNum'], "红球": " ".join(i['lotteryDrawResult'].split()[:5])} for i in raw])
    except: return pd.DataFrame()

df_raw = fetch_data()

if not df_raw.empty:
    st.success(f"✅ 官方数据已同步至最新期")
    num_p = st.sidebar.number_input("统计最近期数", value=29)
    
    # --- 3. 频率演算逻辑 ---
    recent = df_raw.head(num_p)
    counts = Counter([int(n) for s in recent['红球'] for n in s.split()])
    mapping = {c: [] for c in range(max(counts.values()) + 1)}
    for i in range(1, 36): mapping[counts.get(i, 0)].append(i)
    
    # 视觉展示 (还原图片样式)
    for freq in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[freq])])
        color = "#FF4B4B" if freq >= 5 else ("#9FA8DA" if freq == 0 else "#31333F")
        st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:10px;"><div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:80px;text-align:center;">{freq} 次</div><div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div></div>', unsafe_allow_html=True)

    # --- 4. 自动记录账本 ---
    st.markdown("---")
    SAVE_FILE = "stat_history.csv"
    if st.button("💾 点击记录当前快照 (存档)"):
        new_record = {"时间": pd.Timestamp.now().strftime('%m-%d %H:%M'), "期号": df_raw.iloc[0]['期号'], "最热号": ",".join([f"{x:02d}" for x in mapping[max(mapping.keys())]])}
        pd.DataFrame([new_record]).to_csv(SAVE_FILE, mode='a', header=not os.path.exists(SAVE_FILE), index=False)
        st.balloons()
        st.success("账本已更新！")

    if os.path.exists(SAVE_FILE):
        st.subheader("📁 历史快照账本")
        st.table(pd.read_csv(SAVE_FILE).tail(5)) # 显示最近5条记录
