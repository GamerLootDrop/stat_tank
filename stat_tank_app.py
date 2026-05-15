import streamlit as st
import pandas as pd
from collections import Counter
import math
import os
import random
import requests
from bs4 import BeautifulSoup
import time  
import re
import itertools

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
    .filter-box { background: #1E1E1E; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 15px;}
    
    /* 彻底封死顶部区域：禁止点击、高度归零 */
    [data-testid="stHeader"], .stApp > header { display: none !important; pointer-events: none !important; height: 0px !important; }
    #MainMenu, footer, .stDeployButton, .stAppDeployButton, [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
    
    /* 还原图1：高阶控制台UI */
    .ratio-badge { background-color: #262626; border: 1px solid #444; padding: 8px 15px; border-radius: 6px; font-weight: bold; text-align: center; font-size: 16px;}
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
            if pwd == "888888":  
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ 警告：口令错误，访问被拒绝！")
    st.stop()


# ==========================================
# 2. 智能读取引擎 (防频刷冷却雷达)
# ==========================================
def fetch_latest_data(lottery_code, local_latest_issue):
    """
    高精度实时全网增量同步爬虫引擎 (带5分钟频繁抓取冷却拦截器)
    """
    if f"err_{lottery_code}" in st.session_state:
        del st.session_state[f"err_{lottery_code}"]

    now_time = time.time()
    last_fetch_key = f"last_fetch_time_{lottery_code}"
    if last_fetch_key in st.session_state:
        if now_time - st.session_state[last_fetch_key] < 300:
            return pd.DataFrame()

    urls = [
        f"https://datachart.500.com/{lottery_code}/history/newinc/history.php?limit=50&_t={int(now_time)}", 
        f"https://datachart.500.com/{lottery_code}/history/inc/history.php?limit=50&_t={int(now_time)}"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": f"https://datachart.500.com/{lottery_code}/history/history.shtml"
    }
    
    new_rows = []
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code != 200:
                continue
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            trs = soup.find_all('tr', class_=['t_tr1', 't_tr2', 't_tr']) or soup.find_all('tr')
            
            for tr in trs:
                tds = tr.find_all('td')
                if len(tds) < 8: 
                    continue 

                iss_str = re.sub(r'\D', '', tds[0].get_text(strip=True))
                if len(iss_str) < 3: 
                    continue
                issue_val = int("20" + iss_str[:10]) if len(iss_str) == 5 else int(iss_str[:10])
                
                if issue_val <= local_latest_issue:
                    continue
                
                balls = []
                for td in tds[1:]:
                    text = td.get_text(strip=True)
                    if text.isdigit():
                        balls.append(int(text))
                
                date_str = tds[-1].get_text(strip=True)
                if not re.search(r'\d{4}-\d{2}-\d{2}', date_str):
                    date_str = time.strftime("%Y-%m-%d", time.localtime())
                
                if len(balls) >= 7:
                    core_balls = balls[:7]
                    new_rows.append([issue_val, date_str, core_balls[0], core_balls[1], core_balls[2], core_balls[3], core_balls[4], core_balls[5], core_balls[6]])
            
            if new_rows:
                st.session_state[last_fetch_key] = now_time
                break 
        except Exception:
            continue

    if new_rows:
        cols = ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '后1', '后2'] if lottery_code == 'dlt' else ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '前6', '后1']
        df_new = pd.DataFrame(new_rows, columns=cols)
        return df_new.sort_values(by='期号', ascending=False).reset_index(drop=True)
    else:
        return pd.DataFrame()


@st.cache_data(ttl=60)  
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
                
            cols_use = [0, 1, 2, 3, 4, 5, 6, 7, 8]
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
        df_final = df_final.drop_duplicates(subset=['期号'], keep='first') 
        df_final = df_final.sort_values(by='期号', ascending=False).reset_index(drop=True)
        df_final['日期_解析'] = pd.to_datetime(df_final['日期'], errors='coerce')
        df_final['星期'] = df_final['日期_解析'].dt.dayofweek
        
    return df_final, new_count

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

# 用于012路精确匹配筛选的核心算法
def check_012_ratio(numbers, target_0, target_1, target_2):
    c0 = sum(1 for x in numbers if x % 3 == 0)
    c1 = sum(1 for x in numbers if x % 3 == 1)
    c2 = sum(1 for x in numbers if x % 3 == 2)
    return c0 == target_0 and c1 == target_1 and c2 == target_2

