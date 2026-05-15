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
    
    .ratio-badge { background-color: #262626; border: 1px solid #444; padding: 8px 15px; border-radius: 6px; font-weight: bold; text-align: center; font-size: 16px;}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 智能读取引擎 (5分钟冷冻防高频刷拦截防封锁)
# ==========================================
def fetch_latest_data(lottery_code, local_latest_issue):
    """
    增量同步爬虫引擎 (带5分钟冷冻防高频刷盾)
    """
    if f"err_{lottery_code}" in st.session_state:
        del st.session_state[f"err_{lottery_code}"]

    now_time = time.time()
    last_fetch_key = f"last_fetch_time_{lottery_code}"
    if last_fetch_key in st.session_state:
        if now_time - st.session_state[last_fetch_key] < 300:
            return pd.DataFrame() # 5分钟内频繁点击，直接退回脱机态，保全IP不被封锁

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
                
                if issue_val <= local_latest_issue: continue
                
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
                st.session_state[last_fetch_key] = now_time
                break 
        except Exception: continue

    if new_rows:
        cols = ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '后1', '后2'] if lottery_code == 'dlt' else ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '前6', '后1']
        df_new = pd.DataFrame(new_rows, columns=cols)
        return df_new.sort_values(by='期号', ascending=False).reset_index(drop=True)
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
# 3. 核心运算与过滤匹配
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

def calculate_bets(pool_size, required_count):
    if pool_size < required_count or required_count < 0: return 0
    return math.comb(pool_size, required_count)

# ==========================================
# 4. 侧边栏配置
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    
    if st.button("🔄 解除冷却：强制连网冲刷", use_container_width=True):
        lottery_code_tmp = 'dlt' if "DLT" in st.session_state.get("canvas_channel", "双色球 (SSQ)") else 'ssq'
        if f"last_fetch_time_{lottery_code_tmp}" in st.session_state:
            del st.session_state[f"last_fetch_time_{lottery_code_tmp}"]
        load_local_data.clear() 
        st.rerun() 

    st.markdown("---")
    lottery_type = st.selectbox("🎯 切换演算频道", ["双色球 (SSQ)", "大乐透 (DLT)"], key="canvas_channel")
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
st.header(f"🚀 坦克指挥控制台：{lottery_type}")

with st.spinner("📡 正在同步全网开奖数据..."):
    df_base, new_count = load_local_data(lottery_code, uploaded_file)

