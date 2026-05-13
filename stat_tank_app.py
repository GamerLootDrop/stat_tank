import streamlit as st
import pandas as pd
from collections import Counter
import math
import os

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
# 2. 数据源脱机读取引擎 (彻底告别网络拦截)
# ==========================================
@st.cache_data
def load_local_data(lottery_code, uploaded_file=None):
    # 优先读取管理员临时上传的文件
    if uploaded_file is not None:
        try:
            return pd.read_csv(uploaded_file)
        except:
            return pd.DataFrame()
            
    # 如果没上传，则默认去读取 GitHub 根目录下的 .csv 文件
    file_path = f"{lottery_code}.csv"
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path)
        except:
            pass
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
    
    lottery_type = st.selectbox("🎯 切换演算频道", ["双色球 (SSQ)", "大乐透 (DLT)"])
    period_limit = st.slider("📅 深度扫描期数", min_value=10, max_value=100, value=70, step=10)
    
    st.markdown("---")
    st.markdown("### 🗄️ 数据库管理 (Admin)")
    st.caption("脱机模式下，可在此临时上传最新的 CSV 数据包。")
    uploaded_file = st.file_uploader(f"临时投喂 {lottery_type} 数据 (.csv)", type=['csv'])

    st.markdown("---")
    st.caption("🚀 引擎状态：本地静态解耦模式")
    st.caption("🛡️ 防封策略：彻底断开公网爬虫，100% 免拦截")

is_dlt = "DLT" in lottery_type
lottery_code = 'dlt' if is_dlt else 'ssq'

# ==========================================
# 5. 主画面：高级数据看板
# ==========================================
st.header(f"🚀 雷达监测：{lottery_type} (近 {period_limit} 期走势)")

# 读取数据：优先读上传的，没上传就读同目录下的 .csv
df_base = load_local_data(lottery_code, uploaded_file)

if not df_base.empty:
    # 截取滑动条指定的期数
    df = df_base.head(period_limit)
    latest_issue = str(df_base.iloc[0]['期号'])
    
    st.success(f"🟢 **静态金库加载成功！响应时间 0ms。当前金库最新期号为**：第 {latest_issue} 期。")
    
    with st.expander("🔍 展开查看基础数据源 (CSV)"):
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
    st.warning("⚠️ **脱机金库暂无数据！**")
    st.info("请通过左侧边栏的【数据库管理】上传最新的 `.csv` 文件，或者在你的 GitHub 代码根目录中放置 `dlt.csv` 和 `ssq.csv`，网站将自动读取。")
    st.markdown("""
    **如何准备 CSV 文件？**
    表格需包含表头：`期号,前1,前2,前3,前4,前5,后1,后2` (大乐透) 或 `期号,前1,前2,前3,前4,前5,前6,后1` (双色球)。
    """)
