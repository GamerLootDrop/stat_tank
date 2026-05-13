import streamlit as st
import pandas as pd
from collections import Counter
import math
import os
import random

# ==========================================
# 1. 坦克指挥部 UI 深度清洁
# ==========================================
st.set_page_config(page_title="坦克指挥控制台", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    /* 彻底抹除 Streamlit 原生组件的黑边框和阴影 */
    div[data-testid="stNotification"], div[role="alert"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: none !important;
        color: #90CAF9 !important;
    }
    /* 球体样式 */
    .ball-container { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
    .ball {
        width: 35px; height: 35px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: bold; font-size: 14px; color: white;
    }
    .ball-red { background: radial-gradient(circle at 10px 10px, #FF4B2B, #B31217); }
    .ball-blue { background: radial-gradient(circle at 10px 10px, #6FB1FC, #0052D4); }
    .ball-yellow { background: radial-gradient(circle at 10px 10px, #FFD700, #F39C12); color: #333; }
    
    /* 结果卡片 */
    .result-card { 
        background: #1E1E1E; padding: 20px; border-radius: 12px; 
        border-left: 5px solid #00E676; margin-top: 15px; 
    }
    /* 号池文字流 */
    .pool-text { color: #888; font-family: monospace; font-size: 13px; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心数学模型 (保留计算逻辑，不露字)
# ==========================================
def nCr(n, r):
    return math.comb(n, r) if 0 <= r <= n else 0

@st.cache_data
def load_data(lottery_code, uploaded_file):
    # 此处包含之前的万能数据读取逻辑
    try:
        if uploaded_file:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(f"{lottery_code}.csv")
        return df
    except: return pd.DataFrame()

# ==========================================
# 3. 自动化配比算法 (自适应)
# ==========================================
def auto_calculate_ratio(df, is_dlt):
    """分析历史趋势，推荐当前最可能的 012 配比"""
    if df.empty: return (2, 2, 1) if is_dlt else (2, 2, 2)
    # 取最近 20 期分析
    recent = df.head(20)
    cols = ['前1','前2','前3','前4','前5'] if is_dlt else ['前1','前2','前3','前4','前5','前6']
    flat_nums = recent[cols].values.flatten()
    r0 = sum(1 for x in flat_nums if x % 3 == 0) / len(recent)
    r1 = sum(1 for x in flat_nums if x % 3 == 1) / len(recent)
    r2 = sum(1 for x in flat_nums if x % 3 == 2) / len(recent)
    
    total = 5 if is_dlt else 6
    # 按比例分配个数
    n0 = round(total * (r0 / (r0+r1+r2)))
    n1 = round(total * (r1 / (r0+r1+r2)))
    n2 = total - n0 - n1
    return n0, n1, n2

# ==========================================
# 4. 主界面
# ==========================================
with st.sidebar:
    st.title("坦克指挥部")
    lottery_type = st.selectbox("频道", ["双色球 (SSQ)", "大乐透 (DLT)"])
    period_limit = st.slider("扫描深度", 10, 200, 70)
    up_file = st.file_uploader("上传补给")

is_dlt = "DLT" in lottery_type
lottery_code = 'dlt' if is_dlt else 'ssq'
req_f = 5 if is_dlt else 6
max_f = 35 if is_dlt else 33

df = load_data(lottery_code, up_file)

if not df.empty:
    st.subheader(f"🚀 {lottery_type} 012路自适应筛选")
    
    # 自动预设
    auto_n0, auto_n1, auto_n2 = auto_calculate_ratio(df, is_dlt)
    
    # 快捷按钮
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    if col_btn1.button("✨ 智能自适应"):
        st.session_state.f0, st.session_state.f1, st.session_state.f2 = auto_n0, auto_n1, auto_n2
    if col_btn2.button("⚖️ 均势分布"):
        st.session_state.f0, st.session_state.f1, st.session_state.f2 = (2, 2, 1) if is_dlt else (2, 2, 2)
    if col_btn3.button("🔥 激进热态"):
        st.session_state.f0, st.session_state.f1, st.session_state.f2 = (3, 1, 1) if is_dlt else (3, 2, 1)

    # 号池显示 (无黑块)
    f0 = [x for x in range(1, max_f+1) if x % 3 == 0]
    f1 = [x for x in range(1, max_f+1) if x % 3 == 1]
    f2 = [x for x in range(1, max_f+1) if x % 3 == 2]

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("0路 (余0)")
        st.markdown(f"<div class='pool-text'>{', '.join([str(x).zfill(2) for x in f0])}</div>", unsafe_allow_html=True)
        n0 = st.number_input("个数", 0, req_f, st.session_state.get('f0', auto_n0), key="k0")
    with c2:
        st.caption("1路 (余1)")
        st.markdown(f"<div class='pool-text'>{', '.join([str(x).zfill(2) for x in f1])}</div>", unsafe_allow_html=True)
        n1 = st.number_input("个数", 0, req_f, st.session_state.get('f1', auto_n1), key="k1")
    with c3:
        st.caption("2路 (余2)")
        st.markdown(f"<div class='pool-text'>{', '.join([str(x).zfill(2) for x in f2])}</div>", unsafe_allow_html=True)
        n2 = st.number_input("个数", 0, req_f, st.session_state.get('f2', auto_n2), key="k2")

    # 结果输出 (纯净算法版)
    if (n0 + n1 + n2) == req_f:
        ans_f = nCr(len(f0), n0) * nCr(len(f1), n1) * nCr(len(f2), n2)
        # 默认后区逻辑 (大乐透按12选2计算，双色球16选1)
        ans_b = nCr(12, 2) if is_dlt else 16
        total = ans_f * ans_b

        st.markdown(f"""
        <div class="result-card">
            <div style='font-size:14px; color:#888;'>当前配置：前区 {n0}:{n1}:{n2}</div>
            <div style='font-size:26px; color:#FFD700; font-weight:bold; margin:5px 0;'>剩余 {total} 组</div>
            <div style='font-size:14px; color:#00E676;'>预估消耗：{total * 2} 元</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🎯 执行精选提取"):
            for i in range(5):
                res = sorted(random.sample(f0, n0) + random.sample(f1, n1) + random.sample(f2, n2))
                st.success(f"精选 {i+1}: {' '.join([str(x).zfill(2) for x in res])}")
    else:
        st.error(f"⚠️ 总数需等于 {req_f} (当前 {n0+n1+n2})")
else:
    st.info("请先在左侧上传开奖数据文件...")
