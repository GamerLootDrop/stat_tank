import streamlit as st
import pandas as pd
from collections import Counter
import requests
import os

# 1. 仪表盘配置
st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率深度过滤器 (Pro版)")
st.markdown("---")

# 2. 联网同步函数
@st.cache_data(ttl=3600)
def fetch_lotto_data():
    try:
        url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        raw_list = response.json()['value']['list']
        data = [{"期号": i['lotteryDrawNum'], "红球": " ".join(i['lotteryDrawResult'].split(' ')[:5]), "日期": i['lotteryDrawTime']} for i in raw_list]
        return pd.DataFrame(data)
    except: return pd.DataFrame()

with st.spinner('📡 正在同步官方开奖数据...'):
    df_raw = fetch_lotto_data()

if not df_raw.empty:
    latest = df_raw.iloc[0]
    st.success(f"✅ 已同步最新：第 {latest['期号']} 期 | 号码：{latest['红球']}")

    # 3. 统计设置
    num_periods = st.sidebar.number_input("统计最近期数", value=29, min_value=1)
    
    # 核心逻辑：数数
    recent_df = df_raw.head(num_periods)
    all_reds = [int(n) for s in recent_df['红球'] for n in s.split()]
    counts = Counter(all_reds)
    
    # 4. 样式展示（还原他的图片）
    mapping = {c: [] for c in range(max(counts.values()) + 1)}
    for i in range(1, 36):
        mapping[counts.get(i, 0)].append(i)
    
    for freq in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[freq])])
        color = "#FF4B4B" if freq >= 5 else ("#9FA8DA" if freq == 0 else "#31333F")
        st.markdown(f"""<div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="background-color:{color}; color:white; padding:5px 15px; border-radius:5px; font-weight:bold; width:80px; text-align:center;">{freq} 次</div>
            <div style="margin-left:20px; font-size:20px; font-family:monospace; font-weight:bold;">{nums_str}</div>
        </div>""", unsafe_allow_html=True)

    # 5. 记录与账本
    st.markdown("---")
    st.subheader("📁 数据快照记录")
    SAVE_FILE = "stat_history.csv"

    if st.button("💾 保存当前频率快照"):
        # 记录最热和最冷的号作为备注
        hot_nums = ",".join([f"{x:02d}" for x in sorted(mapping[max(mapping.keys())])])
        new_data = {"记录日期": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), "对应期号": latest['期号'], "最热号码": hot_nums}
        df_log = pd.DataFrame([new_data])
        df_log.to_csv(SAVE_FILE, mode='a', header=not os.path.exists(SAVE_FILE), index=False)
        st.toast("✅ 已记录到账本")

    if os.path.exists(SAVE_FILE):
        st.table(pd.read_csv(SAVE_FILE).tail(5)) # 展示最近5条
else:
    st.error("同步失败，请检查网络")
