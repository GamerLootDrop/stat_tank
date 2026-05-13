import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率实时过滤器 (表格模式适配版)")

# --- 1. 专门适配您的表格模式 ---
def load_special_data():
    # 文件名必须和您上传的一模一样
    file_path = "dlt.xls - data.csv" 
    if os.path.exists(file_path):
        try:
            # 关键动作：skiprows=1 跳过第一行空行
            df = pd.read_csv(file_path, skiprows=1)
            
            # 过滤掉没有期号的行
            df = df.dropna(subset=[df.columns[0]]) 
            
            # 强制按期号倒叙排，确保最新的在最上面
            df = df.sort_values(by=df.columns[0], ascending=False)
            return df
        except Exception as e:
            st.error(f"表格格式读取失败：{e}")
    return pd.DataFrame()

df = load_special_data()

# --- 2. 演算逻辑 ---
if not df.empty:
    latest_issue = df.iloc[0, 0] # 取第一行第一列的期号
    st.success(f"✅ 适配成功！当前正在演算：第 {latest_issue} 期")
    
    num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1)
    recent_data = df.head(num_p)
    
    # 重点：根据您的表格模式，红球在第 3, 4, 5, 6, 7 列
    all_reds = []
    for i in range(len(recent_data)):
        # 提取这 5 列的数据
        row_balls = recent_data.iloc[i, 2:7].values
        # 转化成整数
        for b in row_balls:
            try:
                val = int(float(b))
                if 1 <= val <= 35:
                    all_reds.append(val)
            except:
                continue

    counts = Counter(all_reds)
    
    # 频率分组展示
    mapping = {c: [] for c in range(max(counts.values() or [0]) + 1)}
    for i in range(1, 36):
        mapping[counts.get(i, 0)].append(i)

    st.subheader(f"📅 最近 {num_p} 期频率分布图")
    for f in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
        color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
        st.markdown(f"""
        <div style="display:flex;align-items:center;margin-bottom:10px;">
            <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:80px;text-align:center;">{f} 次</div>
            <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
        </div>""", unsafe_allow_html=True)
else:
    st.warning("🚨 没读到数据！请确认 'dlt.xls - data.csv' 就在 'stat_tank' 文件夹里。")
