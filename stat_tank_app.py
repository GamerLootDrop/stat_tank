import streamlit as st
import pandas as pd
from collections import Counter
import math
import os
import random

# ==========================================
# 1. 全局页面配置
# ==========================================
st.set_page_config(page_title="坦克指挥控制台", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .ball-container { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
    .ball {
        width: 38px; height: 38px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: bold; font-size: 15px; color: white;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    .ball-red { background: radial-gradient(circle at 10px 10px, #FF4B2B, #B31217); box-shadow: 0 0 8px rgba(255, 75, 43, 0.6); }
    .ball-blue { background: radial-gradient(circle at 10px 10px, #6FB1FC, #0052D4); box-shadow: 0 0 8px rgba(0, 82, 212, 0.6); }
    .ball-yellow { background: radial-gradient(circle at 10px 10px, #FFD700, #F39C12); color: #333; text-shadow: none; box-shadow: 0 0 8px rgba(243, 156, 18, 0.6); }
    
    .freq-tag {
        background-color: #2b2b2b; color: #00E676; padding: 5px 10px;
        border-radius: 5px; font-weight: bold; margin-right: 15px;
        border-left: 4px solid #00E676;
        min-width: 80px; text-align: center;
    }
    .stat-row { display: flex; align-items: center; margin-bottom: 10px; background: #1E1E1E; padding: 10px; border-radius: 8px;}
    .filter-box { background: #1E1E1E; padding: 25px; border-radius: 12px; border: 1px solid #444; margin-top: 10px;}
    
    /* 重点修复：号码池 UI 升级，干掉死黑背景 */
    .pool-display { 
        font-size: 0.85rem; 
        color: #90CAF9; /* 浅蓝色文字，更具科技感 */
        background: rgba(255, 255, 255, 0.05) !important; /* 强制覆盖自带黑底，改为极淡的透明白 */
        padding: 8px 12px; 
        border-radius: 6px; 
        margin-bottom: 15px; 
        border: 1px solid rgba(255, 255, 255, 0.1); 
        line-height: 1.6;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);
    }
    
    .result-card { background: #0E1117; padding: 15px; border-radius: 10px; border-left: 5px solid #00E676; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 智能脱机读取引擎
# ==========================================
@st.cache_data
def load_local_data(lottery_code, uploaded_file=None):
    is_excel = False
    if uploaded_file is not None:
        file_source = uploaded_file
        if uploaded_file.name.endswith(('.xls', '.xlsx')): is_excel = True
    else:
        if os.path.exists(f"{lottery_code}.xls"):
            file_source = f"{lottery_code}.xls"
            is_excel = True
        elif os.path.exists(f"{lottery_code}.csv"):
            file_source = f"{lottery_code}.csv"
        else:
            return pd.DataFrame()
    
    try:
        if hasattr(file_source, 'seek'): file_source.seek(0)
        def read_data(src, **kwargs):
            if is_excel:
                try: return pd.read_excel(src, **kwargs)
                except: 
                    if hasattr(src, 'seek'): src.seek(0)
                    return pd.read_csv(src, sep='\t', **kwargs)
            else:
                return pd.read_csv(src, encoding_errors='ignore', **kwargs)

        df_test = read_data(file_source, nrows=1)
        if '前1' in df_test.columns:
            if hasattr(file_source, 'seek'): file_source.seek(0)
            df = read_data(file_source)
            df = df.sort_values(by='期号', ascending=False).reset_index(drop=True)
            return df
        else:
            if hasattr(file_source, 'seek'): file_source.seek(0)
            if lottery_code == 'dlt':
                cols_to_use, col_names = [0, 2, 3, 4, 5, 6, 7, 8], ['期号', '前1', '前2', '前3', '前4', '前5', '后1', '后2']
            else:
                cols_to_use, col_names = [0, 2, 3, 4, 5, 6, 7, 8], ['期号', '前1', '前2', '前3', '前4', '前5', '前6', '后1']
            df_raw = read_data(file_source, skiprows=2, header=None, usecols=cols_to_use)
            df_raw.columns = col_names
            df_raw = df_raw.dropna(subset=['前1', '后1'])
            df_raw['期号'] = df_raw['期号'].astype(str).str.replace(r'\.0$', '', regex=True)
            for col in col_names:
                if col != '期号': df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0).astype(int)
            return df_raw.sort_values(by='期号', ascending=False).reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame()

# ==========================================
# 3. 数学计算辅助
# ==========================================
def calculate_frequencies(df, is_dlt=True):
    if is_dlt:
        front_nums, back_nums = df[['前1', '前2', '前3', '前4', '前5']].values.flatten(), df[['后1', '后2']].values.flatten()
        front_max, back_max = 35, 12
    else:
        front_nums, back_nums = df[['前1', '前2', '前3', '前4', '前5', '前6']].values.flatten(), df[['后1']].values.flatten()
        front_max, back_max = 33, 16
    front_counts, back_counts = Counter(front_nums), Counter(back_nums)
    for i in range(1, front_max + 1): front_counts.setdefault(i, 0)
    for i in range(1, back_max + 1): back_counts.setdefault(i, 0)
    return front_counts, back_counts

def nCr(n, r):
    return math.comb(n, r) if 0 <= r <= n else 0

# ==========================================
# 4. 侧边栏
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("指挥中心")
    lottery_type = st.selectbox("🎯 频道切换", ["双色球 (SSQ)", "大乐透 (DLT)"])
    period_limit = st.slider("📅 走势期数", 10, 200, 70)
    st.markdown("---")
    uploaded_file = st.file_uploader("📂 上传新开奖文件", type=['csv', 'xls', 'xlsx'])

is_dlt = "DLT" in lottery_type
lottery_code = 'dlt' if is_dlt else 'ssq'
req_f, req_b = (5, 2) if is_dlt else (6, 1)
max_f, max_b = (35, 12) if is_dlt else (33, 16)

# ==========================================
# 5. 主画面
# ==========================================
st.header(f"🚀 {lottery_type} 核心雷达走势")

df_base = load_local_data(lottery_code, uploaded_file)

if not df_base.empty:
    df = df_base.head(period_limit)
    latest_issue = str(df_base.iloc[0]['期号'])
    st.caption(f"当前分析：第 {latest_issue} 期之前的 {period_limit} 期走势")

    # 1. 频次矩阵
    front_counts, back_counts = calculate_frequencies(df, is_dlt)
    front_color_class, back_color_class = ("ball-blue", "ball-yellow") if is_dlt else ("ball-red", "ball-blue")

    col1, col2 = st.columns(2)
    def render_balls(counts_dict, ball_class):
        freq_group = {}
        for num, freq in counts_dict.items(): freq_group.setdefault(freq, []).append(num)
        html_str = ""
        for freq in sorted(freq_group.keys(), reverse=True):
            nums_sorted = sorted(freq_group[freq])
            balls_html = "".join([f"<div class='ball {ball_class}'>{str(n).zfill(2)}</div>" for n in nums_sorted])
            html_str += f"<div class='stat-row'><div class='freq-tag'>{freq} 次</div><div class='ball-container'>{balls_html}</div></div>"
        return html_str

    with col1:
        st.markdown(f"### {'🔵' if is_dlt else '🔴'} 前区热度")
        st.markdown(render_balls(front_counts, front_color_class), unsafe_allow_html=True)
    with col2:
        st.markdown(f"### {'🟡' if is_dlt else '🔵'} 后区热度")
        st.markdown(render_balls(back_counts, back_color_class), unsafe_allow_html=True)

    st.markdown("---")
    
    # 2. 012路形态缩水计算器 (核心)
    st.subheader("📐 012路 智能缩水计算器")
    st.info(f"根据《计算公式000.docx》，通过分配 0/1/2 路出号比例，实时锁定剩余组数和金额。")

    # 定义号池
    f0 = [x for x in range(1, max_f + 1) if x % 3 == 0]
    f1 = [x for x in range(1, max_f + 1) if x % 3 == 1]
    f2 = [x for x in range(1, max_f + 1) if x % 3 == 2]
    b0 = [x for x in range(1, max_b + 1) if x % 3 == 0]
    b1 = [x for x in range(1, max_b + 1) if x % 3 == 1]
    b2 = [x for x in range(1, max_b + 1) if x % 3 == 2]

    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    
    # 侧重于前区的UI
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        st.markdown("**0路 (余0)**")
        st.markdown(f"<div class='pool-display'>{', '.join([str(x).zfill(2) for x in f0])}</div>", unsafe_allow_html=True)
        rf0 = st.number_input("前区0路出几个", 0, req_f, 2, key="rf0")
    with fc2:
        st.markdown("**1路 (余1)**")
        st.markdown(f"<div class='pool-display'>{', '.join([str(x).zfill(2) for x in f1])}</div>", unsafe_allow_html=True)
        rf1 = st.number_input("前区1路出几个", 0, req_f, 2, key="rf1")
    with fc3:
        st.markdown("**2路 (余2)**")
        st.markdown(f"<div class='pool-display'>{', '.join([str(x).zfill(2) for x in f2])}</div>", unsafe_allow_html=True)
        rf2 = st.number_input("前区2路出几个", 0, req_f, 1 if is_dlt else 2, key="rf2")

    st.markdown("---")
    # 侧重于后区的UI
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        st.markdown(f"**后区0路 (共{len(b0)}个)**")
        rb0 = st.number_input("后区0路出几个", 0, req_b, 0 if is_dlt else 0, key="rb0")
    with bc2:
        st.markdown(f"**后区1路 (共{len(b1)}个)**")
        rb1 = st.number_input("后区1路出几个", 0, req_b, 1 if is_dlt else 1, key="rb1")
    with bc3:
        st.markdown(f"**后区2路 (共{len(b2)}个)**")
        rb2 = st.number_input("后区2路出几个", 0, req_b, 1 if is_dlt else 0, key="rb2")

    st.markdown('</div>', unsafe_allow_html=True)

    # 逻辑验证与实时计算
    sum_f, sum_b = (rf0 + rf1 + rf2), (rb0 + rb1 + rb2)
    
    if sum_f != req_f:
        st.warning(f"💡 注意：当前前区 012路分配总和为 {sum_f}，必须等于 {req_f} 才能计算。")
    elif sum_b != req_b:
        st.warning(f"💡 注意：当前后区 012路分配总和为 {sum_b}，必须等于 {req_b} 才能计算。")
    else:
        # 核心排列组合公式应用
        ans_f = nCr(len(f0), rf0) * nCr(len(f1), rf1) * nCr(len(f2), rf2)
        ans_b = nCr(len(b0), rb0) * nCr(len(b1), rb1) * nCr(len(b2), rb2)
        total_bets = ans_f * ans_b
        
        # 结果展示区
        st.markdown(f"""
        <div class="result-card">
            <h3 style='margin:0; color:#00E676;'>🎯 筛选计算结果</h3>
            <p style='font-size:1.2rem; margin-top:10px;'>
                形态：前区({rf0}:{rf1}:{rf2}) + 后区({rb0}:{rb1}:{rb2})<br>
                剩余注数：<span style='color:#FFD700; font-weight:bold;'>{total_bets}</span> 组<br>
                单倍投入：<span style='color:#FF4B2B; font-weight:bold;'>{total_bets * 2}</span> 元
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 实战出号
        if total_bets > 0:
            if st.button("🎲 随机提取 5 组符合此形态的号码"):
                st.write("---")
                for i in range(min(5, total_bets)):
                    p_f = sorted(random.sample(f0, rf0) + random.sample(f1, rf1) + random.sample(f2, rf2))
                    p_b = sorted(random.sample(b0, rb0) + random.sample(b1, rb1) + random.sample(b2, rb2))
                    f_txt = " ".join([str(x).zfill(2) for x in p_f])
                    b_txt = " ".join([str(x).zfill(2) for x in p_b])
                    st.code(f"精选第{i+1}组: [ {f_txt} ] + [ {b_txt} ]")

else:
    st.warning("⚠️ **数据仓库空虚！** 请在侧边栏上传 xls/csv 激活指挥控制台。")
