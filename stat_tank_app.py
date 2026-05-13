import streamlit as st
import pandas as pd
from collections import Counter
import requests

# 1. 标题配置
st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率深度过滤器 (500网同步版)")

# --- 2. 500网/官方数据联网同步逻辑 ---
@st.cache_data(ttl=3600)  # 每小时自动更新，不用手动传文件
def fetch_data_from_web():
    try:
        # 对接官方/500网通用数据源接口
        url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()['value']['list']
        
        # 提取期号和红球
        clean_data = []
        for item in data:
            nums = item['lotteryDrawResult'].split(' ')
            clean_data.append({
                "期号": item['lotteryDrawNum'],
                "红球": " ".join(nums[:5])
            })
        return pd.DataFrame(clean_data)
    except Exception as e:
        st.error(f"📡 联网同步失败: {e}")
        return pd.DataFrame()

# 自动执行同步
with st.spinner('📡 正在联网抓取最新数据...'):
    df = fetch_data_from_web()

# --- 3. 统计展示逻辑 (核心) ---
if not df.empty:
    st.success(f"✅ 已同步最新：第 {df.iloc[0]['期号']} 期")
    
    # 设定统计期数 (比如29期)
    num_p = st.sidebar.number_input("统计最近期数", value=29)
    
    # 获取最近N期的号码并数数
    recent_nums = [int(n) for s in df.head(num_p)['红球'] for n in s.split()]
    counts = Counter(recent_nums)
    
    # 按照频率分组
    mapping = {}
    for i in range(1, 36):
        c = counts.get(i, 0)
        mapping.setdefault(c, []).append(i)
    
    # 视觉化输出 (还原图片格式)
    for freq in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[freq])])
        color = "#FF4B4B" if freq >= 5 else ("#9FA8DA" if freq == 0 else "#31333F")
        
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="background-color: {color}; color: white; padding: 5px 15px; border-radius: 5px; font-weight: bold; width: 80px; text-align: center;">
                {freq} 次
            </div>
            <div style="margin-left: 20px; font-size: 22px; font-family: monospace; font-weight: bold;">
                {nums_str}
            </div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.warning("⚠️ 没抓到数据，请检查网络或稍后刷新。")
