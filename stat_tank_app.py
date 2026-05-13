import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="大数据频率演算终端", layout="wide")
st.title("📊 大数据频率实时过滤器 (精准修复版)")

# --- 1. 查找并读取数据 ---
def get_data():
    all_f = [f for f in os.listdir('.') if f.endswith('.csv')]
    if all_f:
        # 找到包含 data 或 dlt 的文件
        target = all_f[0]
        try:
            # 您的表格：第1行空，第2行表头
            df = pd.read_csv(target, skiprows=1)
            # 删掉彻底为空的行
            df = df.dropna(subset=[df.columns[0]])
            return df, target
        except: return None, None
    return None, None

df_raw, fname = get_data()

# --- 2. 核心演算逻辑 ---
if df_raw is not None:
    # 自动识别期号
    latest_id = df_raw.iloc[0, 0]
    st.success(f"✅ 已连接：{fname} | 最新期号：{latest_issue if 'latest_issue' in locals() else latest_id}")

    # 侧边栏：这里点期数会触发重新演算
    num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1, max_value=len(df_raw))
    
    # 截取选定的行数
    subset = df_raw.head(int(num_p))
    
    # 【核心修复】：精准抓取红球（第3到第7列）
    all_balls = []
    # 您的表格红球在索引 2, 3, 4, 5, 6 的位置
    for row_idx in range(len(subset)):
        for col_idx in range(2, 7):
            val = subset.iloc[row_idx, col_idx]
            try:
                # 处理 13.0 这种带小数点的格式，先转浮点再转整
                clean_num = int(float(val))
                if 1 <= clean_num <= 35:
                    all_balls.append(clean_num)
            except:
                continue

    # 计算频率
    counts = Counter(all_balls)
    
    # 建立频率分组（0次到最高次）
    max_f = max(counts.values()) if counts else 0
    mapping = {c: [] for c in range(max_f + 1)}
    for i in range(1, 36):
        mapping[counts.get(i, 0)].append(i)

    # --- 3. 视觉展示 ---
    st.subheader(f"📅 最近 {num_p} 期频率分布")
    # 倒序显示，高频在前
    for f in sorted(mapping.keys(), reverse=True):
        nums = sorted(mapping[f])
        nums_str = "  ".join([f"{x:02d}" for x in nums])
        # 颜色逻辑：高频红，0次灰，其他黑
        if f >= 5: color = "#FF4B4B"
        elif f == 0: color = "#9FA8DA"
        else: color = "#31333F"
        
        st.markdown(f"""
        <div style="display:flex;align-items:center;margin-bottom:10px;">
            <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:100px;text-align:center;">{f} 次</div>
            <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
        </div>""", unsafe_allow_html=True)
else:
    st.error("🚨 还是没看到数据文件，请确保 CSV 文件和代码在同一个文件夹里。")
