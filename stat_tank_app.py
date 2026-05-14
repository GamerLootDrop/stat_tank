import streamlit as st
import pandas as pd
from collections import Counter
import math
import os
import random

# ==========================================
# 1. 全局页面配置 (完全保留你的极简防黑框 UI)
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
    
    /* 彻底封死顶部区域：禁止点击、高度归零 */
    [data-testid="stHeader"], .stApp > header {
        display: none !important;
        pointer-events: none !important;
        height: 0px !important;
    }
    
    /* 深度抹除所有官方图标和菜单按钮 */
    #MainMenu, footer, .stDeployButton, .stAppDeployButton, [data-testid="stToolbar"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 智能暴力清洗引擎 (新装载：解决统计不准)
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
        # 暴力读取：无视表头，全当字符串读入，防止错位
        if is_excel:
            df_raw = pd.read_excel(file_source, header=None, dtype=str)
        else:
            df_raw = pd.read_csv(file_source, encoding_errors='ignore', header=None, dtype=str)

        # 智能锁定列 (抓取第0列期号，第1列日期，以及开奖号)
        cols_to_use = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        if lottery_code == 'dlt':
            col_names = ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '后1', '后2']
        else:
            col_names = ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '前6', '后1']
            
        df_raw = df_raw.iloc[:, cols_to_use]
        df_raw.columns = col_names

        # 暴力清洗开奖号码列：转为数字，非数字变 NaN，然后清理掉
        df_raw['前1'] = pd.to_numeric(df_raw['前1'], errors='coerce')
        df_raw = df_raw.dropna(subset=['前1']) 
        
        # 期号去杂质，确保排序正确
        df_raw['期号'] = df_raw['期号'].astype(str).str.replace(r'\D', '', regex=True)
        df_raw['期号'] = pd.to_numeric(df_raw['期号'], errors='coerce').fillna(0).astype(int)
        
        # 尝试解析日期以供"按星期"走势使用
        df_raw['日期_解析'] = pd.to_datetime(df_raw['日期'], errors='coerce')
        df_raw['星期'] = df_raw['日期_解析'].dt.dayofweek # 0是周一，6是周日

        for col in col_names:
            if col not in ['期号', '日期']:
                df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0).astype(int)
                
        # 严格过滤掉非法开奖行
        df_raw = df_raw[(df_raw['前1'] > 0) & (df_raw['前1'] <= 35)]
        return df_raw.sort_values(by='期号', ascending=False).reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame()

# ==========================================
# 3. 核心运算与形态扫描逻辑 (保留 + 升级)
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

# 【新装载】深度形态扫描器 (重号/连号)
def scan_advanced_patterns(df_slice, df_full, is_dlt):
    front_cols = ['前1', '前2', '前3', '前4', '前5'] if is_dlt else ['前1', '前2', '前3', '前4', '前5', '前6']
    repeat_count = 0
    consecutive_count = 0
    
    for idx, row in df_slice.iterrows():
        nums = sorted([row[c] for c in front_cols])
        # 扫描连号
        has_consecutive = any(nums[i+1] - nums[i] == 1 for i in range(len(nums)-1))
        if has_consecutive: consecutive_count += 1
            
        # 扫描重号 (需到总库比对上一期)
        full_idx = df_full.index[df_full['期号'] == row['期号']].tolist()
        if full_idx and full_idx[0] + 1 < len(df_full):
            prev_row = df_full.iloc[full_idx[0] + 1]
            prev_nums = set([prev_row[c] for c in front_cols])
            if len(set(nums).intersection(prev_nums)) > 0:
                repeat_count += 1
                
    return repeat_count, consecutive_count

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
# 4. 侧边栏 (战术选项升级)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    lottery_type = st.selectbox("🎯 切换演算频道", ["双色球 (SSQ)", "大乐透 (DLT)"])
    
    # 【升级】顾客要求的固定战术期数
    period_limit = st.selectbox("📅 战术期数锁定", [5, 10, 29, 30, 50, 100], index=4)
    if period_limit == 5: st.caption("💡 战术提示: 5期极短线，适合单看后区蓝球走势。")
    if period_limit == 29: st.caption("💡 战术提示: 29期中短线，适合红蓝双区联动复盘。")
    
    st.markdown("---")
    st.markdown("### 🗄️ 数据库管理")
    uploaded_file = st.file_uploader(f"临时投喂 {lottery_type} 数据", type=['csv', 'xls', 'xlsx'])

is_dlt = "DLT" in lottery_type
lottery_code = 'dlt' if is_dlt else 'ssq'
req_f, req_b = (5, 2) if is_dlt else (6, 1)
max_f, max_b = (35, 12) if is_dlt else (33, 16)

# ==========================================
# 5. 主画面 (搭载全新战术雷达)
# ==========================================
df_base = load_local_data(lottery_code, uploaded_file)

