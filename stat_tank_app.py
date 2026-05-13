import streamlit as st
import pandas as pd
from collections import Counter
import requests

st.set_page_config(page_title="数据频率演算终端", layout="wide")
st.title("📊 大数据频率深度过滤器 (防死机加强版)")

# --- 1. 核心抓取函数（带防空值保护） ---
@st.cache_data(ttl=600)
def safe_fetch():
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1"
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            json_data = r.json()
            # 关键保护：先确认数据里有没有东西
            if json_data and 'value' in json_data and 'list' in json_data['value']:
                raw_list = json_data['value']['list']
                if raw_list:
                    return pd.DataFrame([{"期号": i['lotteryDrawNum'], "红球": " ".join(i['lotteryDrawResult'].split()[:5])} for i in raw_list])
    except Exception as e:
        print(f"Fetch Error: {e}")
    return pd.DataFrame() # 哪怕失败，也返回一个空的表格，而不是 None

# --- 2. 运行抓取 ---
df = safe_fetch()

# --- 3. 统计展示（加了 df.empty 判断，绝对不会再报 NoneType 错） ---
if not df.empty:
    st.success(f"✅ 数据同步成功：最新第 {df.iloc[0]['期号']} 期")
    
    num_p = st.sidebar.number_input("统计最近期数", value=29, min_value=1)
    # 统计逻辑...
    recent_nums = [int(n) for s in df.head(num_p)['红球'] for n in s.split() if n.isdigit()]
    counts = Counter(recent_nums)
    
    # 频率分组展示
    for f in range(max(counts.values() or [0]), -1, -1):
        nums = [f"{i:02d}" for i in range(1, 36) if counts.get(i, 0) == f]
        if nums:
            color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
            st.markdown(f"""<div style="display:flex;align-items:center;margin-bottom:10px;">
                <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:80px;text-align:center;">{f} 次</div>
                <div style="margin-left:20px;font-size:20px;font-family:monospace;font-weight:bold;">{' '.join(nums)}</div>
            </div>""", unsafe_allow_html=True)
else:
    st.error("🚨 自动抓取受阻（网络连接超时）。")
    st.info("💡 解决办法：\n1. 请点击网页右上角三个点 -> 选择 'Clear cache'。\n2. 然后点击 'Rerun'。\n3. 多试1-2次通常就能穿透过去。")
