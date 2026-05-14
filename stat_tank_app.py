import streamlit as st
import pandas as pd
from collections import Counter
import math
import os
import random
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. 全局页面配置 (绝对保留你最喜欢的极简防黑框 UI)
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
    [data-testid="stHeader"], .stApp > header { display: none !important; pointer-events: none !important; height: 0px !important; }
    #MainMenu, footer, .stDeployButton, .stAppDeployButton, [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛡️ 1.5 安全认证 (内部口令密码墙)
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center; color: #FF4B2B; margin-top: 100px;'>🚀 坦克战略指挥部</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>此系统为内部绝密版本，未授权人员请立即退出。</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pwd = st.text_input("🔒 请输入安全访问口令：", type="password")
        if st.button("验证身份进入系统", use_container_width=True):
            if pwd == "888888":  # 这里修改密码
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ 警告：口令错误，访问被拒绝！")
    st.stop()

# ==========================================
# 2. 智能读取引擎 (防弹清洗 + 自动云端抓取)
# ==========================================
def fetch_latest_data(lottery_code, local_latest_issue):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    url = f"https://datachart.500.com/{lottery_code}/history/newinc/history.php?limit=30"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        tbody = soup.find('tbody', id='tdata')
        if not tbody: return pd.DataFrame()
        
        new_data = []
        for tr in tbody.find_all('tr'):
            if 'class' in tr.attrs: continue
            tds = tr.find_all('td')
            if len(tds) < 10: continue
            
            issue = int(tds[0].text.strip())
            if issue <= local_latest_issue: break # 数据已是最新
            date_str = tds[len(tds)-1].text.strip() # 抓取日期
            
            if lottery_code == 'dlt':
                nums = [int(tds[i].text.strip()) for i in range(1, 8)]
                new_data.append([issue, date_str] + nums)
            else:
                nums = [int(tds[i].text.strip()) for i in range(1, 8)]
                new_data.append([issue, date_str] + nums)
                
        if new_data:
            cols = ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '后1', '后2'] if lottery_code == 'dlt' else ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '前6', '后1']
            return pd.DataFrame(new_data, columns=cols)
    except Exception: pass
    return pd.DataFrame()

@st.cache_data(ttl=300)
def load_local_data(lottery_code, uploaded_file=None):
    df_local = pd.DataFrame()
    source = uploaded_file if uploaded_file else (f"{lottery_code}.csv" if os.path.exists(f"{lottery_code}.csv") else (f"{lottery_code}.xls" if os.path.exists(f"{lottery_code}.xls") else None))
    
    if source:
        try:
            if hasattr(source, 'seek'): source.seek(0)
            if str(source).endswith(('xls','xlsx')):
                df_raw = pd.read_excel(source, header=None, dtype=str)
            else:
                df_raw = pd.read_csv(source, encoding_errors='ignore', header=None, dtype=str)
                
            cols_use = [0, 1, 2, 3, 4, 5, 6, 7, 8] # 必须带上日期列
            c_names = ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '后1', '后2'] if lottery_code == 'dlt' else ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '前6', '后1']
            
            df_raw = df_raw.iloc[:, cols_use]
            df_raw.columns = c_names
            df_raw['前1'] = pd.to_numeric(df_raw['前1'], errors='coerce')
            df_raw = df_raw.dropna(subset=['前1'])
            df_raw['期号'] = df_raw['期号'].astype(str).str.replace(r'\D', '', regex=True)
            df_raw['期号'] = pd.to_numeric(df_raw['期号'], errors='coerce').fillna(0).astype(int)
            for c in c_names[2:]: df_raw[c] = pd.to_numeric(df_raw[c], errors='coerce').fillna(0).astype(int)
            df_local = df_raw[(df_raw['前1']>0)&(df_raw['前1']<=35)].sort_values(by='期号', ascending=False).reset_index(drop=True)
        except Exception: pass
        
    local_latest = int(df_local.iloc[0]['期号']) if not df_local.empty else 0
    df_new = fetch_latest_data(lottery_code, local_latest)
    
    new_count = len(df_new)
    if not df_new.empty:
        df_final = pd.concat([df_new, df_local], ignore_index=True)
    else:
        df_final = df_local
        
    if not df_final.empty:
        df_final['日期_解析'] = pd.to_datetime(df_final['日期'], errors='coerce')
        df_final['星期'] = df_final['日期_解析'].dt.dayofweek
        
    return df_final, new_count

# ==========================================
# 3. 核心运算与深度扫描逻辑 (带上最新加的重号连号)
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

def calculate_bets(n, r): return math.comb(n, r) if r <= n and r >= 0 else 0

