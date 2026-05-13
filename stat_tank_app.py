import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from collections import Counter
import re

# ==========================================
# 1. 全局页面配置
# ==========================================
st.set_page_config(page_title="坦克指挥控制台", page_icon="🚀", layout="wide")

# 注入自定义 CSS
st.markdown("""
<style>
    .ball-container { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
    .ball {
        width: 40px; height: 40px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: bold; font-size: 16px; color: white;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
    }
    .ball-front { background: linear-gradient(135deg, #0052D4, #4364F7, #6FB1FC); }
    .ball-back { background: linear-gradient(135deg, #FF416C, #FF4B2B); }
    .freq-tag {
        background-color: #2b2b2b; color: #00E676; padding: 5px 10px;
        border-radius: 5px; font-weight: bold; margin-right: 15px;
        border-left: 4px solid #00E676;
        min-width: 80px; text-align: center;
    }
    .stat-row { display: flex; align-items: center; margin-bottom: 15px; background: #1E1E1E; padding: 10px; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 超级数据抓取引擎 (加入动态防错位机制)
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
        if not tbody_match:
            return pd.DataFrame()
            
        tbody = tbody_match.group(1)
        trs = re.findall(r'<tr.*?>(.*?)</tr>', tbody, re.DOTALL)
        
        parsed_data = []
        for tr in trs:
            tds = re.findall(r'<td.*?>(.*?)</td>', tr, re.DOTALL)
            clean_tds = [re.sub(r'<.*?>', '', td).strip() for td in tds]
            
            if len(clean_tds) >= 8 and clean_tds[0].isdigit():
                # 🛡️ 核心修复：动态纠偏逻辑
                # 如果第2列（索引1）也是类似期号的巨大数字，说明存在隐藏列，真实号码从第3列（索引2）开始
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

# ==========================================
# 4. 侧边栏：操作控制台
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    
    lottery_type = st.selectbox("🎯 切换演算频道", ["大乐透 (DLT)", "双色球 (SSQ)"])
    period_limit = st.slider("📅 深度扫描期数", min_value=10, max_value=100, value=30, step=10)
    
    st.markdown("---")
    st.caption("🔧 系统状态：公网直连模式 (带自动纠偏)")
    st.caption("🛡️ 数据源：500.com 实时图表")

# ==========================================
# 5. 主画面：高级数据看板
# ==========================================
st.header(f"🚀 雷达监测：{lottery_type} (近 {period_limit} 期走势)")

is_dlt = "DLT" in lottery_type
df = fetch_latest_data('dlt' if is_dlt else 'ssq', limit=period_limit)

if not df.empty:
    latest_issue = df.iloc[0]
    st.success(f"🟢 **网络联机成功！当前抓取到的最新期号为**：第 {latest_issue['期号']} 期")
    
    front_counts, back_counts = calculate_frequencies(df, is_dlt)
    
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
        st.markdown(f"### 🔵 前区 (1-{'35' if is_dlt else '33'})")
        st.markdown(render_balls(front_counts, "ball-front"), unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"### 🔴 后区 (1-{'12' if is_dlt else '16'})")
        st.markdown(render_balls(back_counts, "ball-back"), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📊 全局前区号码热度柱状图")
    front_df = pd.DataFrame(list(front_counts.items()), columns=['号码', '出现次数']).sort_values('号码')
    front_df['号码'] = front_df['号码'].astype(str).str.zfill(2)
    fig = px.bar(front_df, x='号码', y='出现次数', color='出现次数', color_continuous_scale='Blues', text='出现次数')
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), margin=dict(t=20, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("🚨 无法获取数据！请检查当前网络连接或平台服务状态。")
