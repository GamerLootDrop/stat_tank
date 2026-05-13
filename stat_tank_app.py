import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from collections import Counter

# ==========================================
# 1. 全局页面配置 (开启宽屏和暗黑模式感)
# ==========================================
st.set_page_config(page_title="坦克指挥控制台", page_icon="🚀", layout="wide")

# 注入自定义 CSS，打造发光的高级“号码球”和卡片效果
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
    }
    .stat-row { display: flex; align-items: center; margin-bottom: 15px; background: #1E1E1E; padding: 10px; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据抓取引擎 (强化防拦截 + 本地兜底)
# ==========================================
@st.cache_data(ttl=3600) # 缓存1小时，避免频繁请求被封
def fetch_dlt_data(limit=100):
    """从官方API自动抓取大乐透最新数据"""
    url = f"https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize={limit}&isVerify=1&pageNo=1"
    
    # 全副武装的请求头，伪装成正常的国内电脑浏览器
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.lottery.gov.cn/",
        "Origin": "https://www.lottery.gov.cn",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('success'):
            records = data['value']['list']
            parsed_data = []
            for item in records:
                draw_no = item['lotteryDrawNum']
                numbers = item['lotteryDrawResult'].split(' ')
                parsed_data.append({
                    '期号': draw_no,
                    '前1': int(numbers[0]), '前2': int(numbers[1]), '前3': int(numbers[2]),
                    '前4': int(numbers[3]), '前5': int(numbers[4]),
                    '后1': int(numbers[5]), '后2': int(numbers[6])
                })
            return pd.DataFrame(parsed_data)
            
    except Exception as e:
        # 如果依然被拦截或网络出错，自动回退到本地数据
        st.warning("⚠️ 云端服务器触发官方防爬保护，系统已自动切换为【本地历史数据】模式。")
        try:
            # 读取你仓库里的 lotto_history_demo.csv
            df_local = pd.read_csv("lotto_history_demo.csv")
            return df_local.head(limit)
        except Exception as local_e:
            st.error("本地备用数据读取失败，请检查 lotto_history_demo.csv 是否存在。")
            return pd.DataFrame()
            
    return pd.DataFrame()

# ==========================================
# 3. 核心统计逻辑
# ==========================================
def calculate_frequencies(df, front_max=35, back_max=12):
    front_nums = df[['前1', '前2', '前3', '前4', '前5']].values.flatten()
    back_nums = df[['后1', '后2']].values.flatten()
    
    front_counts = Counter(front_nums)
    back_counts = Counter(back_nums)
    
    # 补全0次出现的号码
    for i in range(1, front_max + 1): front_counts.setdefault(i, 0)
    for i in range(1, back_max + 1): back_counts.setdefault(i, 0)
        
    return front_counts, back_counts

# ==========================================
# 4. 侧边栏：操作控制台
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
    st.title("控制台设置")
    
    lottery_type = st.selectbox("🎯 切换演算频道", ["大乐透 (DLT)", "双色球 (SSQ) - 待接入"])
    
    # 高级滑块操作：随意拖动，右侧数据瞬间变化
    period_limit = st.slider("📅 深度扫描期数", min_value=10, max_value=100, value=30, step=10)
    
    st.markdown("---")
    st.caption("🔧 系统状态：自动联机抓取中...")
    st.caption("🛡️ 加固逻辑：碎石机 4.0 Pro版")

# ==========================================
# 5. 主画面：高级数据看板
# ==========================================
st.header(f"🚀 雷达监测：{lottery_type} (近 {period_limit} 期走势)")

# 执行抓取
if "DLT" in lottery_type:
    df = fetch_dlt_data(limit=period_limit)
else:
    st.warning("双色球接口正在施工中，当前演示大乐透。")
    df = fetch_dlt_data(limit=period_limit)

if not df.empty:
    # 顶部数据概览
    try:
        latest_issue = df.iloc[0]
        st.info(f"🟢 **最新开奖获取成功**：第 {latest_issue['期号']} 期")
        
        front_counts, back_counts = calculate_frequencies(df)
        
        # ------------------------------------------
        # 模块 A：高级柱状图走势 (Plotly)
        # ------------------------------------------
        st.subheader("📊 全局号码热度图谱")
        
        # 转换数据给 Plotly 用
        front_df = pd.DataFrame(list(front_counts.items()), columns=['号码', '出现次数']).sort_values('号码')
        front_df['号码'] = front_df['号码'].astype(str).str.zfill(2) # 补零，如 01, 02
        
        fig = px.bar(front_df, x='号码', y='出现次数', 
                     color='出现次数', color_continuous_scale='Blues',
                     title="前区号码频次分布", text='出现次数')
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", 
                          font=dict(color="white"), margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

        # ------------------------------------------
        # 模块 B：极客风号码频次矩阵 (替代干瘪的文本)
        # ------------------------------------------
        st.subheader("🧬 高频触达矩阵")
        
        col1, col2 = st.columns(2)
        
        def render_balls(counts_dict, ball_class):
            # 按频次分组
            freq_group = {}
            for num, freq in counts_dict.items():
                freq_group.setdefault(freq, []).append(num)
                
            # 生成 HTML
            html_str = ""
            for freq in sorted(freq_group.keys(), reverse=True):
                nums_sorted = sorted(freq_group[freq])
                balls_html = "".join([f"<div class='ball {ball_class}'>{str(n).zfill(2)}</div>" for n in nums_sorted])
                
                html_str += f"""
                <div class="stat-row">
                    <div class="freq-tag">{freq} 次出现</div>
                    <div class="ball-container" style="margin-bottom:0;">{balls_html}</div>
                </div>
                """
            return html_str

        with col1:
            st.markdown("### 🔵 前区 (1-35)")
            st.markdown(render_balls(front_counts, "ball-front"), unsafe_allow_html=True)
            
        with col2:
            st.markdown("### 🔴 后区 (1-12)")
            st.markdown(render_balls(back_counts, "ball-back"), unsafe_allow_html=True)

    except KeyError:
         st.error("数据列名不匹配。如果是本地数据模式，请确保 csv 文件包含 '期号', '前1', '前2'... '后1', '后2' 这些列。")

else:
    st.error("未能获取到任何数据。")