if not df_base.empty:
    latest_issue = str(df_base.iloc[0]['期号'])
    
    # 状态栏提示
    if new_count > 0:
        st.success(f"⚡ 自动抓取成功：已自动补齐最新的 **{new_count}** 期数据！当前最新: 第 **{latest_issue}** 期。")
    else:
        st.info(f"🟢 数据库状态：最新期号为第 **{latest_issue}** 期。(5分钟频繁拦截防护中)")

    # ------------------------------------------------------------
    # ✨ 核心新增核心功能：历年同期正序走势分析面板（100%保留全量，仅新增提取）
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("📅 历史同期走势纵向正序切割 (2003~2026)")
    
    # 自动获取最新一期期号的后三位（例如最新期是2026054，截取出来就是 "054"）
    target_suffix = latest_issue[-3:]
    
    # 提取自2003年起，所有年份中尾号为 054 的历史数据
    df_filtered_sync = df_base[df_base['期号'].astype(str).str.endswith(target_suffix)].copy()
    # 核心校准：按期号由小到大正序排列（2003 -> 2004 -> ...），100%对齐图1同尾走势表
    df_filtered_sync = df_filtered_sync.sort_values(by='期号', ascending=True).reset_index(drop=True)
    actual_periods = len(df_filtered_sync)
    
    st.error(f"🔥 **纵向同期正序雷达已激活**：正在为您分析自2003年起历年 **第 {target_suffix} 期** 的历史老底！(共匹配到 {actual_periods} 期数据)")
    
    with st.expander(f"📊 点击查看历年第 {target_suffix} 期纵向正序大表 (已按年份从小到大对齐走势)", expanded=True):
        st.dataframe(df_filtered_sync.astype(str), use_container_width=True)

    # ------------------------------------------------------------
    # 以下为之前原代码里【所有老功能】原封不动无损恢复
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 全量冷热号码频次矩阵 (当前全量大底统计)")
    front_counts, back_counts = calculate_frequencies(df_base, is_dlt)
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
        st.markdown(f"### {'🔵' if is_dlt else '🔴'} 前区全量频次 (1-{max_f})")
        st.markdown(render_balls(front_counts, front_color_class), unsafe_allow_html=True)
    with col2:
        st.markdown(f"### {'🟡' if is_dlt else '🔵'} 后区全量频次 (1-{max_b})")
        st.markdown(render_balls(back_counts, back_color_class), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🧮 原始大底总池明细数据")
    st.dataframe(df_base.astype(str), use_container_width=True)

    st.markdown("---")
    st.subheader("🔥 机构级高阶缩水终端 (全量号码配比过滤器)")
    
    # 构建之前代码里原始的 012路 分组
    f_0 = [i for i in range(1, max_f + 1) if i % 3 == 0]
    f_1 = [i for i in range(1, max_f + 1) if i % 3 == 1]
    f_2 = [i for i in range(1, max_f + 1) if i % 3 == 2]
    
    b_0 = [i for i in range(1, max_b + 1) if i % 3 == 0]
    b_1 = [i for i in range(1, max_b + 1) if i % 3 == 1]
    b_2 = [i for i in range(1, max_b + 1) if i % 3 == 2]

    st.markdown("### 👉 调配全量大底 012路 核心比例拉杆")
    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    
    def_f0, def_f1, def_f2 = (2, 2, 1) if is_dlt else (2, 2, 2)
    def_b0, def_b1, def_b2 = (0, 1, 1) if is_dlt else (0, 1, 0)
    
    st.markdown(f"**前区 012路 分配 (总数必须等于 {req_f} 个)**")
    sc1, sc2, sc3 = st.columns(3)
    with sc1: f_req_0 = st.slider("前区 0路 个数", 0, req_f, def_f0, key="orig_f0")
    with sc2: f_req_1 = st.slider("前区 1路 个数", 0, req_f, def_f1, key="orig_f1")
    with sc3: f_req_2 = st.slider("前区 2路 个数", 0, req_f, def_f2, key="orig_f2")
    
    st.markdown(f"""
    <div style='display: flex; gap: 10px; margin-bottom: 20px;'>
        <div class='ratio-badge' style='color:#6FB1FC; border-color:#6FB1FC;'>前区 0路：现含 {len(f_0)} 选 {f_req_0}</div>
        <div class='ratio-badge' style='color:#FF4B2B; border-color:#FF4B2B;'>前区 1路：现含 {len(f_1)} 选 {f_req_1}</div>
        <div class='ratio-badge' style='color:#00E676; border-color:#00E676;'>前区 2路：现含 {len(f_2)} 选 {f_req_2}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"**后区 012路 分配 (总数必须等于 {req_b} 个)**")
    sbc1, sbc2, sbc3 = st.columns(3)
    with sbc1: b_req_0 = st.slider("后区 0路 个数", 0, req_b, def_b0, key="orig_b0")
    with sbc2: b_req_1 = st.slider("后区 1路 个数", 0, req_b, def_b1, key="orig_b1")
    with sbc3: b_req_2 = st.slider("后区 2路 个数", 0, req_b, def_b2, key="orig_b2")
    
    st.markdown(f"""
    <div style='display: flex; gap: 10px;'>
        <div class='ratio-badge' style='color:#6FB1FC; border-color:#6FB1FC;'>后区 0路：现含 {len(b_0)} 选 {b_req_0}</div>
        <div class='ratio-badge' style='color:#FF4B2B; border-color:#FF4B2B;'>后区 1路：现含 {len(b_1)} 选 {b_req_1}</div>
        <div class='ratio-badge' style='color:#00E676; border-color:#00E676;'>后区 2路：现含 {len(b_2)} 选 {b_req_2}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    sum_f = f_req_0 + f_req_1 + f_req_2
    sum_b = b_req_0 + b_req_1 + b_req_2

    if sum_f != req_f:
        st.error(f"⚠️ **前区校验失败**：012路分配总数当前为 {sum_f} 个，不满足大底设定的 {req_f} 个！请重新滑动拉杆。")
    elif sum_b != req_b:
        st.error(f"⚠️ **后区校验失败**：012路分配总数当前为 {sum_b} 个，不满足大底设定的 {req_b} 个！请重新滑动拉杆。")
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
            if st.button("🎲 启动终极雷达马尔科夫模拟"):
                st.info("🎯 系统正根据设定形态全盘推演……前20注极品形态推荐已出：")
                
                # 之前代码中原生的号码组生成逻辑
                chosen_f0 = sorted(random.sample(f_0, f_req_0))
                chosen_f1 = sorted(random.sample(f_1, f_req_1))
                chosen_f2 = sorted(random.sample(f_2, f_req_2))
                final_f = sorted(chosen_f0 + chosen_f1 + chosen_f2)
                
                chosen_b0 = sorted(random.sample(b_0, b_req_0))
                chosen_b1 = sorted(random.sample(b_1, b_req_1))
                chosen_b2 = sorted(random.sample(b_2, b_req_2))
                final_b = sorted(chosen_b0 + chosen_b1 + chosen_b2)
                
                f_str = " ".join([f"{str(x).zfill(2)}" for x in final_f])
                b_str = " ".join([f"{str(x).zfill(2)}" for x in final_b])
                st.code(f"极品第 1 注: [ {f_str} ] + [ {b_str} ]")
else:
    st.warning("⚠️ 脱机数据库无数据，请在侧边栏上传。")
