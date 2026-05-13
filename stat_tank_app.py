import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率实时过滤器 (双彩种兼容版)")

# --- 1. 获取文件夹内所有 CSV 数据 ---
def get_all_csvs():
    # 只找以 .csv 结尾的文件
    return [f for f in os.listdir('.') if f.endswith('.csv')]

csv_files = get_all_csvs()

if csv_files:
    # 让您在侧边栏明确选择现在要算哪一个
    st.sidebar.header("📁 数据选择")
    target_file = st.sidebar.selectbox("请选择要分析的表格：", csv_files)
    
    try:
        # 读取表格（跳过第一行空行）
        df = pd.read_csv(target_file, skiprows=1)
        # 清理掉没期号的行
        df = df.dropna(subset=[df.columns[0]])
        # 强制按第一列（期号）倒序排列
        df = df.sort_values(by=df.columns[0], ascending=False)
        
        # --- 2. 识别彩种逻辑 ---
        is_ssq = "ssq" in target_file.lower() or "双色球" in target_file
        game_name = "🔴 双色球 (33选6)" if is_ssq else "🟢 大乐透 (35选5)"
        red_needed = 6 if is_ssq else 5
        max_val = 33 if is_ssq else 35
        
        latest_id = df.iloc[0, 0]
        st.success(f"✅ 已选中：{game_name} | 文件：{target_file} | 最新期：{latest_id}")

        # --- 3. 统计演算 ---
        num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1, max_value=len(df))
        subset = df.head(int(num_p))
        
        all_balls = []
        for i in range(len(subset)):
            # 关键：从第3列（索引2）开始抓，如果是双色球抓6个，大乐透抓5个
            row_reds = subset.iloc[i, 2 : 2 + red_needed].values
            for b in row_reds:
                try:
                    val = int(float(b))
                    if 1 <= val <= max_val:
                        all_balls.append(val)
                except: continue

        counts = Counter(all_balls)
        max_f = max(counts.values()) if counts else 0
        mapping = {c: [] for c in range(max_f + 1)}
        for i in range(1, max_val + 1):
            mapping[counts.get(i, 0)].append(i)

        # --- 4. 出图 ---
        st.subheader(f"📅 {game_name} 最近 {num_p} 期频率分布")
        for f in sorted(mapping.keys(), reverse=True):
            nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
            color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
            st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:10px;"><div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:120px;text-align:center;">{f} 次出现</div><div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div></div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"解析出错：{e}")
else:
    st.error("🚨 警告：文件夹里一个 .csv 文件都没看到！")
    st.info("💡 请务必把大乐透和双色球的 CSV 表格拖进 GitHub 的 'stat_tank' 文件夹。")
