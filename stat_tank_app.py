import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="数据频率演算终端", layout="wide")
st.title("📊 大数据频率实时过滤器 (全能兼容版)")

# --- 1. 查找并读取数据 ---
def get_data():
    all_f = [f for f in os.listdir('.') if f.endswith('.csv')]
    if all_f:
        # 默认取第一个 CSV
        target = all_f[0]
        try:
            # 您的表格：第1行空，第2行表头
            df = pd.read_csv(target, skiprows=1)
            # 过滤掉彻底为空的行
            df = df.dropna(how='all').dropna(subset=[df.columns[0]])
            return df, target
        except: return None, None
    return None, None

df_raw, fname = get_data()

# --- 2. 核心演算逻辑 ---
if df_raw is not None:
    # 自动识别期号
    latest_id = df_raw.iloc[0, 0]
    st.success(f"✅ 已连接：{fname} | 最新期号：{latest_id}")

    # 侧边栏设置
    num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1, max_value=len(df_raw))
    
    # 自动判断球种（根据文件名或列数）
    is_ssq = "ssq" in fname.lower() or "双色球" in fname
    game_type = "双色球 (33选6)" if is_ssq else "大乐透 (35选5)"
    red_needed = 6 if is_ssq else 5
    max_ball_val = 33 if is_ssq else 35
    
    st.sidebar.info(f"当前识别模式：{game_type}")

    # 截取行数
    subset = df_raw.head(int(num_p))
    
    # 【核心修复】：安全抓取红球逻辑
    all_balls = []
    for row_idx in range(len(subset)):
        row_data = subset.iloc[row_idx]
        # 从第3列开始，往后抓 5 或 6 个球
        # 使用 min 确保不会超出表格实际的总列数
        actual_cols = len(row_data)
        for col_idx in range(2, min(2 + red_needed, actual_cols)):
            val = row_data.iloc[col_idx]
            try:
                # 兼容 13.0 这种带小数点的格式
                clean_num = int(float(val))
                if 1 <= clean_num <= max_ball_val:
                    all_balls.append(clean_num)
            except:
                continue

    # 计算频率
    counts = Counter(all_balls)
    max_f = max(counts.values()) if counts else 0
    mapping = {c: [] for c in range(max_f + 1)}
    for i in range(1, max_ball_val + 1):
        mapping[counts.get(i, 0)].append(i)

    # --- 3. 视觉展示 ---
    st.subheader(f"📅 最近 {num_p} 期频率分布 ({game_type})")
    for f in sorted(mapping.keys(), reverse=True):
        nums = sorted(mapping[f])
        nums_str = "  ".join([f"{x:02d}" for x in nums])
        
        # 颜色逻辑
        if f >= 5: color = "#FF4B4B"
        elif f == 0: color = "#9FA8DA"
        else: color = "#31333F"
        
        st.markdown(f"""
        <div style="display:flex;align-items:center;margin-bottom:10px;">
            <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:100px;text-align:center;">{f} 次出现</div>
            <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
        </div>""", unsafe_allow_html=True)
else:
    st.error("🚨 仓库文件夹里没看到 CSV 数据文件！")
