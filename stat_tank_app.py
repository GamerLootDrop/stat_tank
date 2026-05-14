import streamlit as st
import pandas as pd
from collections import Counter
import math
import os
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ==========================================
# 0. 全局页面配置 & 视觉净化
# ==========================================
st.set_page_config(page_title="坦克指挥控制台", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    /* 彻底抹除官方图标、黑框、顶部菜单 */
    .stApp { background-color: #0E1117; }
    div[data-testid="stMarkdownContainer"] pre, code { background: transparent !important; border: none !important; color: #00E676 !important; }
    div[data-testid="stNotification"], .stAlert { background-color: rgba(0,230,118,0.05) !important; border: 1px solid #333 !important; color: #90CAF9 !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
    .mini-ball { display: inline-flex; width: 24px; height: 24px; border-radius: 50%; align-items: center; justify-content: center; font-size: 11px; margin: 1px; color: #E0E0E0; border: 1px solid #444; background: #262626; }
    .pool-box { line-height: 1.2; padding: 5px 0; margin-bottom: 5px; }
    div[data-testid="stNumberInput"] label { font-size: 0.8rem; color: #888; }
    .result-card { background: #161b22; padding: 12px; border-radius: 8px; border-left: 4px solid #00E676; margin-top: 5px; }
    [data-testid="stHeader"], .stApp > header { display: none !important; pointer-events: none !important; height: 0px !important; }
    #MainMenu, footer, .stDeployButton, .stAppDeployButton, [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 🛡️ 军用级安全认证 (密码墙)
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center; color: #00E676; margin-top: 100px;'>🚀 坦克战略指挥部</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>此系统为内部绝密版本，未授权人员请立即退出。</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pwd = st.text_input("🔒 请输入安全访问口令：", type="password")
        if st.button("验证身份进入系统", use_container_width=True):
            if pwd == "888888":  # <--- 在这里修改你的专属密码
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ 警告：口令错误，访问被拒绝！")
    st.stop()  # 密码不对，代码死死卡在这里，绝对不加载后面的数据！

# ==========================================
# 2. 🕸️ 智能潜行爬虫 (增量抓取，防封杀)
# ==========================================
def fetch_latest_data(lottery_code, local_latest_issue):
    """
    潜行爬虫：只抓最近30期，对比本地期号，只把最新的补进去。
    采用 500.com 数据源，极其稳定，加入随机 User-Agent 防封。
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = f"https://datachart.500.com/{lottery_code}/history/newinc/history.php?limit=30"
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        tbody = soup.find('tbody', id='tdata')
        if not tbody: return pd.DataFrame()
        
        new_data = []
        for tr in tbody.find_all('tr'):
            if 'class' in tr.attrs: continue  # 跳过不相干的行
            tds = tr.find_all('td')
            if len(tds) < 10: continue
            
            issue = int(tds[0].text.strip())
            # 【核心反爬与增量逻辑】只抓取比本地最新的期号还要新的数据
            if issue <= local_latest_issue: 
                break
                
            date_str = tds[len(tds)-1].text.strip()
            if lottery_code == 'dlt':
                nums = [tds[i].text.strip() for i in range(1, 8)] # 5+2
                new_data.append([issue, date_str] + nums)
            else:
                nums = [tds[i].text.strip() for i in range(1, 8)] # 6+1
                new_data.append([issue, date_str] + nums)
                
        if new_data:
            cols = ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '后1', '后2'] if lottery_code == 'dlt' else ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '前6', '后1']
            df_new = pd.DataFrame(new_data, columns=cols)
            for c in cols[2:]: df_new[c] = pd.to_numeric(df_new[c])
            return df_new
        else:
            return pd.DataFrame() # 没有新数据
    except Exception as e:
        return pd.DataFrame() # 网络错误或防爬虫拦截时静默失败，使用本地数据

# ==========================================
# 3. 智能读取与清洗引擎 (含自动同步)
# ==========================================
@st.cache_data(ttl=300) # 缓存5分钟，防止用户狂点按钮导致封IP
def get_and_sync_data(lottery_code, uploaded_file):
    # 1. 读本地库 (修复：全面支持读取云端仓库的 xls 和 csv)
    df_local = pd.DataFrame()
    
    if uploaded_file:
        source = uploaded_file
    elif os.path.exists(f"{lottery_code}.xls"):
        source = f"{lottery_code}.xls"
    elif os.path.exists(f"{lottery_code}.xlsx"):
        source = f"{lottery_code}.xlsx"
    elif os.path.exists(f"{lottery_code}.csv"):
        source = f"{lottery_code}.csv"
    else:
        source = None

    if source:
        try:
            if str(source).endswith(('xls','xlsx')):
                df_raw = pd.read_excel(source, header=None, dtype=str)
            else:
                df_raw = pd.read_csv(source, encoding_errors='ignore', header=None, dtype=str)
                
            cols_use = [0, 1, 2, 3, 4, 5, 6, 7, 8]
            c_names = ['期号','日期','前1','前2','前3','前4','前5','后1','后2'] if lottery_code == 'dlt' else ['期号','日期','前1','前2','前3','前4','前5','前6','后1']
            
            df_raw = df_raw.iloc[:, cols_use]
            df_raw.columns = c_names
            df_raw['前1'] = pd.to_numeric(df_raw['前1'], errors='coerce')
            df_raw = df_raw.dropna(subset=['前1'])
            df_raw['期号'] = df_raw['期号'].astype(str).str.replace(r'\D', '', regex=True)
            df_raw['期号'] = pd.to_numeric(df_raw['期号'], errors='coerce').fillna(0).astype(int)
            for c in c_names[2:]: df_raw[c] = pd.to_numeric(df_raw[c], errors='coerce').fillna(0).astype(int)
            df_local = df_raw[(df_raw['前1']>0)&(df_raw['前1']<=35)].sort_values(by='期号', ascending=False).reset_index(drop=True)
        except Exception as e:
            pass

    # 2. 爬虫检查最新并合并
    local_latest = int(df_local.iloc[0]['期号']) if not df_local.empty else 0
    df_new = fetch_latest_data(lottery_code, local_latest)
    
    if not df_new.empty:
        # 如果有新数据，拼接到本地数据最上方
        df_final = pd.concat([df_new, df_local], ignore_index=True)
    else:
        df_final = df_local

    if not df_final.empty:
        df_final['日期_解析'] = pd.to_datetime(df_final['日期'], errors='coerce')
        df_final['星期'] = df_final['日期_解析'].dt.dayofweek
        
    return df_final, len(df_new) # 返回总数据和抓取到的新数据条数

def calculate_bets(n, r): return math.comb(n, r) if r <= n and r >= 0 else 0

def scan_advanced_patterns(df_slice, df_full, is_dlt):
    front_cols = ['前1','前2','前3','前4','前5'] if is_dlt else ['前1','前2','前3','前4','前5','前6']
    repeat_count = 0; consecutive_count = 0
    for idx, row in df_slice.iterrows():
        nums = sorted([row[c] for c in front_cols])
        if any(nums[i+1] - nums[i] == 1 for i in range(len(nums)-1)): consecutive_count += 1
        full_idx = df_full.index[df_full['期号'] == row['期号']].tolist()
        if full_idx and full_idx[0] + 1 < len(df_full):
            prev_nums = set([df_full.iloc[full_idx[0] + 1][c] for c in front_cols])
            if len(set(nums).intersection(prev_nums)) > 0: repeat_count += 1
    return repeat_count, consecutive_count

# ==========================================
# 4. 侧边栏 (集成传送门与自动同步配置)
# ==========================================
with st.sidebar:
    st.title("🛰️ 控制中心")
    
    # 【内部传送门】可以通过这里的链接跳转到你系统的其他页面
    st.markdown("🔗 **系统内部导航**")
    st.markdown("[🔙 返回主站系统](/)") # 跳转到根目录
    st.markdown("[📊 数据大屏监控](/dashboard)") # 假设你的其他页面链接
    st.markdown("---")

    lottery_type = st.selectbox("频道切换", ["双色球 (SSQ)", "大乐透 (DLT)"])
    period_limit = st.selectbox("战术期数", [5, 10, 29, 30, 50, 100], index=4)
    uploaded_file = st.file_uploader("强制手动覆盖底库", type=['csv', 'xls', 'xlsx'])

is_dlt = "DLT" in lottery_type
lot_code = 'dlt' if is_dlt else 'ssq'
req_f, max_f = (5, 35) if is_dlt else (6, 33)
req_b, max_b = (2, 12) if is_dlt else (1, 16)

# ==========================================
# 5. 主界面 (云端更新 + 战术雷达)
# ==========================================
# 运行智能读取与爬虫同步
with st.spinner('📡 正在连线云端检测最新开奖数据...'):
    df_base, newly_fetched_count = get_and_sync_data(lot_code, uploaded_file)

if not df_base.empty:
    latest_issue = str(df_base.iloc[0]['期号'])
    
    # 云端更新提示
    if newly_fetched_count > 0:
        st.success(f"⚡ 云端爬虫工作完毕！已秘密抓取并补充 **{newly_fetched_count}** 期最新数据！当前截至第 **{latest_issue}** 期。")
    else:
        st.info(f"✅ 云端核对完毕。暂无新数据产生，本地第 **{latest_issue}** 期已是全网最新。")

    st.markdown("### 📡 开启高级过滤雷达")
    filter_mode = st.radio("选择分析维度", ["默认 (近期连贯走势)", "历史同期对比", "星期独立走势"], horizontal=True)
    
    if filter_mode == "历史同期对比":
        suffix = latest_issue[-3:]
        df_filtered = df_base[df_base['期号'].astype(str).str.endswith(suffix)]
        st.info(f"📅 **已锁定历史同期**：正在分析尾号为 **{suffix}** 的全部往期。")
    elif filter_mode == "星期独立走势":
        c1, c2 = st.columns([1, 2])
        with c1:
            week_target = st.selectbox("开奖日", ["周一", "周三", "周六"] if is_dlt else ["周二", "周四", "周日"])
            week_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周六": 5, "周日": 6}
        df_filtered = df_base[df_base['星期'] == week_map[week_target]]
        st.info(f"📆 **已开启星期专属走势**：正在挖掘 **{week_target}** 的特有规律。")
    else:
        df_filtered = df_base

    df = df_filtered.head(period_limit)
    actual_periods = len(df)
    
    # 智能配比推荐
    f_cols = ['前1','前2','前3','前4','前5'] if is_dlt else ['前1','前2','前3','前4','前5','前6']
    all_f = df[f_cols].values.flatten()
    c0, c1, c2 = sum(1 for x in all_f if x%3==0), sum(1 for x in all_f if x%3==1), sum(1 for x in all_f if x%3==2)
    tot = c0+c1+c2
    rec_f0, rec_f1 = round(req_f*(c0/tot)), round(req_f*(c1/tot)); rec_f2 = req_f - rec_f0 - rec_f1

    st.markdown("---")
    # 重号与连号
    repeat_num, cons_num = scan_advanced_patterns(df, df_base, is_dlt)
    rc1, rc2 = st.columns(2)
    rc1.warning(f"🔁 重号率：在这 {actual_periods} 期中，**{repeat_num}**期开出上期落号({repeat_num/actual_periods*100:.1f}%)")
    rc2.error(f"🔗 连号率：在这 {actual_periods} 期中，**{cons_num}**期开出了连号({cons_num/actual_periods*100:.1f}%)")

    # 012路快捷键
    st.subheader(f"📐 012路 精准缩水 (第{latest_issue}期起算)")
    c_btn1, c_btn2 = st.columns([1, 2])
    with c_btn1:
        if st.button("✨ 智能自适应", use_container_width=True): st.session_state.f0, st.session_state.f1, st.session_state.f2 = rec_f0, rec_f1, rec_f2
    with c_btn2:
        preset = st.selectbox("快速配比选项", ["自定义", "2-2-1", "2-1-2", "1-2-2", "3-1-1"] if is_dlt else ["自定义", "2-2-2", "3-2-1", "1-2-3"])
        if preset != "自定义":
            p = [int(x) for x in preset.split('-')]
            st.session_state.f0, st.session_state.f1, st.session_state.f2 = p[0], p[1], p[2]
    
    # 选号池
    f_0 = [x for x in range(1, max_f + 1) if x % 3 == 0]
    f_1 = [x for x in range(1, max_f + 1) if x % 3 == 1]
    f_2 = [x for x in range(1, max_f + 1) if x % 3 == 2]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**0路**")
        st.markdown(f"<div class='pool-box'>{''.join([f'<span class=mini-ball>{str(x).zfill(2)}</span>' for x in f_0])}</div>", unsafe_allow_html=True)
        in_f0 = st.number_input("0路", 0, req_f, st.session_state.get('f0', rec_f0), key="kf0", label_visibility="collapsed")
    with col_b:
        st.markdown("**1路**")
        st.markdown(f"<div class='pool-box'>{''.join([f'<span class=mini-ball>{str(x).zfill(2)}</span>' for x in f_1])}</div>", unsafe_allow_html=True)
        in_f1 = st.number_input("1路", 0, req_f, st.session_state.get('f1', rec_f1), key="kf1", label_visibility="collapsed")
    with col_c:
        st.markdown("**2路**")
        st.markdown(f"<div class='pool-box'>{''.join([f'<span class=mini-ball>{str(x).zfill(2)}</span>' for x in f_2])}</div>", unsafe_allow_html=True)
        in_f2 = st.number_input("2路", 0, req_f, st.session_state.get('f2', rec_f2), key="kf2", label_visibility="collapsed")

    # 结果
    if (in_f0 + in_f1 + in_f2) == req_f:
        total_bets = calculate_bets(len(f_0), in_f0) * calculate_bets(len(f_1), in_f1) * calculate_bets(len(f_2), in_f2) * calculate_bets(max_b, req_b)
        st.markdown(f"""
        <div class="result-card">
            <div style='color:#888; font-size:12px;'>配比 {in_f0}:{in_f1}:{in_f2} (后区全包)</div>
            <div style='font-size:22px; color:#FFD700; font-weight:bold;'>剩余 {total_bets} 注</div>
            <div style='color:#00E676; font-size:14px;'>投入预估: {total_bets * 2} 元</div>
        </div>
        """, unsafe_allow_html=True)
        if total_bets > 0 and st.button("🎲 提取精选", use_container_width=True):
            for i in range(5):
                pick = sorted(random.sample(f_0, in_f0) + random.sample(f_1, in_f1) + random.sample(f_2, in_f2))
                st.code(f"{i+1}: {' '.join([str(x).zfill(2) for x in pick])}")
    else: st.error(f"总和需={req_f}")
else:
    st.info("💡 请在左侧上传初始化数据底库...")
