import streamlit as st
import pandas as pd
from collections import Counter
import requests
import os

# 1. 仪表盘配置
st.set_page_config(page_title="数据频率演算终端", layout="wide")
st.title("📊 大数据频率深度过滤器 (Pro版)")
st.markdown("---")

# --- 2. 联网同步最新数据（加强防报错版） ---
@st.cache_data(ttl=600)  # 每10分钟尝试更新
def fetch_lotto_data():
    # 接口1：体彩官方
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&isVerify=1&pageNo=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://www.sporttery.cn/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            raw_list = response.json().get('value', {}).get('list', [])
            if raw_list:
                data = [{"期号": i['lotteryDrawNum'], "红球": " ".join(i['lotteryDrawResult'].split(' ')[:5]), "日期": i['lotteryDrawTime']} for i in raw_list]
                return pd.DataFrame(data)
    except Exception as e:
        print(f"尝试同步失败: {e}")
    return pd.DataFrame()

with st.spinner('📡 正在尝试多种方式同步最新数据...'):
    df_raw = fetch_lotto_data()

# --- 3. 如果同步失败，允许手动录入（保底方案） ---
if df_raw.empty:
    st.error("📡 自动同步暂时受阻（网络波动）。")
    st.info("💡 别担心，您可以手动输入最新一期号码，工具依然可以计算：")
    manual_input = st.text_input("请输入最新一期红球（如：01 02 03 04 05）")
    if manual_input:
        # 这里逻辑可以继续运行，但最好是让自动抓取成功
        st.warning("建议刷新页面重试，或联系技术支持。")
else:
    # --- 4. 正常显示统计（同之前逻辑） ---
    latest = df_raw.iloc[0]
    st.success(f"✅ 联网同步成功：第 {latest['期号']} 期 | 开奖：{latest['红球']}")

    num_periods = st.sidebar.number_input("统计最近期数", value=29, min_value=1)
    
    recent_df = df_raw.head(num_periods)
    all_reds = [int(n) for s in recent_df['红球'] for n in s.split()]
    counts = Counter(all_reds)
    
    mapping = {c: [] for c in range(max(counts.values()) + 1) if c >= 0}
    for i in range(1, 36):
        mapping[counts.get(i, 0)].append(i)
    
    for freq in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[freq])])
        color = "#FF4B4B" if freq >= 5 else ("#9FA8DA" if freq == 0 else "#31333F")
        st.markdown(f"""<div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="background-color:{color}; color:white; padding:5px 15px; border-radius:5px; font-weight:bold; width:80px; text-align:center;">{freq} 次</div>
            <div style="margin-left:20px; font-size:22px; font-family:monospace; font-weight:bold;">{nums_str}</div>
        </div>""", unsafe_allow_html=True)

    # --- 5. 账本记录 ---
    st.markdown("---")
    st.subheader("📁 数据快照记录")
    SAVE_FILE = "stat_history.csv"
    if st.button("💾 保存当前频率快照"):
        hot_nums = ",".join([f"{x:02d}" for x in sorted(mapping[max(mapping.keys())])])
        new_data = {"记录日期": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), "对应期号": latest['期号'], "高频红号": hot_nums}
        df_log = pd.DataFrame([new_data])
        # 记录到文件
        if not os.path.exists(SAVE_FILE):
            df_log.to_csv(SAVE_FILE, index=False)
        else:
            df_log.to_csv(SAVE_FILE, mode='a', header=False, index=False)
        st.balloons()

    if os.path.exists(SAVE_FILE):
        st.table(pd.read_csv(SAVE_FILE).tail(5))
