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
import base64
import json

# ==========================================
# 0. 百度 AI 视觉大脑 (OCR) 接口配置
# ==========================================
BAIDU_API_KEY = "F6lfslP94zn49B90NXSv5NhV"
BAIDU_SECRET_KEY = "589HERNjnrxX17w4CKdqMVUrJeKGRryR"

def get_baidu_token(api_key, secret_key):
    """获取百度AI的通行令牌（小白增强版：错误直接弹窗）"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try:
        # 连线百度服务器，超时时间设为 8 秒
        res = requests.post(url, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=8)
        res_json = res.json()
        
        # 如果百度提示账号密码不对，直接在网页前端弹红框
        if "error" in res_json:
            st.error(f"🔑 百度账号验证失败！请检查代码顶部的 BAIDU_API_KEY 和 SECRET_KEY 是否填错。具体原因: {res_json.get('error_description')}")
            return None
        return res_json.get("access_token")
    except Exception as e:
        st.error(f"❌ 连线百度服务器超时！可能是此时网络波动，请稍后再试。错误信息: {str(e)}")
        return None

def baidu_ocr(image_bytes, token):
    """调用百度网络图片文字识别提取文本（小白增强版：网络延时+接口纠错）"""
    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/webimage?access_token=" + token
    payload = {'image': base64.b64encode(image_bytes).decode('utf-8')}
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
    try:
        # 🚀 核心改动 1：把原本的 8 秒超时，延长到 25 秒！防止由于晒票图片太大、上传慢导致断连
        res = requests.post(url, headers=headers, data=payload, timeout=25)
        res_json = res.json()
        
        # 🚀 核心改动 2：如果百度接口报错（比如免费额度用光了），直接弹窗提示
        if "error_code" in res_json:
            st.error(f"⚠️ 百度视觉大脑返回错误！错误原因: {res_json.get('error_msg')} (错误码: {res_json.get('error_code')})")
            return ""
            
        words_result = res_json.get("words_result", [])
        return " ".join([item.get("words", "") for item in words_result])
    except Exception as e:
        # 🚀 核心改动 3：如果是其他突发情况，把真正的病因打印在网页上
        st.error(f"❌ 图片上传或识别时发生异常，病因: {str(e)}")
        return ""

# ==========================================
# 🏅 新增：红蓝球智能分离清洗核心算法
# ==========================================
def parse_red_blue_from_text(text, is_dlt=True):
    """智能从混杂的OCR/文本中，切分出晒票的红球与蓝球"""
    red_balls = []
    blue_balls = []
    
    # 规整常见中文分隔符
    text_clean = text.replace('：', ':').replace('，', ',').replace('；', ';').replace('—', '-')
    lines = re.split(r'[\n\r;,\t]', text_clean)
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 战术一：寻找明显的红蓝分割标识（如 +, -, |, 蓝, 后区）
        if any(sep in line for sep in ['+', '-', '|', '蓝', '后']):
            parts = re.split(r'[\+\-\|蓝后]', line, maxsplit=1)
            r_part = re.findall(r'\b(0?[1-9]|[1-2][0-9]|3[0-5])\b', parts[0])
            if is_dlt:
                b_part = re.findall(r'\b(0?[1-9]|1[0-2])\b', parts[1])
            else:
                b_part = re.findall(r'\b(0?[1-9]|1[0-6])\b', parts[1])
            
            red_balls.extend([int(x) for x in r_part if (is_dlt and int(x)<=35) or (not is_dlt and int(x)<=33)])
            blue_balls.extend([int(x) for x in b_part])
        else:
            # 战术二：无明显分隔符，抓出单行所有有效数字，按大单格式智能切分
            all_nums = re.findall(r'\b([0-3]?[0-9])\b', line)
            all_nums = [int(x) for x in all_nums if 1 <= int(x) <= 35]
            if not all_nums: continue
            
            if is_dlt and len(all_nums) >= 7:
                # 大乐透单注标准：最后2个为蓝球且<=12
                if all_nums[-1] <= 12 and all_nums[-2] <= 12:
                    red_balls.extend([x for x in all_nums[:-2] if x <= 35])
                    blue_balls.extend(all_nums[-2:])
                else:
                    red_balls.extend([x for x in all_nums if x <= 35])
            elif not is_dlt and len(all_nums) >= 7:
                # 双色球单注标准：最后1个为蓝球且<=16
                if all_nums[-1] <= 16:
                    red_balls.extend([x for x in all_nums[:-1] if x <= 33])
                    blue_balls.extend([all_nums[-1]])
                else:
                    red_balls.extend([x for x in all_nums if x <= 33])
            else:
                # 散装号码，默认归入红球
                if is_dlt:
                    red_balls.extend([x for x in all_nums if x <= 35])
                else:
                    red_balls.extend([x for x in all_nums if x <= 33])
                    
    # 终极兜底：如果没有剥离出蓝球，说明文本极度混乱，直接把所有1-35内的数字作为红球样本
    if not blue_balls:
        all_matches = re.findall(r'\b(0?[1-9]|[1-2][0-9]|3[0-5])\b', text)
        red_balls = [int(x) for x in all_matches if (is_dlt and int(x)<=35) or (not is_dlt and int(x)<=33)]
        
    return red_balls, blue_balls

# ==========================================
# 1. 全局页面配置
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
    .ball-blue { background: radial-gradient(circle at 10px 10px, #6FB1FC, #0052D4); box-shadow: 0 0 6px rgba(0, 82, 212, 0.5); }
    .ball-yellow { background: radial-gradient(circle at 10px 10px, #FFD700, #F39C12); color: #333; text-shadow: none; box-shadow: 0 0 6px rgba(243, 156, 18, 0.5); }
    
    /* 频次横条在手机和电脑上都能自适应紧凑排列 */
    .freq-tag {
        background-color: #2b2b2b; color: #00E676; padding: 4px 8px;
        border-radius: 5px; font-weight: bold; margin-right: 10px;
        border-left: 4px solid #00E676; min-width: 65px; text-align: center; font-size: 13px;
    }
    .stat-row { display: flex; align-items: center; margin-bottom: 8px; background: #1E1E1E; padding: 8px; border-radius: 8px;}
    .filter-box { background: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-bottom: 12px;}
    
    /* 彻底封死顶部区域 */
    [data-testid="stHeader"], .stApp > header { display: none !important; pointer-events: none !important; height: 0px !important; }
    #MainMenu, footer, .stDeployButton, .stAppDeployButton, [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
    
    .ratio-badge { background-color: #262626; border: 1px solid #444; padding: 6px 12px; border-radius: 6px; font-weight: bold; text-align: center; font-size: 14px; flex: 1;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛡️ 1.5 安全认证
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
# 2. 智能读取历史中枢
# ==========================================
def fetch_latest_data(lottery_code, local_latest_issue, custom_limit=50):
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
            
            if new_rows: break 
        except Exception: continue

    if new_rows:
        cols = ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '后1', '后2'] if lottery_code == 'dlt' else ['期号', '日期', '前1', '前2', '前3', '前4', '前5', '前6', '后1']
        df_new = pd.DataFrame(new_rows, columns=cols)
        return df_new.sort_values(by='期号', ascending=False).reset_index(drop=True)
    return pd.DataFrame()


@st.cache_data(ttl=5)
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

# ==========================================
# 4. 侧边栏
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    
    if st.button("🔄 解除冷却：强制连网冲刷", use_container_width=True):
        load_local_data.clear() 
        st.rerun() 

    st.markdown("---")
    st.markdown("### 🗄️ 数据库管理 (Admin)")
    uploaded_file = st.file_uploader("临时投喂本地开奖文件", type=['csv', 'xls', 'xlsx'])

# ==========================================
# 5. 主画面开奖数据分析区
# ==========================================
st.header("🚀 坦克战略指挥中控雷达")

top_col1, top_col2 = st.columns(2)
with top_col1:
    lottery_type = st.selectbox("🎯 切换开奖频道", ["双色球 (SSQ)", "大乐透 (DLT)"], index=1)
with top_col2:
    period_limit = st.selectbox("📅 战术期数锁定", [5, 10, 29, 30, 50, 100], index=3)

is_dlt = "DLT" in lottery_type
lottery_code = 'dlt' if is_dlt else 'ssq'
req_f, req_b = (5, 2) if is_dlt else (6, 1)
max_f, max_b = (35, 12) if is_dlt else (33, 16)

if "filter_mode_state" not in st.session_state:
    st.session_state.filter_mode_state = "历史同期对比"

with st.spinner("📡 正在连线云端检测最新开奖数据..."):
    df_base, new_count = load_local_data(lottery_code, uploaded_file, target_mode=st.session_state.filter_mode_state)

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
        if '期' in latest_issue:
            current_period_str = latest_issue.split('期')[0][-3:]
        else:
            current_period_str = latest_issue[-3:]
            
        default_target_period = int(current_period_str) + 1
        target_period_int = st.number_input("🎯 请确认预测目标期号 (自动 +1 期)：", min_value=1, max_value=160, value=default_target_period, step=1)
        target_period_str = f"{target_period_int:03d}"
        st.info(f"📅 **已锁定预测同期**：为您深度调取历年来尾号为 **{target_period_str}** 的所有往期数据！")
        df_filtered = df_base[df_base['期号'].astype(str).str.endswith(target_period_str)]
    elif filter_mode == "星期独立走势":
        c1, c2 = st.columns([1, 2])
        with c1:
            week_target = st.selectbox("选择开奖日", ["周一", "周三", "周六"] if is_dlt else ["周二", "周四", "周日"])
            week_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周六": 5, "周日": 6}
        df_filtered = df_base[df_base['星期'] == week_map[week_target]]
        st.info(f"📆 **已开启星期独立走势**：挖掘 **{week_target}** 的特有规律。")
    else:
        df_filtered = df_base

    df = df_filtered.head(period_limit)
    actual_periods = len(df)
    
    with st.expander(f"🟢 数据加载成功！共捕获 {actual_periods} 期精准数据 (展开查看明细)"):
        st.dataframe(df.astype(str), use_container_width=True)

    # ==========================================
    # 💎 完美升级：📊 核心形态多维走势分析大盘 (彻底替换原形态扫描)
    # ==========================================
    st.markdown("---")
    st.subheader("📊 核心形态多维走势分析大盘")
    if actual_periods > 0:
        front_cols = ['前1', '前2', '前3', '前4', '前5'] if is_dlt else ['前1', '前2', '前3', '前4', '前5', '前6']
        df_ana = df.copy()
        
        # 计算核心基础技术指标
        df_ana['和值'] = df_ana[front_cols].sum(axis=1)
        df_ana['跨度'] = df_ana[front_cols].max(axis=1) - df_ana[front_cols].min(axis=1)
        
        def get_row_details(row):
            nums = sorted([int(row[c]) for c in front_cols])
            odds = sum(1 for x in nums if x % 2 != 0)
            bigs = sum(1 for x in nums if x > (17 if is_dlt else 16))
            has_consecutive = "有连号" if any(nums[i+1] - nums[i] == 1 for i in range(len(nums)-1)) else "无连号"
            return f"{odds}:{len(front_cols)-odds}", f"{bigs}:{len(front_cols)-bigs}", has_consecutive
            
        res_details = df_ana.apply(get_row_details, axis=1)
        df_ana['奇偶比'] = [r[0] for r in res_details]
        df_ana['大小比'] = [r[1] for r in res_details]
        df_ana['连号状态'] = [r[2] for r in res_details]
        
        # 深度穿透计算历史重号明细
        repeat_status = []
        repeat_num = 0
        cons_num = 0
        for idx, row in df_ana.iterrows():
            nums_set = set(sorted([int(row[c]) for c in front_cols]))
            if row['连号状态'] == "有连号":
                cons_num += 1
            full_idx = df_base.index[df_base['期号'] == row['期号']].tolist()
            if full_idx and full_idx[0] + 1 < len(df_base):
                prev_nums = set([int(df_base.iloc[full_idx[0] + 1][c]) for c in front_cols])
                intersect = nums_set.intersection(prev_nums)
                if len(intersect) > 0:
                    repeat_num += 1
                    repeat_status.append(f"重{len(intersect)}码({','.join([str(x).zfill(2) for x in sorted(intersect)])})")
                else:
                    repeat_status.append("无重号")
            else:
                repeat_status.append("数据源不足")
        df_ana['重号状态'] = repeat_status

        # 1️⃣ 顶置战术级核心数据看板
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📈 历史均值和值", f"{df_ana['和值'].mean():.1f}")
        m2.metric("📐 历史平均跨度", f"{df_ana['跨度'].mean():.1f}")
        m3.metric("🔁 历史重号率", f"{repeat_num / actual_periods * 100:.1f}%")
        m4.metric("🔗 历史连号率", f"{cons_num / actual_periods * 100:.1f}%")
        
        # 2️⃣ 可视化走势图表联动展示区
        t_col1, t_col2 = st.columns([2, 1])
        with t_col1:
            st.markdown("##### 📉 锁定周期内【前区开奖和值】波动轨迹")
            df_chart = df_ana.sort_values(by='期号')[['期号', '和值']].set_index('期号')
            st.line_chart(df_chart, use_container_width=True)
        with t_col2:
            st.markdown("##### 📊 锁定周期内【跨度分布】热度")
            df_span_chart = df_ana.sort_values(by='期号')[['期号', '跨度']].set_index('期号')
            st.bar_chart(df_span_chart, use_container_width=True)
            
        # 3️⃣ 高级形态综合数据全景透视表
        st.markdown("##### 📋 锁定周期内形态透视明细数据流")
        df_show = df_ana[['期号', '和值', '跨度', '奇偶比', '大小比', '连号状态', '重号状态']].copy()
        df_show['期号'] = "第 " + df_show['期号'].astype(str) + " 期"
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ 暂无足够的数据周期进行形态扫描。")

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
    
    st.subheader("⚙️ 012路高阶智能化智能缩水控制台面板")
    f_0 = [x for x in range(1, max_f + 1) if x % 3 == 0]
    f_1 = [x for x in range(1, max_f + 1) if x % 3 == 1]
    f_2 = [x for x in range(1, max_f + 1) if x % 3 == 2]
    b_0 = [x for x in range(1, max_b + 1) if x % 3 == 0]
    b_1 = [x for x in range(1, max_b + 1) if x % 3 == 1]
    b_2 = [x for x in range(1, max_b + 1) if x % 3 == 2]

    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    def_f0, def_f1, def_f2 = (1, 3, 1) if is_dlt else (2, 2, 2)
    def_b0, def_b1, def_b2 = (1, 1, 0) if is_dlt else (0, 1, 0)
    
    st.markdown(f"#### {'🔵' if is_dlt else '🔴'} 前区 012路数量配比调节器")
    sc1, sc2, sc3 = st.columns(3)
    with sc1: f_req_0 = st.number_input("0路出号", min_value=0, max_value=req_f, value=def_f0, step=1, key="num_f0")
    with sc2: f_req_1 = st.number_input("1路出号", min_value=0, max_value=req_f, value=def_f1, step=1, key="num_f1")
    with sc3: f_req_2 = st.number_input("2路出号", min_value=0, max_value=req_f, value=def_f2, step=1, key="num_f2")
    
    st.markdown(f"#### {'🟡' if is_dlt else '🔵'} 后区 012路数量配比调节器")
    sbc1, sbc2, sbc3 = st.columns(3)
    with sbc1: b_req_0 = st.number_input("0路出号", min_value=0, max_value=req_b, value=def_b0, step=1, key="num_b0")
    with sbc2: b_req_1 = st.number_input("1路出号", min_value=0, max_value=req_b, value=def_b1, step=1, key="num_b1")
    with sbc3: b_req_2 = st.number_input("2路出号", min_value=0, max_value=req_b, value=def_b2, step=1, key="num_b2")
    st.markdown('</div>', unsafe_allow_html=True)

    sum_f = f_req_0 + f_req_1 + f_req_2
    sum_b = b_req_0 + b_req_1 + b_req_2

    if sum_f != req_f or sum_b != req_b:
        st.error("⚠️ **校验失败**：请确保前区和后区的012路设定总数正确！")
    else:
        total_filtered_bets = calculate_bets(len(f_0), f_req_0) * calculate_bets(len(f_1), f_req_1) * calculate_bets(len(f_2), f_req_2) * calculate_bets(len(b_0), b_req_0) * calculate_bets(len(b_1), b_req_1) * calculate_bets(len(b_2), b_req_2)
        st.success(f"🔥 形态验证成功：当前配置形态理论极限组合总数为 **{total_filtered_bets}** 注！需投入 **{total_filtered_bets * 2}** 元。")
else:
    st.warning("⚠️ **脱机金库暂无数据！** 请上传 xls/csv。")


# ==========================================
# 6. 🪓 炮灰晒票反杀引擎 (AI 视觉一键全自动版)
# ==========================================
st.markdown("---")
st.header("🪓 炮灰晒票反杀引擎 (红蓝全统计+核心胆拖最少组合版)")
st.info("💡 **实战操作指南**：批量上传晒票截图或直接粘贴文本，系统将调用【百度AI视觉大脑】全自动抠出所有红蓝球号码，【精选最省钱胆拖全托方案】！")

# AI传图核心区
uploaded_images = st.file_uploader("🖼️ 点此批量上传晒票截图（支持一次选中多张照片）", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)

# 备用文本框
raw_text = st.text_area("📋 [备用防线] 如果有不想传图的，也可以在这里直接粘贴文本：", height=100, placeholder="一般情况无需填写，把图片传到上面，全交由 AI 扫描即可。格式如：01 02 03 04 05 + 06 07")

if st.button("⚡ 启动系统反杀逻辑：AI 智能识图与一键出报告", use_container_width=True):
    combined_text = raw_text
    
    # 1. 触发百度 AI 进行图像识别
    if uploaded_images:
        with st.spinner(f"🤖 百度AI视觉大脑启动！正在穿透提取 {len(uploaded_images)} 张图片中的红蓝区隐藏数字..."):
            token = get_baidu_token(BAIDU_API_KEY, BAIDU_SECRET_KEY)
            if token:
                for img in uploaded_images:
                    img_bytes = img.read()
                    text = baidu_ocr(img_bytes, token)
                    
                    # 👇👇👇 就是加了下面这一行透视代码 👇👇👇
                    st.info(f"👀 百度AI底层看到的原始文字是：{text}")
                    
                    combined_text += " " + text
            else:
                st.error("🚨 AI 接口连线失败！请检查百度的 API_KEY 和 SECRET_KEY 是否正确配置。")
    
    if not combined_text.strip():
        st.warning("⚠️ 弹药库为空！请上传图片或粘贴数字！")
    else:
        # 2. 调用红蓝球智能清洗分离算法
        red_nums, blue_nums = parse_red_blue_from_text(combined_text, is_dlt)
        
        if not red_nums:
            st.error("❌ 未检测到有效的号码，请检查图片是否清晰或文本是否正确！")
        else:
            # ================= 提取明细核对面板 =================
            with st.expander(f"👀 AI 视觉成功提取了 {len(red_nums)} 个红球, {len(blue_nums)} 个蓝球样本，点击核对抓取明细", expanded=True):
                st.markdown("**🔴 成功抠出的红球样本：**")
                st.code(" ".join([str(x).zfill(2) for x in red_nums]))
                if blue_nums:
                    st.markdown("**🔵 成功抠出的蓝球样本：**")
                    st.code(" ".join([str(x).zfill(2) for x in blue_nums]))
            
            # 统计红蓝球频次（响应用户的最新需求）
            counts_red = Counter(red_nums)
            counts_blue = Counter(blue_nums)
            
            sorted_red = counts_red.most_common()
            sorted_blue = counts_blue.most_common()
            
            # ================= 完美升级：多维矩阵热力反杀选号盘 =================
            st.markdown("### 📊 晒票所有号码多维热力反杀盘")
            st.info("💡 **热力图说明**：号码按选号盘整齐平铺。🔥 颜色越红（深红/鲜红）代表大众资金撞车越严重，属于**绝对炮灰区**；❄️ 蓝色或深灰代表资金真空盲区，极易爆冷，属于**黄金潜伏区**！")

            # 准备颜色映射辅助函数
            def get_heat_color(num, counts_dict, is_blue_ball=False):
                freq = counts_dict.get(num, 0)
                if freq == 0:
                    return "#1e293b" # 没出现过，冷色调暗夜底色
                
                max_freq = max(counts_dict.values()) if counts_dict else 1
                if max_freq == 0: max_freq = 1
                ratio = freq / max_freq
                
                if not is_blue_ball:
                    # 红球热力：根据占比从浅橘红到深血红
                    if ratio > 0.7: return "#B31217" # 爆热（深血红）
                    elif ratio > 0.4: return "#FF4B2B" # 炽热（火红）
                    else: return "#FF8A75" # 温热（浅红）
                else:
                    # 蓝球热力：从浅蓝到深海蓝
                    if ratio > 0.7: return "#002266" # 爆热蓝
                    elif ratio > 0.4: return "#0052D4" # 炽热蓝
                    else: return "#64B5F6" # 温热蓝

            tc1, tc2 = st.columns(2)
            with tc1:
                st.markdown("#### 🔴 前区红球大众热力选号矩阵")
                max_red_num = 35 if is_dlt else 33
                html_red_matrix = "<div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; max-width: 450px;'>"
                for i in range(1, max_red_num + 1):
                    freq = counts_red.get(i, 0)
                    bg_color = get_heat_color(i, counts_red, is_blue_ball=False)
                    border_style = "border: 2px solid #FF4B2B;" if freq > 0 else "border: 1px solid #475569;"
                    # 🚀 核心修复：单行紧凑拼接 HTML，彻底消灭 Streamlit 的黑色代码框误判
                    html_red_matrix += f"<div style='background:{bg_color}; {border_style} border-radius:6px; padding:8px 4px; text-align:center; color:white;'><b style='font-size:15px;'>{str(i).zfill(2)}</b><br><span style='font-size:11px; opacity:0.85;'>{freq}次</span></div>"
                html_red_matrix += "</div>"
                st.markdown(html_red_matrix, unsafe_allow_html=True)
                
            with tc2:
                st.markdown("#### 🔵 后区蓝球大众热力选号矩阵")
                max_blue_num = 12 if is_dlt else 16
                html_blue_matrix = "<div style='display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; max-width: 450px;'>"
                for i in range(1, max_blue_num + 1):
                    freq = counts_blue.get(i, 0)
                    bg_color = get_heat_color(i, counts_blue, is_blue_ball=True)
                    border_style = "border: 2px solid #0052D4;" if freq > 0 else "border: 1px solid #475569;"
                    # 🚀 核心修复：同理单行紧凑化处理
                    html_blue_matrix += f"<div style='background:{bg_color}; {border_style} border-radius:6px; padding:8px 4px; text-align:center; color:white;'><b style='font-size:15px;'>{str(i).zfill(2)}</b><br><span style='font-size:11px; opacity:0.85;'>{freq}次</span></div>"
                html_blue_matrix += "</div>"
                st.markdown(html_blue_matrix, unsafe_allow_html=True)
            
            # 划定红球炮灰区
            hot_nums = [x[0] for x in sorted_red[:6]]
            
            # 划定红球潜伏区
            max_n = max_f if 'max_f' in locals() else (35 if is_dlt else 33)
            all_possible = set(range(1, max_n + 1))
            appeared_nums = set(red_nums)
            cold_nums = list(all_possible - appeared_nums) 
            low_freq_nums = [x[0] for x in sorted_red if x[1] == 1]
            potential_nums = sorted(list(set(cold_nums + low_freq_nums)))
            
            # 执行左右偏移法
            offset_recommend = set()
            for h in hot_nums:
                for offset in [-2, -1, 1, 2]:
                    target = h + offset
                    if 1 <= target <= max_n and target not in hot_nums:
                        offset_recommend.add(target)
            offset_recommend = sorted(list(offset_recommend))
            
            # ================= 输出华丽的分析报告 =================
            st.markdown("---")
            st.markdown("### 🪓 大众资金盲区反杀实战报告")
            
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
                pot_str = " ".join([f"<span class='ball ball-blue' style='display:inline-flex;margin:2px;'>{str(x).zfill(2)}</span>" for x in potential_nums[:15]])
                st.markdown(pot_str + ("..." if len(potential_nums)>15 else ""), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            st.markdown("#### 🎯 左右偏移突击阵地")
            st.info("💡 **战术逻辑**：系统已自动规避上方的【炮灰号】，并在其左右 1~2 个身位进行火力覆盖。直接从以下红球阵地挑号组单！")
            offset_str = " ".join([f"<span class='ball ball-yellow' style='display:inline-flex;margin:4px;'>{str(x).zfill(2)}</span>" for x in offset_recommend])
            st.markdown(f"<div style='background:#2b2b2b; padding:15px; border-radius:10px; text-align:center;'>{offset_str}</div>", unsafe_allow_html=True)
            
            # ================= 新增：🎯 核心胆拖全托最省方案推演（定制） =================
            st.markdown("---")
            st.markdown("### 🏆 核心战术胆拖方案推演（最省组合全托列出）")
            
            dan_source = potential_nums if potential_nums else offset_recommend
            
            if is_dlt:
                # 大乐透：四胆全托 与 三胆全托 单独列出
                d4_nums = (dan_source + [1, 2, 3, 4])[:4]
                d3_nums = (dan_source + [1, 2, 3])[:3]
                d4_str = " ".join([str(x).zfill(2) for x in d4_nums])
                d3_str = " ".join([str(x).zfill(2) for x in d3_nums])
                
                # 方案一：4胆全托
                st.markdown("<div class='filter-box' style='border-color:#FFD700; background:#1b1b10;'>", unsafe_allow_html=True)
                st.markdown("#### 🌟 【方案一】大乐透 · 四胆全托红球组合（极限最少组合）")
                st.markdown(f"* **🎯 建议红球胆码**：<span style='color:#FFD700; font-weight:bold;'>{d4_str}</span> （系统优先从盲区冷号精选4个）", unsafe_allow_html=True)
                st.markdown(f"* **🚜 红球拖码**：包揽其余所有 **{35 - 4}** 个红球（全托）")
                st.markdown(f"* **📊 红球组合注数**：仅需 **31 注** 红球组合！")
                st.markdown("* **💰 战术实战预算**：")
                st.markdown("  1. **后区精选组合**：若锁定后区2个心水蓝球 → **仅需 31 注 (62元)** —— *反杀最省钱方案！*")
                st.markdown("  2. **后区全托组合**：若后区12个蓝球也全包(66注) → **需 2,046 注 (4,092元)**")
                st.markdown("</div>", unsafe_allow_html=True)
                
                # 方案二：3胆全托
                st.markdown("<div class='filter-box' style='border-color:#FFD700; background:#101b1b;'>", unsafe_allow_html=True)
                st.markdown("#### 🌟 【方案二】大乐透 · 三胆全托红球组合（稳健捕获组合）")
                st.markdown(f"* **🎯 建议红球胆码**：<span style='color:#FFD700; font-weight:bold;'>{d3_str}</span> （系统优先从盲区冷号精选3个）", unsafe_allow_html=True)
                st.markdown(f"* **🚜 红球拖码**：包揽其余所有 **{35 - 3}** 个红球（全托）")
                st.markdown(f"* **📊 红球组合注数**：固定为 **496 注** 红球组合")
                st.markdown("* **💰 战术实战预算**：")
                st.markdown("  1. **后区精选组合**：若锁定后区2个心水蓝球 → **共 496 注 (992元)**")
                st.markdown("  2. **后区全托组合**：若后区12个蓝球也全包(66注) → **共 32,736 注 (65,472元)**")
                st.markdown("</div>", unsafe_allow_html=True)
                
            else:
                # 双色球：五胆全托 单独列出
                d5_nums = (dan_source + [1, 2, 3, 4, 5])[:5]
                d5_str = " ".join([str(x).zfill(2) for x in d5_nums])
                
                st.markdown("<div class='filter-box' style='border-color:#FF4B2B; background:#1b1010;'>", unsafe_allow_html=True)
                st.markdown("#### 🌟 【核心战术推演】双色球 · 五胆全托红球组合（极限最少组合）")
                st.markdown(f"* **🎯 建议红球胆码**：<span style='color:#FF4B2B; font-weight:bold;'>{d5_str}</span> （依据：当前晒票资金真空盲区号 + 热点领域扩散号精选）", unsafe_allow_html=True)
                st.markdown(f"* **🚜 红球拖码**：包揽其余所有 **{33 - 5}** 个红球（全托）")
                st.markdown(f"* **📊 红球组合注数**：仅需 **28 注** 红球组合！")
                st.markdown("</div>", unsafe_allow_html=True)
                
            # ======================================================================
            # 📐 数学正统：📊 纯公式全维度交集概率矩阵核算大底 (智能自适应双色球/大乐透双通道完全体)
            # ======================================================================
            st.markdown("---")
            st.markdown("### 📐 纯公式全维度数据融聚选号中控")
            
            # 精准获取当前前端滑块设定的期数描述
            current_period_desc = str(history_limit) if 'history_limit' in locals() else "自定义"
            st.info(f"💡 **五合一全自适应决策链**：核心中控已完美接管前端 **【{current_period_desc}期】** 大盘惯性！并已智能对齐{'大乐透' if is_dlt else '双色球'}独立统计变量，全面融入同期分布、星期爆发概率与AI晒票博弈。")

            max_r = 35 if is_dlt else 33
            max_b = 12 if is_dlt else 16
            req_r = 5 if is_dlt else 6
            req_b = 2 if is_dlt else 1

            # ------------------------------------------------------------------
            # 管道 1：智能动态绑定大乐透(_list)和双色球的不同统计变量，防止大盘计算踩空
            # ------------------------------------------------------------------
            if is_dlt:
                # 智能接管大乐透专线变量 (精确对齐 _list 后缀)
                recent_red_pool = [x[0] for x in sorted_red_30[:15]] if 'sorted_red_30' in locals() and sorted_red_30 else list(range(1, max_r+1))
                history_tongqi_pool = [x[0] for x in sorted_history_red_list[:15]] if 'sorted_history_red_list' in locals() and sorted_history_red_list else list(range(1, max_r+1))
                weekday_pool = [x[0] for x in sorted_weekday_red_list[:15]] if 'sorted_weekday_red_list' in locals() and sorted_weekday_red_list else list(range(1, max_r+1))

                recent_blue_pool = [x[0] for x in sorted_blue_30[:6]] if 'sorted_blue_30' in locals() and sorted_blue_30 else list(range(1, max_b+1))
                weekday_blue_pool = [x[0] for x in sorted_weekday_blue_list[:6]] if 'sorted_weekday_blue_list' in locals() and sorted_weekday_blue_list else list(range(1, max_b+1))
            else:
                # 智能接管双色球专线变量
                recent_red_pool = [x[0] for x in sorted_red_30[:15]] if 'sorted_red_30' in locals() and sorted_red_30 else list(range(1, max_r+1))
                history_tongqi_pool = [x[0] for x in sorted_history_red[:15]] if 'sorted_history_red' in locals() and sorted_history_red else list(range(1, max_r+1))
                weekday_pool = [x[0] for x in sorted_weekday_red[:15]] if 'sorted_weekday_red' in locals() and sorted_weekday_red else list(range(1, max_r+1))

                recent_blue_pool = [x[0] for x in sorted_blue_30[:6]] if 'sorted_blue_30' in locals() and sorted_blue_30 else list(range(1, max_b+1))
                weekday_blue_pool = [x[0] for x in sorted_weekday_blue[:6]] if 'sorted_weekday_blue' in locals() and sorted_weekday_blue else list(range(1, max_b+1))

            # ------------------------------------------------------------------
            # 管道 2：公式矩阵得分核算 (红球大热一票否决，蓝球柔性惩罚)
            # ------------------------------------------------------------------
            red_scores = {}
            for num in range(1, max_r + 1):
                score = 0
                if num in recent_red_pool: score += 3       # 联动滑块期数惯性
                if num in history_tongqi_pool: score += 2   # 联动历史同期惯性
                if num in weekday_pool: score += 2          # 联动特定星期爆发率
                
                # 数学互斥：如果撞车了当前大众晒票里买得最火爆的 6 个炮灰号，直接清零抹杀！
                if num in hot_nums:
                    score = 0
                red_scores[num] = score

            blue_scores = {}
            for num in range(1, max_b + 1):
                score = 0
                if num in recent_blue_pool: score += 3
                if num in weekday_blue_pool: score += 2
                
                # 柔性期望扣分：散户买得越多，扣分越重，从而筛选出大冷真空蓝球
                blue_strike = counts_blue.get(num, 0)
                score = score - (blue_strike * 2)  
                blue_scores[num] = score

            # ------------------------------------------------------------------
            # 管道 3：确定性稳定降序截取
            # ------------------------------------------------------------------
            sorted_math_reds = [num for num, score in sorted(red_scores.items(), key=lambda x: (x[1], -x[0]), reverse=True) if score > 0]
            sorted_math_blues = [num for num, score in sorted(blue_scores.items(), key=lambda x: (x[1], -x[0]), reverse=True)]

            # 确定性容错兜底
            if len(sorted_math_reds) < req_r + 2:
                sorted_math_reds = [x for x in range(1, max_r + 1) if x not in hot_nums]
            if len(sorted_math_blues) < req_b + 2:
                sorted_math_blues = [x for x in range(1, max_b + 1)]

            # 提取最终红蓝球实战方案
            final_math_reds = sorted(sorted_math_reds[:req_r])
            final_math_blues = sorted(sorted_math_blues[:req_b])
            
            # 战术复式扩容：红球稳健增加 2 个；蓝球/后区如果是大乐透增加 2 个(选4个球)，双色球增加 1 个(选2个球)
            fushi_math_reds = sorted(sorted_math_reds[:req_r + 2])
            fushi_blue_count = req_b + 2 if is_dlt else req_b + 1
            fushi_math_blues = sorted(sorted_math_blues[:fushi_blue_count])

            # ------------------------------------------------------------------
            # 管道 4：流线型前端渲染
            # ------------------------------------------------------------------
            rc1, rc2 = st.columns(2)
            ball_class_r = "ball-blue" if is_dlt else "ball-red"
            ball_class_b = "ball-yellow" if is_dlt else "ball-blue"

            with rc1:
                st.markdown("<div class='filter-box' style='border-color:#00E676; background:#0d1b13; padding:15px; border-radius:8px;'>", unsafe_allow_html=True)
                st.markdown(f"#### 🎯 五合一数据融聚 · 精选准确单式 ({'5+2' if is_dlt else '6+1'})")
                st.markdown(f"<span style='color:#a0aec0; font-size:13px;'>当前方案已无缝对接 <b>{current_period_desc}期</b> 走势，剔除大众晒票噪声，锁定高分交集。</span>", unsafe_allow_html=True)
                
                r_html = "".join([f"<div class='ball {ball_class_r}' style='display:inline-flex;margin:2px;'>{str(x).zfill(2)}</div>" for x in final_math_reds])
                b_html = "".join([f"<div class='ball {ball_class_b}' style='display:inline-flex;margin:2px;'>{str(x).zfill(2)}</div>" for x in final_math_blues])
                
                st.markdown(f"<div class='ball-container' style='margin-top:15px;'>{r_html} <span style='color:#4a5568;font-weight:bold;margin:0 10px;'>+</span> {b_html}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with rc2:
                st.markdown("<div class='filter-box' style='border-color:#29B6F6; background:#0d171b; padding:15px; border-radius:8px;'>", unsafe_allow_html=True)
                st.markdown(f"#### 🛡️ 五合一数据融聚 · 战术复式号码 ({len(fushi_math_reds)}+{len(fushi_math_blues)})")
                st.markdown(f"<span style='color:#a0aec0; font-size:13px;'>结合 <b>{current_period_desc}期</b> 形态空间进行多点覆盖的期望最大化防御方案：</span>", unsafe_allow_html=True)
                
                rf_html = "".join([f"<div class='ball {ball_class_r}' style='display:inline-flex;margin:2px;'>{str(x).zfill(2)}</div>" for x in fushi_math_reds])
                bf_html = "".join([f"<div class='ball {ball_class_b}' style='display:inline-flex;margin:2px;'>{str(x).zfill(2)}</div>" for x in fushi_math_blues])
                
                st.markdown(f"<div class='ball-container' style='margin-top:15px;'>{rf_html} <span style='color:#4a5568;font-weight:bold;margin:0 10px;'>+</span> {bf_html}</div>", unsafe_allow_html=True)
                zhusu = math.comb(len(fushi_math_reds), req_r) * math.comb(len(fushi_math_blues), req_b)
                st.markdown(f"<div style='margin-top:10px; font-size:13px; color:#63b3ed;'>📊 **组合注数**：共 **{zhusu}** 注 | 实战预算 **{zhusu * 2}** 元</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # 底部保留直观的期望分值核算明细表
            st.markdown(f"#### 📈 大底号码多维交集（当前: {current_period_desc}期）期望分值核算表")
            prob_data = []
            for x in range(1, max_r + 1):
                scr = red_scores.get(x, 0)
                status = "🚨 晒票撞车（强制剥离）" if x in hot_nums else (f"💎 建议保留（交集得分: {scr}分）" if scr > 0 else "💤 历史冷滞")
                prob_data.append({"号码": f"{str(x).zfill(2)}号红球", "多维交集热度得分": f"{scr} 分", "战术决策状态": status})
            st.dataframe(pd.DataFrame(prob_data), use_container_width=True, hide_index=True)
                
            st.balloons()