# ==========================================
# 4. 侧边栏
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    st.markdown("🔗 **[🔙 返回主站系统](/)**") 
    
    if st.button("🔄 解除冷却：强制连网冲刷", use_container_width=True):
        lottery_code_tmp = 'dlt' if "DLT" in st.session_state.get("canvas_channel", "双色球 (SSQ)") else 'ssq'
        if f"last_fetch_time_{lottery_code_tmp}" in st.session_state:
            del st.session_state[f"last_fetch_time_{lottery_code_tmp}"]
        load_local_data.clear() 
        st.rerun() 

    st.markdown("---")
    lottery_type = st.selectbox("🎯 切换演算频道", ["双色球 (SSQ)", "大乐透 (DLT)"], key="canvas_channel")
    period_limit = st.selectbox("📅 战术期数锁定", [5, 10, 29, 30, 50, 100], index=3)
    st.markdown("---")
    st.markdown("### 🗄️ 数据库管理 (Admin)")
    uploaded_file = st.file_uploader(f"临时投喂 {lottery_type} 数据", type=['csv', 'xls', 'xlsx'])

is_dlt = "DLT" in lottery_type
lottery_code = 'dlt' if is_dlt else 'ssq'
req_f, req_b = (5, 2) if is_dlt else (6, 1)
max_f, max_b = (35, 12) if is_dlt else (33, 16)

# ==========================================
# 5. 主画面区
# ==========================================
st.header(f"🚀 雷达监测：{lottery_type}")

with st.spinner("📡 正在连线云端检测最新开奖数据..."):
    df_base, new_count = load_local_data(lottery_code, uploaded_file)

if f"err_{lottery_code}" in st.session_state:
    st.sidebar.error(f"🚨 联网雷达警告：\n{st.session_state[f'err_{lottery_code}']}\n\n💡 应对方案：请通过下方 Admin 投喂最新的本地文件。")

