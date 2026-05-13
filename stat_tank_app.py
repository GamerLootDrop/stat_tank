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
    .filter-box { background: #1E1E1E; padding: 20px; border-radius: 10px; border: 1px solid #333;}
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
# 3. 核心运算逻辑
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

def calculate_bets(n, r):
    return math.comb(n, r) if r <= n and r >= 0 else 0

def generate_text_report(title, front_counts, back_counts, is_dlt):
    report = f"========== {title} ==========\n\n[前区统计]\n"
    def format_dict(counts_dict):
        freq_group = {}
        for num, freq in counts_dict.items(): freq_group.setdefault(freq, []).append(num)
        res = ""
        for freq in sorted(freq_group.keys(), reverse=True):
            nums = ",".join([str(n).zfill(2) for n in sorted(freq_group[freq])])
            res += f"{freq}次: {nums}\n"
        return res
    report += format_dict(front_counts) + "\n[后区统计]\n" + format_dict(back_counts) + "\n========================================="
    return report

# ==========================================
# 4. 侧边栏
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    lottery_type = st.selectbox("🎯 切换演算频道", ["双色球 (SSQ)", "大乐透 (DLT)"])
    period_limit = st.slider("📅 深度扫描期数", min_value=10, max_value=200, value=70, step=10)
    st.markdown("---")
    st.markdown("### 🗄️ 数据库管理 (Admin)")
    uploaded_file = st.file_uploader(f"临时投喂 {lottery_type} 数据", type=['csv', 'xls', 'xlsx'])

is_dlt = "DLT" in lottery_type
lottery_code = 'dlt' if is_dlt else 'ssq'
req_f, req_b = (5, 2) if is_dlt else (6, 1)
max_f, max_b = (35, 12) if is_dlt else (33, 16)

# ==========================================
# 5. 主画面
# ==========================================
st.header(f"🚀 雷达监测：{lottery_type} (近 {period_limit} 期走势)")

df_base = load_local_data(lottery_code, uploaded_file)

if not df_base.empty:
    df = df_base.head(period_limit)
    latest_issue = str(df_base.iloc[0]['期号'])
    
    with st.expander(f"🟢 数据加载成功！当前最新期号: 第 {latest_issue} 期 (展开查看CSV)"):
        st.dataframe(df.head(10).astype(str), use_container_width=True)

    front_counts, back_counts = calculate_frequencies(df, is_dlt)
    front_color_class, back_color_class = ("ball-blue", "ball-yellow") if is_dlt else ("ball-red", "ball-blue")

    st.subheader("🧬 核心出现频次矩阵")
    col1, col2 = st.columns(2)
    def render_balls(counts_dict, ball_class):
        freq_group = {}
        for num, freq in counts_dict.items(): freq_group.setdefault(freq, []).append(num)
        html_str = ""
        for freq in sorted(freq_group.keys(), reverse=True):
            nums_sorted = sorted(freq_group[freq])
            balls_html = "".join([f"<div class='ball {ball_class}'>{str(n).zfill(2)}</div>" for n in nums_sorted])
            html_str += f"<div class='stat-row'><div class='freq-tag'>{freq} 次</div><div class='ball-container' style='margin-bottom:0;'>{balls_html}</div></div>"
        return html_str

    with col1:
        st.markdown(f"### {'🔵' if is_dlt else '🔴'} 前区 (1-{max_f})")
        st.markdown(render_balls(front_counts, front_color_class), unsafe_allow_html=True)
    with col2:
        st.markdown(f"### {'🟡' if is_dlt else '🔵'} 后区 (1-{max_b})")
        st.markdown(render_balls(back_counts, back_color_class), unsafe_allow_html=True)

    st.markdown("---")
    
    # ==========================================
    # 🌟 基础计算器 (保留区)
    # ==========================================
    calc_col, export_col = st.columns([1.5, 1])
    with calc_col:
        st.subheader("🧮 基础复式计算器")
        cc1, cc2 = st.columns(2)
        with cc1: sel_front = st.number_input(f"选取前区个数 (至少{req_f}个)", min_value=req_f, max_value=max_f, value=req_f)
        with cc2: sel_back = st.number_input(f"选取后区个数 (至少{req_b}个)", min_value=req_b, max_value=max_b, value=req_b)
        bets = calculate_bets(sel_front, req_f) * calculate_bets(sel_back, req_b)
        st.info(f"💰 基础全包共计 **{bets}** 注，需投入 **{bets * 2}** 元。")

    with export_col:
        st.subheader("🖨️ 导出走势报告")
        text_report = generate_text_report(f"{lottery_type} 近 {period_limit} 期走势", front_counts, back_counts, is_dlt)
        st.download_button("📥 下载统计 txt", data=text_report, file_name=f"{lottery_type}_report.txt", mime="text/plain", use_container_width=True)

    st.markdown("---")
    
    # ==========================================
    # 📐 012路形态过滤引擎 (新加装区)
    # ==========================================
    st.subheader("📐 012路形态过滤引擎 (基于概率论与组合数学)")
    st.caption("运用你提供的公式文档，通过排列组合 $C_n^k$ 和独立事件乘法原理，精准计算特定 012路 形态的注数！")
    
    # 引入文档中的数学公式
    with st.expander("📝 展开查看底层计算公式参考"):
        st.markdown("基于《计算公式000.docx》：")
        st.latex(r"C_n^k = \frac{n!}{k!(n-k)!} \quad \text{(组合数)}")
        st.latex(r"P(AB) = P(A)P(B) \quad \text{(独立事件与乘法原理)}")
        st.markdown("总注数 = $C_{N_{f0}}^{k_{f0}} \\times C_{N_{f1}}^{k_{f1}} \\times C_{N_{f2}}^{k_{f2}} \\times C_{N_{b0}}^{k_{b0}} \\times C_{N_{b1}}^{k_{b1}} \\times C_{N_{b2}}^{k_{b2}}$")

    # 构建 0/1/2 路池
    f_0 = [x for x in range(1, max_f + 1) if x % 3 == 0]
    f_1 = [x for x in range(1, max_f + 1) if x % 3 == 1]
    f_2 = [x for x in range(1, max_f + 1) if x % 3 == 2]
    
    b_0 = [x for x in range(1, max_b + 1) if x % 3 == 0]
    b_1 = [x for x in range(1, max_b + 1) if x % 3 == 1]
    b_2 = [x for x in range(1, max_b + 1) if x % 3 == 2]

    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    f_col1, f_col2 = st.columns(2)
    
    # 智能预设默认分配方案
    def_f0, def_f1, def_f2 = (2, 2, 1) if is_dlt else (2, 2, 2)
    def_b0, def_b1, def_b2 = (0, 1, 1) if is_dlt else (0, 1, 0)
    
    with f_col1:
        st.markdown(f"**{'🔵' if is_dlt else '🔴'} 前区 012路分配 (总共需选 {req_f} 个)**")
        f_req_0 = st.number_input(f"0路出号数 (余数0, 共{len(f_0)}个码)", 0, req_f, def_f0, key="f0")
        f_req_1 = st.number_input(f"1路出号数 (余数1, 共{len(f_1)}个码)", 0, req_f, def_f1, key="f1")
        f_req_2 = st.number_input(f"2路出号数 (余数2, 共{len(f_2)}个码)", 0, req_f, def_f2, key="f2")
        
    with f_col2:
        st.markdown(f"**{'🟡' if is_dlt else '🔵'} 后区 012路分配 (总共需选 {req_b} 个)**")
        b_req_0 = st.number_input(f"0路出号数 (余数0, 共{len(b_0)}个码)", 0, req_b, def_b0, key="b0")
        b_req_1 = st.number_input(f"1路出号数 (余数1, 共{len(b_1)}个码)", 0, req_b, def_b1, key="b1")
        b_req_2 = st.number_input(f"2路出号数 (余数2, 共{len(b_2)}个码)", 0, req_b, def_b2, key="b2")
    st.markdown('</div>', unsafe_allow_html=True)

    # 逻辑校验与计算
    sum_f = f_req_0 + f_req_1 + f_req_2
    sum_b = b_req_0 + b_req_1 + b_req_2

    if sum_f != req_f:
        st.error(f"⚠️ **前区数量错误！** 0/1/2路的总和必须等于 {req_f}，目前总和是 {sum_f}。")
    elif sum_b != req_b:
        st.error(f"⚠️ **后区数量错误！** 0/1/2路的总和必须等于 {req_b}，目前总和是 {sum_b}。")
    else:
        # 基于组合公式进行核心运算
        comb_f0 = calculate_bets(len(f_0), f_req_0)
        comb_f1 = calculate_bets(len(f_1), f_req_1)
        comb_f2 = calculate_bets(len(f_2), f_req_2)
        
        comb_b0 = calculate_bets(len(b_0), b_req_0)
        comb_b1 = calculate_bets(len(b_1), b_req_1)
        comb_b2 = calculate_bets(len(b_2), b_req_2)
        
        total_filtered_bets = comb_f0 * comb_f1 * comb_f2 * comb_b0 * comb_b1 * comb_b2
        
        st.success(f"⚡ 根据独立事件乘法原理，当前【前区 {f_req_0}:{f_req_1}:{f_req_2} / 后区 {b_req_0}:{b_req_1}:{b_req_2}】形态下的理论极限为：**{total_filtered_bets}** 注！需投入 **{total_filtered_bets * 2}** 元。")
        
        # 自动生成推荐号码
        if total_filtered_bets > 0:
            if st.button("🎲 提取 5 注符合该 012路 形态的实战号码"):
                st.markdown("#### 🎯 精选实战结果：")
                for i in range(min(5, total_filtered_bets)):
                    pick_f = sorted(random.sample(f_0, f_req_0) + random.sample(f_1, f_req_1) + random.sample(f_2, f_req_2))
                    pick_b = sorted(random.sample(b_0, b_req_0) + random.sample(b_1, b_req_1) + random.sample(b_2, b_req_2))
                    
                    f_str = " ".join([f"{str(x).zfill(2)}" for x in pick_f])
                    b_str = " ".join([f"{str(x).zfill(2)}" for x in pick_b])
                    st.code(f"第 {i+1} 注: [ {f_str} ] + [ {b_str} ]")

else:
    st.warning("⚠️ **脱机金库暂无数据！** 请通过侧边栏上传 xls/csv。")
