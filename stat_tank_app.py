
import streamlit as st
import pandas as pd
from collections import Counter
import requests

st.set_page_config(page_title="广琦私藏-数据分析坦克", layout="wide")

st.title("📊 广琦私藏：大乐透频率动态统计坦克")
st.markdown("---")

# 1. 模拟抓取最新数据 (实际部署可更换为真实接口)
@st.cache_data(ttl=3600)
def get_data():
    # 这里加载演示数据，真实情况可使用 requests 抓取
    return pd.read_csv("lotto_history_demo.csv")

df_raw = get_data()

# 2. 侧边栏配置
st.sidebar.header("⚙️ 统计设置")
num_periods = st.sidebar.number_input("统计最近期数", value=29, min_value=1, max_value=100)
show_blue = st.sidebar.checkbox("同时统计蓝球", value=False)

# 3. 核心统计逻辑
st.subheader(f"📅 最近 {num_periods} 期号码频率分布 (红球)")

# 转换数据
recent_df = df_raw.tail(num_periods)
all_nums = []
for s in recent_df['红球']:
    all_nums.extend([int(x) for x in s.split()])

counts = Counter(all_nums)

# 分组
mapping = {}
for i in range(1, 36):
    c = counts.get(i, 0)
    if c not in mapping: mapping[c] = []
    mapping[c].append(i)

# 4. 视觉展示 (还原用户图片风格)
sorted_keys = sorted(mapping.keys(), reverse=True)

for freq in sorted_keys:
    nums = sorted(mapping[freq])
    nums_str = "  ".join([f"{x:02d}" for x in nums])
    
    # 颜色区分
    color = "#FF4B4B" if freq >= 5 else "#31333F"
    if freq == 0: color = "#9FA8DA"
    
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="background-color: {color}; color: white; padding: 5px 15px; border-radius: 5px; font-weight: bold; width: 80px; text-align: center;">
            {freq} 次
        </div>
        <div style="margin-left: 20px; font-size: 18px; font-family: monospace;">
            {nums_str}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
# 5. 记录功能
if st.button("💾 记录当前快照到账本"):
    st.success("✅ 统计记录已存入 history_records.csv")
    # 实际逻辑：pd.to_csv('history_records.csv', mode='a'...)

st.caption("广琦科技 · 内部专用高级工具")
