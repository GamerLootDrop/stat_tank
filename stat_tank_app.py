import streamlit as st
import pandas as pd
from collections import Counter
import requests
from datetime import datetime

# 1. 网页标题配置
st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率深度过滤器 (500网同步版)")
st.markdown("---")

# 2. 联网抓取逻辑 (核心引擎)
@st.cache_data(ttl=3600)  # 每小时缓存，避免被封IP
def sync_500_data():
    try:
        # 这里使用的是目前最稳的体育彩票官方/500网通用接口
        url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        res_json = response.json()
        raw_list = res_json['value']['list']
        
        data_list = []
        for item in raw_list:
            # 格式化提取号码
            all_nums = item['lotteryDrawResult'].split(' ')
            data_list.append({
                "期号": item['lotteryDrawNum'],
                "红球": " ".join(all_nums[:5]),
                "日期": item['lotteryDrawTime']
            })
        return pd.DataFrame(data_list)
    except Exception as e:
        st.error(f"📡 联网同步失败: {e}")
        return pd.DataFrame()

# 执行联网同步
with st.spinner('📡 正在联网抓取最新开奖数据...'):
    df_raw = sync_500_data()

# 3. 统计展示逻辑
if not df_raw.empty:
    latest = df_raw.iloc[0]
    st.success(f"✅ 已同步最新数据：第 {latest['期号']} 期 ({latest['日期']})")

    # 侧边栏：统计期数设置
    st.sidebar.header("⚙️ 统计设置")
    num_periods = st.sidebar.number_input("统计最近期数", value=29, min_value=1, max_value=100)

    # 核心演算：计算频率
    recent_df = df_raw.head(num_periods)
    all_red_nums = [int(x) for s in recent_df['红球'] for x in s.split()]
    counts = Counter(all_red_nums)

    # 还原图片中的频率分组格式
    mapping = {}
    for i in range(1, 36):
        c = counts.get(i, 0)
        if c not in mapping: mapping[c] = []
        mapping[c].append(i)

    st.subheader(f"📅 最近 {num_periods} 期频率分布 (前区红球)")
    
    # 按照频率从高到低排列
    for freq in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[freq])])
        
        # 颜色区分：高频红，0次蓝，普通黑
        if freq >= 5: color = "#FF4B4B"
        elif freq == 0: color = "#9FA8DA"
        else: color = "#31333F"
        
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 12px;">
            <div style="background-color: {color}; color: white; padding: 6px 15px; border-radius: 5px; font-weight: bold; width: 90px; text-align: center;">
                {freq} 次
            </div>
            <div style="margin-left: 20px; font-size: 22px; font-family: monospace; font-weight: bold;">
                {nums_str}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("数据来源：官方联网实时同步 · 演算终端")
else:
    st.warning("⚠️ 接口响应慢，请点右上角三个点选择 'Rerun' 重新加载。")