if not df_base.empty:
    latest_issue = str(df_base.iloc[0]['期号'])
    
    if new_count > 0:
        st.success(f"⚡ 自动抓取成功：已自动补齐最新的 **{new_count}** 期数据！当前最新: 第 **{latest_issue}** 期。")
    else:
        st.info(f"🟢 当前数据库最新状态：最新期号 第 **{latest_issue}** 期。(5分钟频繁拦截防护中)")
        
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

    df = df_filtered.head(period_limit)
    actual_periods = len(df)
    
    with st.expander(f"🟢 数据加载成功！共捕获 {actual_periods} 期精准数据 (展开查看明细)"):
        st.dataframe(df.astype(str), use_container_width=True)

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
    
    # =======================================================
    # 📐 搬迁改造：100%还原图1样式的傻瓜化胆拖+滑块缩水控制台面板
    # =======================================================
    st.subheader("🔥 机构级高阶缩水终端 (1比1完美重塑版)")
    st.caption("完全融合图1的胆拖大池挑选机制与012路实时拉杆滑块缩水引擎")
    
    # 步骤一：设定号码大池 (胆拖模式) —— 完美复制图1左半边和右半边
    with st.expander("👉 第一步：设定基础大底池条件 (胆拖模式)", expanded=True):
        ui_col1, ui_col2 = st.columns(2)
        with ui_col1:
            # 动态调整前区最大选球限制（大乐透前区最多选4个胆，双色球最多5个胆）
            max_dan_limit = req_f - 1
            red_dan = st.multiselect(f"{'🔵' if is_dlt else '🔴'} 选定前区【胆码】 (必出号)", range(1, max_f + 1), max_selections=max_dan_limit)
            red_tuo = st.multiselect(f"⭕ 选定前区【拖码】 (候选号池)", [i for i in range(1, max_f + 1) if i not in red_dan])
        with ui_col2:
            blue_balls = st.multiselect(f"{'🟡' if is_dlt else '🔵'} 选定【后区号码】", range(1, max_b + 1))
            
        st.info(f"当前大底选中状态 ➡️ 前区胆码: {len(red_dan)} 个，前区拖码: {len(red_tuo)} 个，后区选码: {len(blue_balls)} 个")

    # 步骤二：012路拉杆交互控制台 —— 完美复制图1下半部分的滑块配比
    st.markdown("#### 👉 第二步：调配 012路 核心比例拉杆")
    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    
    def_f0, def_f1, def_f2 = (2, 2, 1) if is_dlt else (2, 2, 2)
    def_b0, def_b1, def_b2 = (0, 1, 1) if is_dlt else (0, 1, 0)
    
    st.markdown(f"**前区 012路 个数滑动条 (三项总和必须严格等于 {req_f})**")
    sc1, sc2, sc3 = st.columns(3)
    with sc1: f_req_0 = st.slider("前区 0路 (整除3) 个数", 0, req_f, def_f0, key="v1_f0")
    with sc2: f_req_1 = st.slider("前区 1路 (余1) 个数", 0, req_f, def_f1, key="v1_f1")
    with sc3: f_req_2 = st.slider("前区 2路 (余2) 个数", 0, req_f, def_f2, key="v1_f2")
    
    st.markdown(f"""
    <div style='display: flex; gap: 10px; margin-bottom: 20px;'>
        <div class='ratio-badge' style='color:#6FB1FC; border-color:#6FB1FC;'>前区 0路设定：{f_req_0} 个</div>
        <div class='ratio-badge' style='color:#FF4B2B; border-color:#FF4B2B;'>前区 1路设定：{f_req_1} 个</div>
        <div class='ratio-badge' style='color:#00E676; border-color:#00E676;'>前区 2路设定：{f_req_2} 个</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"**后区 012路 个数滑动条 (三项总和必须严格等于 {req_b})**")
    sbc1, sbc2, sbc3 = st.columns(3)
    with sbc1: b_req_0 = st.slider("后区 0路 个数", 0, req_b, def_b0, key="v1_b0")
    with sbc2: b_req_1 = st.slider("后区 1路 个数", 0, req_b, def_b1, key="v1_b1")
    with sbc3: b_req_2 = st.slider("后区 2路 个数", 0, req_b, def_b2, key="v1_b2")
    
    st.markdown(f"""
    <div style='display: flex; gap: 10px;'>
        <div class='ratio-badge' style='color:#6FB1FC; border-color:#6FB1FC;'>后区 0路设定：{b_req_0} 个</div>
        <div class='ratio-badge' style='color:#FF4B2B; border-color:#FF4B2B;'>后区 1路设定：{b_req_1} 个</div>
        <div class='ratio-badge' style='color:#00E676; border-color:#00E676;'>后区 2路设定：{b_req_2} 个</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 步骤三：执行高阶缩水过滤
    sum_f = f_req_0 + f_req_1 + f_req_2
    sum_b = b_req_0 + b_req_1 + b_req_2

    if sum_f != req_f:
        st.error(f"⚠️ **拉杆配比错误**：前区012路设定总和为 {sum_f}，不等于开奖规定所需的 {req_f} 个！请重新滑动。")
    elif sum_b != req_b:
        st.error(f"⚠️ **拉杆配比错误**：后区012路设定总和为 {sum_b}，不等于开奖规定所需的 {req_b} 个！请重新滑动。")
    else:
        # 计算拖码需要选多少个
        need_tuo_count = req_f - len(red_dan)
        
        if need_tuo_count < 0 or len(red_tuo) < need_tuo_count:
            st.warning(f"💡 基础数量不足：当前前区胆码有 {len(red_dan)} 个，还需从拖码池中自动抽取 {need_tuo_count} 个。但你选的拖码候选球不足，无法组合！")
        elif len(blue_balls) < req_b:
            st.warning(f"💡 后区数量不足：请在第一步中至少勾选 {req_b} 个后区号码！")
        else:
            # 开始进行排列组合计算大底数
            all_front_combinations = list(itertools.combinations(red_tuo, need_tuo_count))
            all_back_combinations = list(itertools.combinations(blue_balls, req_b))
            
            raw_total_bets = len(all_front_combinations) * len(all_back_combinations)
            
            if st.button("⚡ 启动高级马尔可夫演练与条件过滤 (智能缩水)", use_container_width=True):
                valid_front_combs = []
                # 过滤前区
                for tuo_comb in all_front_combinations:
                    full_front = sorted(list(red_dan) + list(tuo_comb))
                    if check_012_ratio(full_front, f_req_0, f_req_1, f_req_2):
                        valid_front_combs.append(full_front)
                
                # 过滤后区
                valid_back_combs = []
                for b_comb in all_back_combinations:
                    if check_012_ratio(b_comb, b_req_0, b_req_1, b_req_2):
                        valid_back_combs.append(b_comb)
                
                # 最终交叉组合数
                final_filtered_bets = len(valid_front_combs) * len(valid_back_combs)
                
                st.success(f"🎉 缩水完成！原始大底共计 {raw_total_bets} 注，经过 012路 滑块精确洗礼后，仅剩 **{final_filtered_bets}** 注极品精华！")
                
                if final_filtered_bets > 0:
                    st.markdown("### 🏆 核心推荐精选号组 (最多展示前20注)：")
                    
                    # 组合出最终的结果集
                    display_count = 0
                    for f_comb in valid_front_combs:
                        for b_comb in valid_back_combs:
                            if display_count >= 20:
                                break
                            f_str = " ".join([f"{str(x).zfill(2)}" for x in f_comb])
                            b_str = " ".join([f"{str(x).zfill(2)}" for x in b_comb])
                            st.code(f"极品第 {display_count + 1} 注: [ {f_str} ] + [ {b_str} ]")
                            display_count += 1
                else:
                    st.error("❌ 过滤提示：大池子里的号码组合与您拉动的 012路 配比冲突，没有号能熬过该缩水条件。请调整滑块配比或扩大选球池！")

    st.markdown("---")
    st.subheader("🖨️ 系统辅助工具")
    text_report = generate_text_report(f"{lottery_type} ({actual_periods}期)", front_counts, back_counts, is_dlt)
    st.download_button("📥 下载基础统计数据 txt 报告", data=text_report, file_name=f"{lottery_type}_report.txt", mime="text/plain", use_container_width=True)

else:
    st.warning("⚠️ **脱机金库暂无数据！** 请通过侧边栏上传 xls/csv。")
