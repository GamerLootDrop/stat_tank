import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from collections import Counter
import re
import math

# ==========================================
# 1. 全局页面配置
# ==========================================
st.set_page_config(page_title="坦克指挥控制台", page_icon="🚀", layout="wide")

# 注入自定义 CSS (定义好红、蓝、黄三种球的样式)
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
# 2. 超级数据抓取引擎 (修复了期号抓取错位的Bug)
# ==========================================
@st.cache_data(ttl=1800)
def fetch_latest_data(lottery_code, limit=100):
    url = f"https://datachart.500.com/{lottery_code}/history/newinc/history.php?limit={limit}&sort=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        html = response.text
        
        tbody_match = re.search(r'<tbody id="tdata">(.*?)</tbody>', html, re.DOTALL)
        if not tbody_match: return pd.DataFrame()
            
        tbody = tbody_match.group(1)
        trs = re.findall(r'<tr.*?>(.*?)</tr>', tbody, re.DOTALL)
        
        parsed_data = []
        for tr in trs:
            tds = re.findall(r'<td.*?>(.*?)</td>', tr, re.DOTALL)
            clean_tds = [re.sub(r'<.*?>', '', td).strip() for td in tds]
            
            # 强化校验：期号长度必须大于4，避免把序号(如1, 2, 3)当成期号
            if len(clean_tds) >= 8 and clean_tds[0].isdigit() and len(clean_tds[0]) > 4:
                try:
                    start_idx = 2 if int(clean_tds[1]) > 100 else 1
                except:
                    start_idx = 1
                    
                if lottery_code == 'dlt':
                    parsed_data.append({
                        '期号': clean_tds[0],
                        '前1': int(clean_tds[start_idx]), '前2': int(clean_tds[start_idx+1]), '前3': int(clean_tds[start_idx+2]),
                        '前4': int(clean_tds[start_idx+3]), '前5': int(clean_tds[start_idx+4]),
                        '后1': int(clean_tds[start_idx+5]), '后2': int(clean_tds[start_idx+6])
                    })
                elif lottery_code == 'ssq':
                    parsed_data.append({
                        '期号': clean_tds[0],
                        '前1': int(clean_tds[start_idx]), '前2': int(clean_tds[start_idx+1]), '前3': int(clean_tds[start_idx+2]),
                        '前4': int(clean_tds[start_idx+3]), '前5': int(clean_tds[start_idx+4]), '前6': int(clean_tds[start_idx+5]),
                        '后1': int(clean_tds[start_idx+6])
                    })
                    
        if parsed_data:
            return pd.DataFrame(parsed_data).head(limit)
            
    except Exception as e:
        st.error(f"联机抓取发生异常: {e}")
        
    return pd.DataFrame()

# ==========================================
# 3. 核心统计逻辑
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

# 用于生成可复制/打印的纯文本报告
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

# 组合数学公式 (用于计算器)
def calculate_bets(n, r):
    if r > n or r < 0: return 0
    return math.comb(n, r)

# ==========================================
# 4. 侧边栏：操作控制台
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    
    lottery_type = st.selectbox("🎯 切换演算频道", ["双色球 (SSQ)", "大乐透 (DLT)"])
    period_limit = st.slider("📅 深度扫描期数", min_value=10, max_value=100, value=30, step=10)
    
    st.markdown("---")
    st.caption("🔧 系统状态：公网直连模式")
    st.caption("🛡️ 颜色校对：精准模式开启")

is_dlt = "DLT" in lottery_type

# ==========================================
# 5. 主画面：高级数据看板
# ==========================================
st.header(f"🚀 雷达监测：{lottery_type} (近 {period_limit} 期走势)")

df = fetch_latest_data('dlt' if is_dlt else 'ssq', limit=period_limit)

if not df.empty:
    latest_issue = df.iloc[0]['期号']
    st.success(f"🟢 **网络联机成功！当前抓取到的最新期号为**：第 {latest_issue} 期")
    
    # --- 【新增】历史数据校验看板 ---
    with st.expander("🔍 展开查看最近 10 期真实开奖数据 (校验防伪)"):
        st.dataframe(df.head(10).astype(str), use_container_width=True)

    front_counts, back_counts = calculate_frequencies(df, is_dlt)
    
    # --- 动态色彩配置 ---
    if is_dlt:
        front_color_class = "ball-blue"
        back_color_class = "ball-yellow"
    else:
        front_color_class = "ball-red"
        back_color_class = "ball-blue"

    # --- 高频触达矩阵 ---
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
    
    # --- 【新增】复式投资计算器 & 一键复制打印 ---
    calc_col, export_col = st.columns([1.5, 1])
    
    with calc_col:
        st.subheader("🧮 专用投资计算器 (复式/胆拖测算)")
        st.info("💡 请输入你打算挑选的号码个数，系统将自动算出总注数和花费。")
        
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
        cost = bets * 2
        st.success(f"💰 按照此方案，共计 **{bets}** 注，需要投入 **{cost}** 元。（基础倍数）")

    with export_col:
        st.subheader("🖨️ 打印与导出中心")
        report_title = f"{lottery_type} 近 {period_limit} 期走势报告"
        text_report = generate_text_report(report_title, front_counts, back_counts, is_dlt)
        
        st.download_button(
            label="📥 一键下载完整统计报告 (.txt)",
            data=text_report,
            file_name=f"{lottery_type}_report.txt",
            mime="text/plain",
            use_container_width=True
        )
        st.caption("或者直接在下方框内 Ctrl+A 全选复制：")
        st.code(text_report, language="text")

else:
    st.error("🚨 无法获取数据！请检查当前网络连接或平台服务状态。")
