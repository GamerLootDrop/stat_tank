import streamlit as st
import pandas as pd
from collections import Counter
import requests

# 1. 标题与页面设置
st.set_page_config(page_title="数据频率演算终端", layout="wide")
st.title("📊 大数据频率深度过滤器 (超级穿透版)")

# --- 2. 核心：多线路同步引擎 ---
@st.cache_data(ttl=600)
def super_fetch():
    # 线路1：官方备用通道
    urls = [
        "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1",
        "https://m.sporttery.cn/api/lottery_draw_num.php?gameNo=85" # 模拟手机版接口，更容易过墙
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
    }

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                # 兼容不同接口的字段名
                raw_list = data.get('value', {}).get('list', []) or data.get('list', [])
                if raw_list:
                    return pd.DataFrame([{"期号": i.get('lotteryDrawNum', '未知'), "红球": " ".join(i.get('lotteryDrawResult', '').split()[:5])} for i in raw_list])
        except:
            continue
    return pd.DataFrame()

# 执行抓取
with st.spinner('📡 正在通过多条线路同步数据，请稍候...'):
    df_raw = super_fetch()

# --- 3. 统计展示 ---
if not df_raw.empty:
    st.success(f"✅ 线路同步成功！最新期号：{df_raw.iloc[0]['期号']}")
    
    num_p = st.sidebar.number_input("统计最近期数", value=29, min_value=1)
    recent = df_raw.head(num_p)
    all_reds = [int(n) for s in recent['红球'] for n in s.split() if n.isdigit()]
    counts = Counter(all_reds)
    
    # 分组显示逻辑
    for f in range(max(counts.values() or [0]), -1, -1):
        nums = [f"{i:02d}" for i in range(1, 36) if counts.get(i, 0) == f]
        if nums:
            color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
            st.markdown(f"""<div style="display:flex;align-items:center;margin-bottom:10px;">
                <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:80px;text-align:center;">{f} 次</div>
                <div style="margin-left:20px;font-size:20px;font-family:monospace;font-weight:bold;">{' '.join(nums)}</div>
            </div>""", unsafe_allow_html=True)
else:
    st.error("🚨 线路暂时全部拥堵！")
    st.info("💡 解决办法：请点击网页右上角三个点 -> 选择 'Rerun'。通常尝试 2-3 次即可穿透网络墙。")