if not df_base.empty:
    latest_issue = str(df_base.iloc[0]['期号'])
    
    st.header(f"🚀 雷达监测：{lottery_type} (最新 {latest_issue} 期)")
    
    # 【新装载】多维战术过滤面板
    st.markdown("### 📡 开启高级过滤雷达")
    filter_mode = st.radio("选择分析维度", ["默认 (近期连贯走势)", "历史同期对比", "星期独立走势"], horizontal=True)
    
    if filter_mode == "历史同期对比":
        # 抓取最新期号的后3位作为同期标识
        suffix = latest_issue[-3:]
        df_filtered = df_base[df_base['期号'].astype(str).str.endswith(suffix)]
        st.info(f"📅 **已锁定历史同期**：正在为您分析历年来尾号为 **{suffix}** 的所有开奖数据。")
    elif filter_mode == "星期独立走势":
        c1, c2 = st.columns([1, 2])
        with c1:
            if is_dlt:
                week_target = st.selectbox("选择开奖日", ["周一", "周三", "周六"])
                week_map = {"周一": 0, "周三": 2, "周六": 5}
            else:
                week_target = st.selectbox("选择开奖日", ["周二", "周四", "周日"])
                week_map = {"周二": 1, "周四": 3, "周日": 6}
        df_filtered = df_base[df_base['星期'] == week_map[week_target]]
        st.info(f"📆 **已开启星期独立走势**：正在深度挖掘 **{week_target}** 的特有规律。")
    else:
        df_filtered = df_base
        st.info("连贯走势模式运行中...")

    # 执行期数切割
    df = df_filtered.head(period_limit)
    actual_periods = len(df)
    
    with st.expander(f"🟢 数据加载成功！共捕获 {actual_periods} 期精准数据 (展开校验)"):
        st.dataframe(df.head(10).astype(str), use_container_width=True)

    # 【新装载】重号 / 连号扫描仪
    st.markdown("---")
    st.subheader("🕵️‍♂️ 形态深度扫描引擎")
    repeat_num, cons_num = scan_advanced_patterns(df, df_base, is_dlt)
    rc1, rc2 = st.columns(2)
    rc1.warning(f"🔁 **前区重号规律**：在这 {actual_periods} 期中，有 **{repeat_num}** 期开出了上一期的落号。(发生概率: **{repeat_num/actual_periods*100:.1f}%**)")
    rc2.error(f"🔗 **前区连号规律**：在这 {actual_periods} 期中，有 **{cons_num}** 期出现了连号组合。(发生概率: **{cons_num/actual_periods*100:.1f}%**)")

    # (保留) 频次矩阵渲染
    st.markdown("---")
    st.subheader("🧬 核心出现频次矩阵")
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
            html_str += f"<div class='stat-row'><div class='freq-tag'>{freq} 次</div><div class='ball-container' style='margin-bottom:0;'>{balls_html}</div></div>"
        return html_str

    with col1:
        st.markdown(f"### {'🔵' if is_dlt else '🔴'} 前区 (1-{max_f})")
        st.markdown(render_balls(front_counts, front_color_class), unsafe_allow_html=True)
    with col2:
        st.markdown(f"### {'🟡' if is_dlt else '🔵'} 后区 (1-{max_b})")
        st.markdown(render_balls(back_counts, back_color_class), unsafe_allow_html=True)

    st.markdown("---")
    
    # (保留) 基础计算器与导出
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
        text_report = generate_text_report(f"{lottery_type} {filter_mode} ({actual_periods}期)", front_counts, back_counts, is_dlt)
        st.download_button("📥 下载统计 txt", data=text_report, file_name=f"{lottery_type}_report.txt", mime="text/plain", use_container_width=True)

    st.markdown("---")
    
    # (完全保留) 012路形态过滤引擎 
    st.subheader("📐 012路形态过滤引擎 (基于概率论与组合数学)")
    st.caption("运用你提供的公式文档，通过排列组合 $C_n^k$ 和独立事件乘法原理，精准计算特定 012路 形态的注数！")
    
    with st.expander("📝 展开查看底层计算公式参考"):
        st.markdown("基于《计算公式000.docx》：")
        st.latex(r"C_n^k = \frac{n!}{k!(n-k)!} \quad \text{(组合数)}")
        st.latex(r"P(AB) = P(A)P(B) \quad \text{(独立事件与乘法原理)}")
        st.markdown("总注数 = $C_{N_{f0}}^{k_{f0}} \\times C_{N_{f1}}^{k_{f1}} \\times C_{N_{f2}}^{k_{f2}} \\times C_{N_{b0}}^{k_{b0}} \\times C_{N_{b1}}^{k_{b1}} \\times C_{N_{b2}}^{k_{b2}}$")

    f_0 = [x for x in range(1, max_f + 1) if x % 3 == 0]
    f_1 = [x for x in range(1, max_f + 1) if x % 3 == 1]
    f_2 = [x for x in range(1, max_f + 1) if x % 3 == 2]
    
    b_0 = [x for x in range(1, max_b + 1) if x % 3 == 0]
    b_1 = [x for x in range(1, max_b + 1) if x % 3 == 1]
    b_2 = [x for x in range(1, max_b + 1) if x % 3 == 2]

    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    f_col1, f_col2 = st.columns(2)
    
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

    sum_f = f_req_0 + f_req_1 + f_req_2
    sum_b = b_req_0 + b_req_1 + b_req_2

    if sum_f != req_f:
        st.error(f"⚠️ **前区数量错误！** 0/1/2路的总和必须等于 {req_f}，目前总和是 {sum_f}。")
    elif sum_b != req_b:
        st.error(f"⚠️ **后区数量错误！** 0/1/2路的总和必须等于 {req_b}，目前总和是 {sum_b}。")
    else:
        comb_f0 = calculate_bets(len(f_0), f_req_0)
        comb_f1 = calculate_bets(len(f_1), f_req_1)
        comb_f2 = calculate_bets(len(f_2), f_req_2)
        
        comb_b0 = calculate_bets(len(b_0), b_req_0)
        comb_b1 = calculate_bets(len(b_1), b_req_1)
        comb_b2 = calculate_bets(len(b_2), b_req_2)
        
        total_filtered_bets = comb_f0 * comb_f1 * comb_f2 * comb_b0 * comb_b1 * comb_b2
        
        st.success(f"⚡ 根据独立事件乘法原理，当前【前区 {f_req_0}:{f_req_1}:{f_req_2} / 后区 {b_req_0}:{b_req_1}:{b_req_2}】形态下的理论极限为：**{total_filtered_bets}** 注！需投入 **{total_filtered_bets * 2}** 元。")
        
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
