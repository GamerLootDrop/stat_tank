import streamlit as st
import pandas as pd
from collections import Counter
import requests
import os

# 1. 坦克外观配置
st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率实时演算终端 (专家版)")

# --- 2. 核心：三线路实时抓取引擎 ---
@st.cache_data(ttl=300) # 每5分钟自动强制检查一次最新开奖
def get_realtime_data():
    # 准备了三条不同的数据进水管
    urls = [
        "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=50&isVerify=1&pageNo=1",
        "http://www.lottery.gov.cn/api/lottery_guide.php?gameNo=85",
        "https://m.sporttery.cn/api/lottery_draw_num.php?gameNo=85"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)"}
    
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                raw_list = data.get('value', {}).get('list', []) or data.get('list', [])
                if raw_list:
                    return pd.DataFrame([{
                        "期号": i['lotteryDrawNum'], 
                        "红球": " ".join(i['lotteryDrawResult'].split()[:5])
                    } for i in raw_list])
        except: continue
    return pd.DataFrame()

# 执行抓取
with st.spinner('📡 正在破译防火墙，实时同步最新开奖数据...'):
    df_raw = get_realtime_data()

# --- 3. 统计与记录逻辑 ---
if not df_raw.empty:
    latest_issue = df_raw.iloc[0]['期号']
    st.success(f"✅ 实时数据已就绪：当前最新为第 {latest_issue} 期")
    
    num_p = st.sidebar.number_input("统计最近期数", value=29, min_value=1)
    counts = Counter([int(n) for s in df_raw.head(num_p)['红球'] for n in s.split() if n.isdigit()])
    
    # 频率分组
    mapping = {c: [] for c in range(max(counts.values() or [0]) + 1)}
    for i in range(1, 36): mapping[counts.get(i, 0)].append(i)
    
    # 显示红框
    for f in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
        color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
        st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:10px;"><div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:80px;text-align:center;">{f} 次</div><div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div></div>', unsafe_allow_html=True)

    # --- 记录功能（只有在有数据时才激活） ---
    st.markdown("---")
    if st.button("💾 点击记录当前【实时频率快照】"):
        # 记录最热的几个号
        hot_nums = ",".join([f"{x:02d}" for x in mapping[max(mapping.keys())]])
        new_row = {"记录时间": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), "对应期号": latest_issue, "当时最热号": hot_nums}
        
        # 存入 GitHub 上的历史账本
        hist_file = "history_log.csv"
        df_log = pd.DataFrame([new_row])
        df_log.to_csv(hist_file, mode='a', header=not os.path.exists(hist_file), index=False)
        st.balloons()
        st.success(f"已成功将第 {latest_issue} 期的频率快照记入账本！")

else:
    st.error("🚨 实时同步暂时受阻。")
    if st.button("♻️ 强制重启抓取引擎"):
        st.cache_data.clear()
        st.rerun()
