import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from collections import Counter
import re
import math
import time
import urllib.parse

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
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 降维打击数据引擎 (官方内部 JSON 接口 + 备用路线)
# ==========================================
@st.cache_data(ttl=86400)
def fetch_base_data(lottery_code):
    limit = 100
    
    # 定义代理跳板矩阵（专门用来对付云端 IP 屏蔽）
    proxy_nodes = [
        "",  # 节点0：尝试云端直连
        "https://api.allorigins.win/raw?url=", # 节点1：AllOrigins
        "https://corsproxy.io/?", # 节点2：Corsproxy
    ]
    
    # ---------------------------------------------------------
    # 💥 战术 A：直接截取官方内部 JSON 数据 (最快、最准、无商业级 WAF)
    # ---------------------------------------------------------
    if lottery_code == 'ssq':
        official_url = f"http://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&issueCount={limit}"
        off_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "http://www.cwl.gov.cn/"}
    else:
        official_url = f"https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize={limit}&isVerify=1&pageNo=1"
        off_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for node in proxy_nodes:
        try:
            req_url = official_url if node == "" else node + urllib.parse.quote(official_url)
            res = requests.get(req_url, headers=off_headers, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                parsed_data = []
                
                if lottery_code == 'ssq':
                    for item in data.get('result', []):
                        reds = item['red'].split(',')
                        parsed_data.append({
                            '期号': item['code'],
                            '前1': int(reds[0]), '前2': int(reds[1]), '前3': int(reds[2]),
                            '前4': int(reds[3]), '前5': int(reds[4]), '前6': int(reds[5]),
                            '后1': int(item['blue'])
                        })
                else:
                    for item in data.get('value', {}).get('list', []):
                        nums = item['lotteryDrawResult'].split()
                        parsed_data.append({
                            '期号': item['lotteryDrawNum'],
                            '前1': int(nums[0]), '前2': int(nums[1]), '前3': int(nums[2]),
                            '前4': int(nums[3]), '前5': int(nums[4]),
                            '后1': int(nums[5]), '后2': int(nums[6])
                        })
                
                if parsed_data:
                    return pd.DataFrame(parsed_data)
        except:
            continue # 如果当前节点被官方屏蔽，立刻切换下一个节点

    # ---------------------------------------------------------
    # 🛡️ 战术 B：极限备用路线 (500.com HTML 强行解析) 
    # 如果福彩/体彩官网宕机，作为最后一道防线
    # ---------------------------------------------------------
    timestamp = int(time.time())
    target_url = f"https://datachart.500.com/{lottery_code}/history/newinc/history.php?limit={limit}&sort=0&_={timestamp}"
    
    for node in proxy_nodes:
        try:
            req_url = target_url if node == "" else node + urllib.parse.quote(target_url)
            res = requests.get(req_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            res.encoding = 'utf-8'
            html = res.text
            
            if '<tbody id="tdata">' in html:
                tbody = re.search(r'<tbody id="tdata">(.*?)</tbody>', html, re.DOTALL).group(1)
                trs = re.findall(r'<tr.*?>(.*?)</tr>', tbody, re.DOTALL)
                parsed_data = []
                for tr in trs:
                    tds = re.findall(r'<td.*?>(.*?)</td>', tr, re.DOTALL)
                    clean_tds = [re.sub(r'<.*?>', '', td).strip() for td in tds]
                    if len(clean_tds) >= 8 and clean_tds[0].isdigit() and len(clean_tds[0]) > 4:
                        try: start_idx = 2 if int(clean_tds[1]) > 100 else 1
                        except: start_idx = 1
                        if lottery_code == 'dlt':
                            parsed_data.append({
                                '期号': clean_tds[0], '前1': int(clean_tds[start_idx]), '前2': int(clean_tds[start_idx+1]), 
                                '前3': int(clean_tds[start_idx+2]), '前4': int(clean_tds[start_idx+3]), '前5': int(clean_tds[start_idx+4]),
                                '后1': int(clean_tds[start_idx+5]), '后2': int(clean_tds[start_idx+6])
                            })
                        elif lottery_code == 'ssq':
                            parsed_data.append({
                                '期号': clean_tds[0], '前1': int(clean_tds[start_idx]), '前2': int(clean_tds[start_idx+1]), 
                                '前3': int(clean_tds[start_idx+2]), '前4': int(clean_tds[start_idx+3]), '前5': int(clean_tds[start_idx+4]), 
                                '前6': int(clean_tds[start_idx+5]), '后1': int(clean_tds[start_idx+6])
                            })
                if parsed_data: return pd.DataFrame(parsed_data)
        except:
            continue
            
    return pd.DataFrame()

# ==========================================
# 3. 核心运算逻辑
# ==========================================
def calculate_frequencies(df, is_dlt=True):
    if is_dlt:
        front_nums = df[['前1', '前2', '前3', '前4', '前5']].values.flatten()
        back_nums = df[['后1', '后2']].values.flatten()
        front_max, back_max = 35, 12
    else:
        front_nums = df[['前1', '前2', '前3', '前4', '前5', '前6']].values.flatten()
        back_nums = df[['后1']].values.flatten()
        front_max, back_max = 33, 16
        
    front_counts = Counter(front_nums)
    back_counts = Counter(back_nums)
    
    for i in range(1, front_max + 1): front_counts.setdefault(i, 0)
    for i in range(1, back_max + 1): back_counts.setdefault(i, 0)
    return front_counts, back_counts

def calculate_bets(n, r):
    if r > n or r < 0: return 0
    return math.comb(n, r)

def generate_text_report(title, front_counts, back_counts, is_dlt):
    report = f"========== {title} ==========\n\n"
    report += f"[前区统计 (1-{'35' if is_dlt else '33'})]\n"
    def format_dict(counts_dict):
        freq_group = {}
        for num, freq in counts_dict.items():
            freq_group.setdefault(freq, []).append(num)
        res = ""
        for freq in sorted(freq_group.keys(), reverse=True):
            nums = ",".join([str(n).zfill(2) for n in sorted(freq_group[freq])])
            res += f"{freq}次: {nums}\n"
        return res
    report += format_dict(front_counts) + "\n"
    report += f"[后区统计 (1-{'12' if is_dlt else '16'})]\n"
    report += format_dict(back_counts)
    report += "\n========================================="
    return report

# ==========================================
# 4. 侧边栏：操作控制台
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    
    if st.button("🔄 手动联网同步最新开奖", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.success("✅ 已下达最高指令！正在直连官方数据中心...")
        time.sleep(1)
        st.rerun()
        
    st.markdown("---")
    lottery_type = st.selectbox("🎯 切换演算频道", ["双色球 (SSQ)", "大乐透 (DLT)"])
    period_limit = st.slider("📅 本地数据深度扫描 (期)", min_value=10, max_value=100, value=70, step=10)
    
    st.markdown("---")
    st.caption("🚀 引擎状态：双线多核（首选官方内部源）")
    st.caption("🛡️ 防封策略：彻底抛弃高防 HTML，直击底层 JSON")

is_dlt = "DLT" in lottery_type
lottery_code = 'dlt' if is_dlt else 'ssq'

# ==========================================
# 5. 主画面：高级数据看板
# ==========================================
st.header(f"🚀 雷达监测：{lottery_type} (近 {period_limit} 期走势)")

with st.spinner('📡 正在规避商业防火墙，通过内部接口抓取体彩/福彩官方数据...'):
    df_base = fetch_base_data(lottery_code)

if not df_base.empty:
    df = df_base.head(period_limit)
    latest_issue = df_base.iloc[0]['期号']
    
    st.success(f"🟢 **网络联机成功！当前最新期号为**：第 {latest_issue} 期。")
    
    with st.expander("🔍 展开查看最近 10 期真实详细数据"):
        st.dataframe(df.head(10).astype(str), use_container_width=True)

    front_counts, back_counts = calculate_frequencies(df, is_dlt)
    
    if is_dlt:
        front_color_class = "ball-blue"
        back_color_class = "ball-yellow"
    else:
        front_color_class = "ball-red"
        back_color_class = "ball-blue"

    st.subheader("🧬 核心出现频次矩阵")
    
    col1, col2 = st.columns(2)
    def render_balls(counts_dict, ball_class):
        freq_group = {}
        for num, freq in counts_dict.items():
            freq_group.setdefault(freq, []).append(num)
        html_str = ""
        for freq in sorted(freq_group.keys(), reverse=True):
            nums_sorted = sorted(freq_group[freq])
            balls_html = "".join([f"<div class='ball {ball_class}'>{str(n).zfill(2)}</div>" for n in nums_sorted])
            html_str += f"""
            <div class="stat-row">
                <div class="freq-tag">{freq} 次</div>
                <div class="ball-container" style="margin-bottom:0;">{balls_html}</div>
            </div>
            """
        return html_str

    with col1:
        st.markdown(f"### {'🔵' if is_dlt else '🔴'} 前区 (1-{'35' if is_dlt else '33'})")
        st.markdown(render_balls(front_counts, front_color_class), unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"### {'🟡' if is_dlt else '🔵'} 后区 (1-{'12' if is_dlt else '16'})")
        st.markdown(render_balls(back_counts, back_color_class), unsafe_allow_html=True)

    st.markdown("---")
    
    calc_col, export_col = st.columns([1.5, 1])
    with calc_col:
        st.subheader("🧮 专用投资计算器")
        req_f = 5 if is_dlt else 6
        req_b = 2 if is_dlt else 1
        max_f = 35 if is_dlt else 33
        max_b = 12 if is_dlt else 16
        
        cc1, cc2 = st.columns(2)
        with cc1:
            sel_front = st.number_input(f"选取前区个数 (至少{req_f}个)", min_value=req_f, max_value=max_f, value=req_f)
        with cc2:
            sel_back = st.number_input(f"选取后区个数 (至少{req_b}个)", min_value=req_b, max_value=max_b, value=req_b)
            
        bets = calculate_bets(sel_front, req_f) * calculate_bets(sel_back, req_b)
        st.info(f"💰 共计 **{bets}** 注，需投入 **{bets * 2}** 元。（基础倍数）")

    with export_col:
        st.subheader("🖨️ 打印与导出中心")
        report_title = f"{lottery_type} 近 {period_limit} 期走势报告"
        text_report = generate_text_report(report_title, front_counts, back_counts, is_dlt)
        
        st.download_button("📥 下载统计报告 (.txt)", data=text_report, file_name=f"{lottery_type}_report.txt", mime="text/plain", use_container_width=True)

else:
    st.error("🚨 终极警报：中国大陆方向的数据接口临时熔断或正在维护，请几分钟后再点击左侧红色按钮重试！")
