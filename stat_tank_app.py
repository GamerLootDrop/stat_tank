import streamlit as st
import pandas as pd
from collections import Counter
import math
import os
import random
import requests
from bs4 import BeautifulSoup
import time  # 引入时间戳，用来击穿网站的反爬缓存
import re
import itertools

# ==========================================
# 1. 全局页面配置 (已针对手机小屏幕与极简防黑框 UI 进行融合调优)
# ==========================================
st.set_page_config(page_title="坦克指挥控制台", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    /* 球体在手机上自适应紧凑排列 */
    .ball-container { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
    .ball {
        width: 34px; height: 34px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: bold; font-size: 14px; color: white;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    .ball-red { background: radial-gradient(circle at 10px 10px, #FF4B2B, #B31217); box-shadow: 0 0 6px rgba(255, 75, 43, 0.5); }
    .ball-blue { background: radial-gradient(circle at 10px 10px, #6FB1FC, #0052D4);
        box-shadow: 0 0 6px rgba(0, 82, 212, 0.5); }
    .ball-yellow { background: radial-gradient(circle at 10px 10px, #FFD700, #F39C12);
        color: #333; text-shadow: none; box-shadow: 0 0 6px rgba(243, 156, 18, 0.5);
    }
    
    /* 频次横条在手机和电脑上都能自适应紧凑排列 */
    .freq-tag {
        background-color: #2b2b2b;
        color: #00E676; padding: 4px 8px;
        border-radius: 5px; font-weight: bold; margin-right: 10px;
        border-left: 4px solid #00E676;
        min-width: 65px; text-align: center;
        font-size: 13px;
    }
    .stat-row { display: flex; align-items: center; margin-bottom: 8px; background: #1E1E1E; padding: 8px;
        border-radius: 8px;}
    .filter-box { background: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333;
        margin-bottom: 12px;}
    
    /* 彻底封死顶部区域：禁止点击、高度归零 */
    [data-testid="stHeader"], .stApp > header { display: none !important;
        pointer-events: none !important; height: 0px !important; }
    #MainMenu, footer, .stDeployButton, .stAppDeployButton, [data-testid="stToolbar"] { display: none !important;
        visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
    
    /* 手机/电脑自适应012路中控UI高亮 */
    .ratio-badge { background-color: #262626;
        border: 1px solid #444; padding: 6px 12px; border-radius: 6px; font-weight: bold; text-align: center; font-size: 14px;
        flex: 1;}
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
# 2. 智能读取引擎 (已彻底废除频繁刷新冷却限制，实现全自动随时跟进最新期号)
# ==========================================
def fetch_latest_data(lottery_code, local_latest_issue, custom_limit=50):
    """
    高精度实时全网增量同步爬虫引擎 (带随机时间戳击穿，保证手机端和电脑端每次进来都是最新数据)
    """
    if f"err_{lottery_code}" in st.session_state:
        del st.session_state[f"err_{lottery_code}"]

    now_time = time.time()
    
    urls = [
        f"https://datachart.500.com/{lottery_code}/history/newinc/history.php?limit={custom_limit}&_t={int(now_time)}", 
        f"https://datachart.500.com/{lottery_code}/history/inc/history.php?limit={custom_limit}&_t={int(now_time)}"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Referer": f"https://datachart.500.com/{lottery_code}/history/history.shtml"
    }
    
    new_rows = []
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code != 200: continue
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            trs = soup.find_all('tr', class_=['t_tr1', 't_tr2', 't_tr']) or soup.find_all('tr')
            
            for tr in trs:
                tds = tr.find_all('td')
                if len(tds) < 8: continue 

                iss_str = re.sub(r'\D', '', tds[0].get_text(strip=True))
                if len(iss_str) < 3: continue
                issue_val = int("20" + iss_str[:10]) if len(iss_str) == 5 else int(iss_str[:10])
                
                if custom_limit == 50 and issue_val <= local_latest_issue: continue
                
                balls = []
                for td in tds[1:]:
                    text = td.get_text(strip=True)
                    if text.isdigit(): balls.append(int(text))
               
                date_str = tds[-1].get_text(strip=True)
                if not re.search(r'\d{4}-\d{2}-\d{2}', date_str):
                    date_str = time.strftime("%Y-%m-%d", time.localtime())
                
                if len(balls) >= 7:
                    core_balls = balls[:7]
                    new_rows.append([issue_val, date_str, core_balls[0], core_balls[1], core_balls[2], core_balls[3], core_balls[4], core_balls[5], core_balls[6]])
            
            if new_rows:
                break 
        except Exception: continue

    if new_rows:
        cols = ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '后1', '后2'] if lottery_code == 'dlt' else ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '前6', '后1']
        df_new = pd.DataFrame(new_rows, columns=cols)
        return df_new.sort_values(by='期号', ascending=False).reset_index(drop=True)
    return pd.DataFrame()


@st.cache_data(ttl=5)  # 缓存时间大幅缩短至5秒，满足移动端和PC端极速刷新同步需求
def load_local_data(lottery_code, uploaded_file=None, target_mode="默认"):
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
    
    if target_mode == "历史同期对比" and df_local.empty:
        df_new = fetch_latest_data(lottery_code, local_latest, custom_limit=3000)
    else:
        df_new = fetch_latest_data(lottery_code, local_latest, custom_limit=100)
    
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
# 3. 核心运算与深度扫描逻辑
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
    repeat_count = 0
    consecutive_count = 0
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
# 4. 侧边栏 (保留后台重刷按钮与Admin上传)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    st.markdown("🔗 **[🔙 返回主站系统](/)**") 
    
    if st.button("🔄 解除冷却：强制连网冲刷", use_container_width=True):
        load_local_data.clear() 
        st.rerun() 

    st.markdown("---")
    st.markdown("### 🗄️ 数据库管理 (Admin)")
    uploaded_file = st.file_uploader("临时投喂本地开奖文件", type=['csv', 'xls', 'xlsx'])

# ==========================================
# 5. 主画面区 (彩种和战术期数平铺在页面最顶部，手机端绝对可见)
# ==========================================
st.header("🚀 坦克战略指挥中控雷达")

# 手机主屏幕大区：头部黄金双选面板
top_col1, top_col2 = st.columns(2)
with top_col1:
    lottery_type = st.selectbox("🎯 切换开奖频道", ["双色球 (SSQ)", "大乐透 (DLT)"], index=1) # 默认大乐透
with top_col2:
    period_limit = st.selectbox("📅 战术期数锁定", [5, 10, 29, 30, 50, 100], index=3) # 默认30期

is_dlt = "DLT" in lottery_type
lottery_code = 'dlt' if is_dlt else 'ssq'
req_f, req_b = (5, 2) if is_dlt else (6, 1)
max_f, max_b = (35, 12) if is_dlt else (33, 16)

if "filter_mode_state" not in st.session_state:
    st.session_state.filter_mode_state = "历史同期对比"

with st.spinner("📡 正在连线云端检测最新开奖数据..."):
    df_base, new_count = load_local_data(lottery_code, uploaded_file, target_mode=st.session_state.filter_mode_state)

if f"err_{lottery_code}" in st.session_state:
    st.error(f"🚨 联网雷达警告：\n{st.session_state[f'err_{lottery_code}']}\n\n💡 应对方案：请通过左侧 Admin 投喂最新的本地文件。")

if not df_base.empty:
    latest_issue = str(df_base.iloc[0]['期号'])
    
    if new_count > 0:
        st.success(f"⚡ 自动抓取成功：已自动补齐最新的 **{new_count}** 期数据！当前最新: 第 **{latest_issue}** 期。")
    else:
        st.info(f"🟢 当前数据库最新状态：最新期号 第 **{latest_issue}** 期。")
        
    st.markdown("### 📡 开启高级过滤雷达")
    
    filter_mode = st.radio("选择分析维度", ["默认 (近期连贯走势)", "历史同期对比", "星期独立走势"], index=["默认 (近期连贯走势)", "历史同期对比", "星期独立走势"].index(st.session_state.filter_mode_state))
    if filter_mode != st.session_state.filter_mode_state:
        st.session_state.filter_mode_state = filter_mode
        st.rerun()
    
    if filter_mode == "历史同期对比":
        # 1. 提取当前最新期号的后三位数字
        if '期' in latest_issue:
            current_period_str = latest_issue.split('期')[0][-3:]
        else:
            current_period_str = latest_issue[-3:]
            
        # 2. 自动计算玩家真正要打的“下一期”（默认+1）
        default_target_period = int(current_period_str) + 1
        
        # 3. 增加交互微调器：客户想分析哪期，自己决定！默认锁定下一期。
        target_period_int = st.number_input(
            "🎯 请确认您要预测的目标期号 (系统已自动为您 +1 期)：", 
            min_value=1, 
            max_value=160, 
            value=default_target_period, 
            step=1
        )
        
        # 4. 格式化为3位数后缀（如 55 -> "055"）
        target_period_str = f"{target_period_int:03d}"
        
        st.info(f"📅 **已锁定预测同期**：系统正在为您深度调取历年来尾号为 **{target_period_str}** 的所有往期数据！")
        
        # 5. 过滤出真正的预测目标历史库
        df_filtered = df_base[df_base['期号'].astype(str).str.endswith(target_period_str)]
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
    if actual_periods > 0:
        repeat_num, cons_num = scan_advanced_patterns(df, df_base, is_dlt)
        rc1, rc2 = st.columns(2)
        rc1.warning(f"🔁 **前区重号规律**：在这 {actual_periods} 期中，有 **{repeat_num}** 期开出了上一期的落号。(发生概率: **{repeat_num/actual_periods*100:.1f}%**)")
        rc2.error(f"🔗 **前区连号规律**：在这 {actual_periods} 期中，有 **{cons_num}** 期出现了连号组合。(发生概率: **{cons_num/actual_periods*100:.1f}%**)")
    else:
        st.warning("⚠️ 暂无足够的数据周期进行形态扫描，请尝试增加数据库深度。")

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

    # =======================================================
    # 📐 012路智能化智能缩水控制台面板 (加减号微调防手滑版布局)
    # =======================================================
    st.markdown("---")
    st.subheader("⚙️ 012路高阶智能化智能缩水控制台")
    
    with st.expander("📝 查看底层公式与学术概念"):
        st.markdown("基于《计算公式000.docx》：")
        st.latex(r"C_n^k = \frac{n!}{k!(n-k)!} \quad \text{(组合大底底数)}")
        st.markdown("**0路数字**：能能被3整除；**1路数字**：除以3余1；**2路数字**：除以3余2。")

    f_0 = [x for x in range(1, max_f + 1) if x % 3 == 0]
    f_1 = [x for x in range(1, max_f + 1) if x % 3 == 1]
    f_2 = [x for x in range(1, max_f + 1) if x % 3 == 2]
    
    b_0 = [x for x in range(1, max_b + 1) if x % 3 == 0]
    b_1 = [x for x in range(1, max_b + 1) if x % 3 == 1]
    b_2 = [x for x in range(1, max_b + 1) if x % 3 == 2]

    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    
    # 根据你研究出来的 30期同期最强配比，直接预设黄金比例：前区 1:3:1，后区 1:1:0
    def_f0, def_f1, def_f2 = (1, 3, 1) if is_dlt else (2, 2, 2)
    def_b0, def_b1, def_b2 = (1, 1, 0) if is_dlt else (0, 1, 0)
    
    st.markdown(f"#### {'🔵' if is_dlt else '🔴'} 前区 012路数量配比调节器 (总和必须等于 {req_f})")
    sc1, sc2, sc3 = st.columns(3)
    with sc1: f_req_0 = st.number_input("0路出号个数", min_value=0, max_value=req_f, value=def_f0, step=1, key="num_f0")
    with sc2: f_req_1 = st.number_input("1路出号个数", min_value=0, max_value=req_f, value=def_f1, step=1, key="num_f1")
    with sc3: f_req_2 = st.number_input("2路出号个数", min_value=0, max_value=req_f, value=def_f2, step=1, key="num_f2")
    
    # 实时彩色渲染前区选定比例
    st.markdown(f"""
    <div style='display: flex; gap: 10px; margin-bottom: 20px;'>
        <div class='ratio-badge' style='color:#6FB1FC; border-color:#6FB1FC;'>前区0路：{f_req_0} 个</div>
        <div class='ratio-badge' style='color:#FF4B2B; border-color:#FF4B2B;'>前区1路：{f_req_1} 个</div>
        <div class='ratio-badge' style='color:#00E676; border-color:#00E676;'>前区2路：{f_req_2} 个</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"#### {'🟡' if is_dlt else '🔵'} 后区 012路数量配比调节器 (总和必须等于 {req_b})")
    sbc1, sbc2, sbc3 = st.columns(3)
    with sbc1: b_req_0 = st.number_input("0路出号个数", min_value=0, max_value=req_b, value=def_b0, step=1, key="num_b0")
    with sbc2: b_req_1 = st.number_input("1路出号个数", min_value=0, max_value=req_b, value=def_b1, step=1, key="num_b1")
    with sbc3: b_req_2 = st.number_input("2路出号个数", min_value=0, max_value=req_b, value=def_b2, step=1, key="num_b2")
    
    # 实时彩色渲染后区选定比例
    st.markdown(f"""
    <div style='display: flex; gap: 10px;'>
        <div class='ratio-badge' style='color:#6FB1FC; border-color:#6FB1FC;'>后区0路：{b_req_0} 个</div>
        <div class='ratio-badge' style='color:#FF4B2B; border-color:#FF4B2B;'>后区1路：{b_req_1} 个</div>
        <div class='ratio-badge' style='color:#00E676; border-color:#00E676;'>后区2路：{b_req_2} 个</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    sum_f = f_req_0 + f_req_1 + f_req_2
    sum_b = b_req_0 + b_req_1 + b_req_2

    # 逻辑守卫检测与差额智能反馈提示
    if sum_f != req_f:
        diff_f = req_f - sum_f
        if diff_f > 0:
            st.error(f"⚠️ **前区校验失败**：当前已设定 {sum_f} 个，**还差 {diff_f} 个号**！请点击 [＋] 按钮增加。")
        else:
            st.error(f"⚠️ **前区校验失败**：当前已设定 {sum_f} 个，**多选了 {abs(diff_f)} 个号**！请点击 [－] 按钮减少。")
    elif sum_b != req_b:
        diff_b = req_b - sum_b
        if diff_b > 0:
            st.error(f"⚠️ **后区校验失败**：当前已设定 {sum_b} 个，**还差 {diff_b} 个号**！请点击 [＋] 按钮增加。")
        else:
            st.error(f"⚠️ **后区校验失败**：当前已设定 {sum_b} 个，**多选了 {abs(diff_b)} 个号**！请点击 [－] 按钮减少。")
    else:
        comb_f0 = calculate_bets(len(f_0), f_req_0)
        comb_f1 = calculate_bets(len(f_1), f_req_1)
        comb_f2 = calculate_bets(len(f_2), f_req_2)
        
        comb_b0 = calculate_bets(len(b_0), b_req_0)
        comb_b1 = calculate_bets(len(b_1), b_req_1)
        comb_b2 = calculate_bets(len(b_2), b_req_2)
        
        total_filtered_bets = comb_f0 * comb_f1 * comb_f2 * comb_b0 * comb_b1 * comb_b2
        st.success(f"🔥 全保形态验证成功：当前配置形态理论极限组合总数为 **{total_filtered_bets}** 注！需投入 **{total_filtered_bets * 2}** 元。")
        
        if total_filtered_bets > 0:
            if st.button("🎲 启动终极雷达：智能筛选 5 注实战精华号码", use_container_width=True):
                st.markdown("#### 🎯 智能全包池内推荐号组：")
                for i in range(min(5, total_filtered_bets)):
                    pick_f = sorted(random.sample(f_0, f_req_0) + random.sample(f_1, f_req_1) + random.sample(f_2, f_req_2))
                    pick_b = sorted(random.sample(b_0, b_req_0) + random.sample(b_1, b_req_1) + random.sample(b_2, b_req_2))
                    
                    f_str = " ".join([f"{str(x).zfill(2)}" for x in pick_f])
                    b_str = " ".join([f"{str(x).zfill(2)}" for x in pick_b])
                    st.code(f"第 {i+1} 注: [ {f_str} ] + [ {b_str} ]")
else:
    st.warning("⚠️ **脱机金库暂无数据！** 请通过侧边栏上传 xls/csv。")


# ==========================================
# 6. 🪓 炮灰晒票反杀引擎 (文本清洗版 + 明细核对)
# ==========================================
st.markdown("---")
st.header("🪓 炮灰晒票反杀引擎")
st.info("💡 **实战操作指南**：打开别人公众号的【万元大票】或【晒票图片】，用手机长按提取文字（或直接复制数字），全部粘贴到下面框里。系统将自动过滤杂质并进行冷热对赌分析！")

raw_text = st.text_area("📋 在此“无脑粘贴”晒票文本 (建议集中粘贴前区红球数字)：", height=150, placeholder="例如：\n公众号大票1：02 05 16 19 23 28 31 + 04 12\n票2：红球 03 08 11 15 22 31...")

if st.button("⚡ 启动系统反杀逻辑：一键出报告", use_container_width=True):
    if not raw_text.strip():
        st.warning("⚠️ 弹药库为空！请先粘贴晒票数字！")
    else:
        # 1. 超级正则清洗：把所有 01-35 的数字全抠出来，干掉所有汉字、符号、乱码
        matches = re.findall(r'\b(0?[1-9]|[1-2][0-9]|3[0-5])\b', raw_text)
        
        # 统一转成整数
        nums = [int(x) for x in matches]
        
        if not nums:
            st.error("❌ 未检测到有效的号码，请检查粘贴的内容是否包含数字！")
        else:
            # ================= 新增：提取明细核对面板 =================
            with st.expander(f"👀 系统成功提取了 {len(nums)} 个红球数字样本，点击核对抓取明细", expanded=True):
                st.markdown("**以下是系统从您的文本中清洗出的所有纯数字：**")
                # 把提取出来的数字格式化一下，方便观看
                formatted_nums = [str(x).zfill(2) for x in nums]
                # 每 15 个数字换一行显示，更清晰
                display_text = ""
                for i in range(0, len(formatted_nums), 15):
                    display_text += " ".join(formatted_nums[i:i+15]) + "\n"
                st.code(display_text)
            # =========================================================

            counts = Counter(nums)
            sorted_counts = counts.most_common()
            
            # 2. 划定炮灰区 (抓出出现次数最多的前 6 个号码)
            hot_nums = [x[0] for x in sorted_counts[:6]]
            
            # 3. 划定潜伏区 (出现次数少于等于1次的，或者根本没在晒票里出现的绝对冷号)
            max_n = max_f if 'max_f' in locals() else (35 if is_dlt else 33)
            all_possible = set(range(1, max_n + 1))
            appeared_nums = set(nums)
            cold_nums = list(all_possible - appeared_nums) # 一次没出现的
            low_freq_nums = [x[0] for x in sorted_counts if x[1] == 1] # 只出现1次的
            potential_nums = sorted(list(set(cold_nums + low_freq_nums)))
            
            # 4. 执行左右偏移法 (+/- 1 或 2 身位)
            offset_recommend = set()
            for h in hot_nums:
                for offset in [-2, -1, 1, 2]:
                    target = h + offset
                    # 如果偏移后的号码在合法区间，且不是大热炮灰号，就加入推荐阵地
                    if 1 <= target <= max_n and target not in hot_nums:
                        offset_recommend.add(target)
            offset_recommend = sorted(list(offset_recommend))
            
            # ================= 输出华丽的分析报告 =================
            st.markdown("### 📊 AI 反杀分析实战报告")
            
            rc1, rc2 = st.columns(2)
            with rc1:
                st.markdown("<div class='filter-box' style='border-color:#FF4B2B;'>", unsafe_allow_html=True)
                st.markdown("#### ☠️ 绝对炮灰榜 (诱饵号)")
                st.markdown("这些是被大众资金疯狂推崇的超级大热号，**建议直接作为死号拉黑，绝不碰！**")
                hot_str = " ".join([f"<span class='ball ball-red' style='display:inline-flex;margin:2px;'>{str(x).zfill(2)}</span>" for x in hot_nums])
                st.markdown(hot_str, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with rc2:
                st.markdown("<div class='filter-box' style='border-color:#00E676;'>", unsafe_allow_html=True)
                st.markdown("#### 💎 黄金潜伏区 (盲区号)")
                st.markdown("大众晒票完美避开的冷区！这些几乎没人买，**极易爆出大冷门，建议从中挑胆！**")
                # 只展示前15个潜伏号防止太长
                pot_str = " ".join([f"<span class='ball ball-blue' style='display:inline-flex;margin:2px;'>{str(x).zfill(2)}</span>" for x in potential_nums[:15]])
                st.markdown(pot_str + ("..." if len(potential_nums)>15 else ""), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            st.markdown("---")
            st.markdown("#### 🎯 左右偏移突击阵地")
            st.info("💡 **战术逻辑**：系统已自动规避上方的【炮灰号】，并在其左右 1~2 个身位进行火力覆盖。直接从以下红球阵地挑号组单！")
            
            offset_str = " ".join([f"<span class='ball ball-yellow' style='display:inline-flex;margin:4px;'>{str(x).zfill(2)}</span>" for x in offset_recommend])
            st.markdown(f"<div style='background:#2b2b2b; padding:15px; border-radius:10px; text-align:center;'>{offset_str}</div>", unsafe_allow_html=True)
            
            st.balloons() # 跑完报告放个特效庆祝一下
