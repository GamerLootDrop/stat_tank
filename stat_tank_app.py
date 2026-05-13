import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="数据频率演算终端", layout="wide")
st.title("📊 大数据频率深度过滤器 (双模版)")

# --- 1. 自动识别并加载数据 ---
def load_dual_engine_data():
    # 尝试寻找大乐透或双色球的文件
    files = [f for f in os.listdir('.') if f.endswith('.csv')]
    # 优先找当前选中的类型
    return files

file_list = load_dual_engine_data()
target_file = st.sidebar.selectbox("📂 选择要演算的数据源", file_list if file_list else ["未找到CSV文件"])

def process_file(file_path):
    try:
        df = pd.read_csv(file_path, skiprows=1)
        df = df.dropna(subset=['开奖期号'])
        df = df.sort_values(by='开奖期号', ascending=False)
        return df
    except:
        return pd.DataFrame()

# --- 2. 核心演算逻辑 ---
if "未找到" not in target_file:
    df_source = process_file(target_file)
    
    if not df_source.empty:
        # 自动判断是双色球还是大乐透
        is_ssq = "ssq" in target_file.lower() or "双色球" in target_file
        game_name = "🔴 双色球" if is_ssq else "🟢 大乐透"
        max_num = 33 if is_ssq else 35
        red_count = 6 if is_ssq else 5
        
        st.success(f"✅ 已载入 {game_name} 数据 | 最新期：{df_source.iloc[0]['开奖期号']}")
        
        num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1)
        recent = df_source.head(num_p)
        
        # 提取前区号码 (跳过期号和日期，取后面的红球列)
        all_reds = []
        for _, row in recent.iterrows():
            # 这里的索引 2:2+red_count 自动适配 5个号或6个号
            line = row.iloc[2:2+red_count].values
            all_reds.extend([int(float(n)) for n in line if pd.notna(n)])

        counts = Counter(all_reds)
        
        # 频率分组
        mapping = {c: [] for c in range(max(counts.values() or [0]) + 1)}
        for i in range(1, max_num + 1):
            mapping[counts.get(i, 0)].append(i)

        st.subheader(f"📅 {game_name} 最近 {num_p} 期频率")
        for f in sorted(mapping.keys(), reverse=True):
            nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
            color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
            st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:10px;"><div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:120px;text-align:center;">{f} 次出现</div><div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div></div>', unsafe_allow_html=True)

        if st.button(f"💾 记录当前 {game_name} 快照"):
            st.balloons()
            st.toast("已记入历史账本！")
else:
    st.info("💡 请把 Excel 刷新后的 CSV 文件(文件名带ssq或dlt)拖进 GitHub 仓库。")
