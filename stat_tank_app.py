import streamlit as st
import pandas as pd
from collections import Counter
import math
import os
import random

# ==========================================
# 1. 全局页面配置 & 强制视觉净化
# ==========================================
st.set_page_config(page_title="坦克指挥控制台", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    /* 彻底抹除原生组件的黑背景和边框 */
    .stApp { background-color: #0E1117; }
    div[data-testid="stMarkdownContainer"] pre, code { background: transparent !important; border: none !important; color: #00E676 !important; }
    div[data-testid="stNotification"], .stAlert { background-color: rgba(0,230,118,0.05) !important; border: 1px solid #333 !important; color: #90CAF9 !important; }
    
    /* 极致紧凑布局：减小手机端间距 */
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }

    /* 迷你球样式：解决手机端显示过大问题 */
    .mini-ball {
        display: inline-flex; width: 24px; height: 24px; border-radius: 50%;
        align-items: center; justify-content: center;
        font-size: 11px; margin: 1px; color: #E0E0E0;
        border: 1px solid #444; background: #262626;
    }
    .pool-box { line-height: 1.2; padding: 5px 0; margin-bottom: 5px; }
    
    /* 隐藏输入框的多余标签以节省高度 */
    div[data-testid="stNumberInput"] label { font-size: 0.8rem; color: #888; }
    
    /* 结果显示区 */
    .result-card { 
        background: #161b22; padding: 12px; border-radius: 8px; 
        border-left: 4px solid #00E676; margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 智能脱机读取引擎 (保留原逻辑)
# ==========================================
@st.cache_data
def load_local_data(lottery_code, uploaded_file=None):
    is_excel = False
    if uploaded_file is not None:
        file_source = uploaded_file
        if uploaded_file.name.endswith(('.xls', '.xlsx')): is_excel = True
    else:
        if os.path.exists(f"{lottery_code}.xls"):
            file_source = f"{lottery_code}.xls"; is_excel = True
        elif os.path.exists(f"{lottery_code}.csv"):
            file_source = f"{lottery_code}.csv"
        else: return pd.DataFrame()
    
    try:
        if hasattr(file_source, 'seek'): file_source.seek(0)
        def read_data(src, **kwargs):
            if is_excel:
                try: return pd.read_excel(src, **kwargs)
                except: 
                    if hasattr(src, 'seek'): src.seek(0)
                    return pd.read_csv(src, sep='\t', **kwargs)
            else: return pd.read_csv(src, encoding_errors='ignore', **kwargs)

        df_test = read_data(file_source, nrows=1)
        if '前1' in df_test.columns:
            if hasattr(file_source, 'seek'): file_source.seek(0)
            df = read_data(file_source)
            return df.sort_values(by='期号', ascending=False).reset_index(drop=True)
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
    except: return pd.DataFrame()

def calculate_bets(n, r): return math.comb(n, r) if r <= n and r >= 0 else 0

# ==========================================
# 3. 侧边栏配置
# ==========================================
with st.sidebar:
    st.title("控制台")
    lottery_type = st.selectbox("频道", ["双色球 (SSQ)", "大乐透 (DLT)"])
    period_limit = st.slider("深度", 10, 200, 70)
    uploaded_file = st.file_uploader("补给数据", type=['csv', 'xls', 'xlsx'])

is_dlt = "DLT" in lottery_type
lot_code = 'dlt' if is_dlt else 'ssq'
req_f, max_f = (5, 35) if is_dlt else (6, 33)
req_b, max_b = (2, 12) if is_dlt else (1, 16)

# ==========================================
# 4. 主界面：012路自适应操作区
# ==========================================
df_base = load_local_data(lot_code, uploaded_file)

if not df_base.empty:
    df = df_base.head(period_limit)
    
    # --- 智能自适应逻辑 (计算最近出号比例) ---
    f_cols = ['前1','前2','前3','前4','前5'] if is_dlt else ['前1','前2','前3','前4','前5','前6']
    all_f = df[f_cols].values.flatten()
    c0 = sum(1 for x in all_f if x % 3 == 0)
    c1 = sum(1 for x in all_f if x % 3 == 1)
    c2 = sum(1 for x in all_f if x % 3 == 2)
    total_f = c0 + c1 + c2
    # 推荐配比
    rec_f0 = round(req_f * (c0/total_f))
    rec_f1 = round(req_f * (c1/total_f))
    rec_f2 = req_f - rec_f0 - rec_f1

    st.subheader(f"📐 012路 智能操作 (第{df_base.iloc[0]['期号']}期)")
    
    # --- 傻瓜式一键设置 ---
    c_btn1, c_btn2, c_btn3 = st.columns([1, 1.5, 1])
    with c_btn1:
        if st.button("✨ 智能自适应", use_container_width=True):
            st.session_state.f0, st.session_state.f1, st.session_state.f2 = rec_f0, rec_f1, rec_f2
    with c_btn2:
        preset = st.selectbox("快速配比选项", ["自定义", "2-2-1", "2-1-2", "1-2-2", "3-1-1", "1-3-1", "1-1-3"] if is_dlt else ["自定义", "2-2-2", "3-2-1", "1-2-3", "4-1-1", "2-3-1"])
        if preset != "自定义":
            p_vals = [int(x) for x in preset.split('-')]
            st.session_state.f0, st.session_state.f1, st.session_state.f2 = p_vals[0], p_vals[1], p_vals[2]
    
    # --- 紧凑号池展示 (横向三列) ---
    f_0 = [x for x in range(1, max_f + 1) if x % 3 == 0]
    f_1 = [x for x in range(1, max_f + 1) if x % 3 == 1]
    f_2 = [x for x in range(1, max_f + 1) if x % 3 == 2]

    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.markdown("**0路**")
        st.markdown(f"<div class='pool-box'>{''.join([f'<span class=mini-ball>{str(x).zfill(2)}</span>' for x in f_0])}</div>", unsafe_allow_html=True)
        in_f0 = st.number_input("0路个", 0, req_f, st.session_state.get('f0', rec_f0), key="kf0", label_visibility="collapsed")
    with col_b:
        st.markdown("**1路**")
        st.markdown(f"<div class='pool-box'>{''.join([f'<span class=mini-ball>{str(x).zfill(2)}</span>' for x in f_1])}</div>", unsafe_allow_html=True)
        in_f1 = st.number_input("1路个", 0, req_f, st.session_state.get('f1', rec_f1), key="kf1", label_visibility="collapsed")
    with col_c:
        st.markdown("**2路**")
        st.markdown(f"<div class='pool-box'>{''.join([f'<span class=mini-ball>{str(x).zfill(2)}</span>' for x in f_2])}</div>", unsafe_allow_html=True)
        in_f2 = st.number_input("2路个", 0, req_f, st.session_state.get('f2', rec_f2), key="kf2", label_visibility="collapsed")

    # --- 结果计算 (保留原始组合数逻辑) ---
    if (in_f0 + in_f1 + in_f2) == req_f:
        # 组合计算逻辑 (后区默认全包以简化操作)
        total_bets = calculate_bets(len(f_0), in_f0) * calculate_bets(len(f_1), in_f1) * calculate_bets(len(f_2), in_f2)
        total_bets *= calculate_bets(max_b, req_b) # 包含后区全包
        
        st.markdown(f"""
        <div class="result-card">
            <div style='color:#888; font-size:12px;'>当前配比 {in_f0}:{in_f1}:{in_f2} (后区全包)</div>
            <div style='font-size:22px; color:#FFD700; font-weight:bold; margin:4px 0;'>剩余 {total_bets} 注</div>
            <div style='color:#00E676; font-size:14px;'>投入预估: {total_bets * 2} 元</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🎲 提取精选号码", use_container_width=True):
            for i in range(5):
                pick = sorted(random.sample(f_0, in_f0) + random.sample(f_1, in_f1) + random.sample(f_2, in_f2))
                st.code(f"{i+1}: {' '.join([str(x).zfill(2) for x in pick])}")
    else:
        st.error(f"总和需等于 {req_f}")

else:
    st.info("💡 请在左侧上传数据...")