def scan_advanced_patterns(df_slice, df_full, is_dlt):
    front_cols = ['前1', '前2', '前3', '前4', '前5'] if is_dlt else ['前1', '前2', '前3', '前4', '前5', '前6']
    repeat_count = 0; consecutive_count = 0
    for idx, row in df_slice.iterrows():
        nums = sorted([row[c] for c in front_cols])
        if any(nums[i+1] - nums[i] == 1 for i in range(len(nums)-1)): consecutive_count += 1
        full_idx = df_full.index[df_full['期号'] == row['期号']].tolist()
        if full_idx and full_idx[0] + 1 < len(df_full):
            prev_nums = set([df_full.iloc[full_idx[0] + 1][c] for c in front_cols])
            if len(set(nums).intersection(prev_nums)) > 0: repeat_count += 1
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
# 4. 侧边栏 (战术期数回归！)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    st.markdown("🔗 **[🔙 返回主站系统](/)**") 
    st.markdown("---")
    lottery_type = st.selectbox("🎯 切换演算频道", ["双色球 (SSQ)", "大乐透 (DLT)"])
    
    # 【找回丢失的功能】固定的战术期数下拉框
    period_limit = st.selectbox("📅 战术期数锁定", [5, 10, 29, 30, 50, 100], index=4)
    if period_limit == 5: st.caption("💡 战术提示: 5期极短线，适合单看后区蓝球走势。")
    if period_limit == 29: st.caption("💡 战术提示: 29期中短线，适合红蓝双区联动复盘。")
    
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
st.header(f"🚀 雷达监测：{lottery_type}")

with st.spinner("📡 正在连线云端检测最新开奖数据..."):
    df_base, new_count = load_local_data(lottery_code, uploaded_file)

if not df_base.empty:
    latest_issue = str(df_base.iloc[0]['期号'])
    
    if new_count > 0:
        st.success(f"⚡ 自动抓取成功：已自动补齐最新的 **{new_count}** 期数据！当前最新: 第 **{latest_issue}** 期。")
        
    # 【找回丢失的功能】高级战术过滤雷达
    st.markdown("### 📡 开启高级过滤雷达")
    filter_mode = st.radio("选择分析维度", ["默认 (近期连贯走势)", "历史同期对比", "星期独立走势"], horizontal=True)
    
    if filter_mode == "历史同期对比":
        suffix = latest_issue[-3:]
        df_filtered = df_base[df_base['期号'].astype(str).str.endswith(suffix)]
        st.info(f"📅 **已锁定历史同期**：正在为您分析历年来尾号为 **{suffix}** 的所有往期数据。")
    elif filter_mode == "星期独立走势":
        c1, c2 = st.columns([1, 2])
        with c1:
            week_target = st.selectbox("选择开奖日", ["周一", "周三", "周六"] if is_dlt else ["周二", "周四", "周日"])
            week_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周六": 5, "周日": 6}
        df_filtered = df_base[df_base['星期'] == week_map[week_target]]
        st.info(f"📆 **已开启星期独立走势**：正在深度挖掘 **{week_target}** 的特有规律。")
    else:
        df_filtered = df_base

    # 执行切割
    df = df_filtered.head(period_limit)
    actual_periods = len(df)
    
    with st.expander(f"🟢 数据加载成功！共捕获 {actual_periods} 期精准数据 (展开查看CSV)"):
        st.dataframe(df.head(10).astype(str), use_container_width=True)

    # 【找回丢失的功能】重号连号深度扫描
    st.markdown("---")
    st.subheader("🕵️‍♂️ 形态深度扫描引擎")
    repeat_num, cons_num = scan_advanced_patterns(df, df_base, is_dlt)
    rc1, rc2 = st.columns(2)
    rc1.warning(f"🔁 **前区重号规律**：在这 {actual_periods} 期中，有 **{repeat_num}** 期开出了上一期的落号。(发生概率: **{repeat_num/actual_periods*100:.1f}%**)")
    rc2.error(f"🔗 **前区连号规律**：在这 {actual_periods} 期中，有 **{cons_num}** 期出现了连号组合。(发生概率: **{cons_num/actual_periods*100:.1f}%**)")

    # 彩色频次矩阵
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
    
    # 基础计算器与导出
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
    
    # ==========================================
    # 📐 012路形态过滤引擎 
    # ==========================================
    st.subheader("📐 012路形态过滤引擎 (基于概率论与组合数学)")
    st.caption("运用你提供的公式文档，通过排列组合 $C_n^k$ 和独立事件乘法原理，精准计算特定 012路 形态的注数！")
    
    with st.expander("📝 展开查看底层计算公式参考"):
        st.markdown("基于《计算公式000.docx》：")
        st.latex(r"C_n^k = \frac{n!}{k!(n-k)!} \quad \text{(组合数)}")
        st.latex(r"P(AB) = P(A)P(B) \quad \text{(独立事件与乘法原理)}")

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
        
        st.success(f"⚡ 根据独立事件乘法原理，当前形态下的理论极限为：**{total_filtered_bets}** 注！需投入 **{total_filtered_bets * 2}** 元。")
        
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
