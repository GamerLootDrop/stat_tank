import streamlit as st
import pandas as pd
from collections import Counter
import requests
from datetime import datetime

# 1. 网页配置
st.set_page_config(page_title="数据频率演算终端", layout="wide")
st.title("📊 大数据频率深度过滤器 (Pro自动版)")
st.markdown("---")

# 2. 联网同步函数
@st.cache_data(ttl=3600)
def fetch_real_lotto_data():
    try:
        # 对接官方接口
        url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        res_json = response.json()
        raw_list = res_json['value']['list']
        data_list = []
        for item in raw_list:
            all_nums = item['lotteryDrawResult'].split(' ')
            data_list.append({
                "期号": item['lotteryDrawNum'],
                "红球": " ".join(all_nums[:5]),
                "日期": item['lotteryDrawTime']
            })
        return pd.DataFrame(data_list)
    except Exception as e:
        return pd.DataFrame()

# 运行同步
with st.spinner('📡 正在联网同步最新开奖数据...'):
    df_raw = fetch_real_lotto_data()

if not df_raw.empty:
    latest = df_raw.iloc[0]
    st.success(f"✅ 同步成功：第 {latest['期号']} 期 | 号码：{latest['红球']}")
    
    # 3. 侧边栏
    num_periods = st.sidebar.number_input("统计最近期数", value=29, min_value=1, max_value=100)
    
    # 4. 统计逻辑
    st.subheader(f"📅 最近 {num_periods} 期频率分布 (前区红球)")
    recent_df = df_raw.head(num_periods)
    all_reds = [int(x) for s in recent_df['红球'] for x in s.split()]
    counts = Counter(all_reds)
    
    mapping = {c: [] for c in range(max(counts.values()) + 1) if c >= 0}
    for i in range(1, 36):
        c = counts.get(i, 0)
        if c not in mapping: mapping[c] = []
        mapping[c].append(i)
        
    # 5. 视觉展示
    for freq in sorted(mapping.keys(), reverse=True):
        nums = sorted(mapping[freq])
        nums_str = "  ".join([f"{x:02d}" for x in nums])
        color = "#FF4B4B" if freq >= 5 else ("#9FA8DA" if freq == 0 else "#31333F")
        
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="background-color: {color}; color: white; padding: 5px 15px; border-radius: 5px; font-weight: bold; width: 80px; text-align: center;">
                {freq} 次
            </div>
            <div style="margin-left: 20px; font-size: 20px; font-family: monospace; font-weight: bold;">
                {nums_str}
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.error("⚠️ 暂时无法获取数据，请刷新页面。")
