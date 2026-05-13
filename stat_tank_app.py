import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率实时过滤器 (全自动适配版)")

# --- 1. 自动寻找仓库里的 CSV 文件 ---
def find_and_load_data():
    # 获取当前文件夹下所有文件
    all_files = os.listdir('.')
    # 找名字里带 data 或 dlt 的 csv 文件
    csv_files = [f for f in all_files if f.endswith('.csv')]
    
    if csv_files:
        # 选第一个找到的文件
        target = csv_files[0]
        try:
            # 适配您的表格模式：跳过第一行，读数据
            df = pd.read_csv(target, skiprows=1)
            # 找第一列作为期号
            id_col = df.columns[0]
            df = df.dropna(subset=[id_col])
            df = df.sort_values(by=id_col, ascending=False)
            return df, target
        except:
            return pd.DataFrame(), None
    return pd.DataFrame(), None

df, filename = find_and_load_data()

# --- 2. 演算逻辑 ---
if not df.empty:
    latest_issue = df.iloc[0, 0]
    st.success(f"✅ 成功读取文件：{filename} | 当前期号：{latest_issue}")
    
    num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1)
    # 精准定位红球列：第3到第7列
    recent_data = df.head(num_p)
    all_reds = []
    for i in range(len(recent_data)):
        # 提取这 5 列的数据
        row_balls = recent_data.iloc[i, 2:7].values
        for b in row_balls:
            try:
                val = int(float(b))
                if 1 <= val <= 35: all_reds.append(val)
            except: continue

    counts = Counter(all_reds)
    mapping = {c: [] for c in range(max(counts.values() or [0]) + 1)}
    for i in range(1, 36): mapping[counts.get(i, 0)].append(i)

    # 视觉展示
    for f in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
        color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
        st.markdown(f"""
        <div style="display:flex;align-items:center;margin-bottom:10px;">
            <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:100px;text-align:center;">{f} 次</div>
            <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
        </div>""", unsafe_allow_html=True)
else:
    st.error("🚨 文件夹里还没看到 CSV 文件！")
    st.info("💡 请在 GitHub 的 'stat_tank' 文件夹里点 Add File，把那个大乐透表格拖进来。")
