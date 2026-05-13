import streamlit as st
import pandas as pd
from collections import Counter
import requests
import time

# 1. 页面配置
st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率实时过滤器 (最新50期版)")

# --- 2. 核心：50期实时抓取引擎 ---
@st.cache_data(ttl=600) # 每10分钟自动刷新一次
def get_latest_50_data():
    # 官方高性能实时接口
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=50&isVerify=1&pageNo=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        # 增加超时逻辑，防止卡死
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            res_data = response.json()
            raw_list = res_data.get('value', {}).get('list', [])
            if raw_list:
                # 只精准提取最新的50期
                data = []
                for i in raw_list:
                    # 提取红球号码
                    reds = i['lotteryDrawResult'].split(' ')[:5]
                    data.append({
                        "期号": i['lotteryDrawNum'],
                        "红球": " ".join(reds),
                        "时间": i['lotteryDrawTime']
                    })
                return pd.DataFrame(data)
    except Exception as e:
        st.error(f"📡 实时同步尝试中... 请点击下方重启按钮")
    return pd.DataFrame()

# 自动运行同步
with st.spinner('📡 正在联网同步最新50期开奖数据...'):
    df_50 = get_latest_50_data()

# --- 3. 统计展示与记录 ---
if not df_50.empty:
    latest = df_50.iloc[0]
    st.success(f"✅ 实时数据已连通！当前最新：第 {latest['期号']} 期 ({latest['时间']})")
    
    # 频率演算逻辑
    all_nums = [int(n) for s in df_50['红球'] for n in s.split()]
    counts = Counter(all_nums)
    
    # 建立频率分组
    mapping = {c: [] for c in range(max(counts.values() or [0]) + 1)}
    for i in range(1, 36):
        mapping[counts.get(i, 0)].append(i)
        
    # 还原您的红框统计视觉图
    for f in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
        color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
        st.markdown(f"""
        <div style="display:flex;align-items:center;margin-bottom:10px;">
            <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:80px;text-align:center;">{f} 次</div>
            <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
        </div>""", unsafe_allow_html=True)

    # 4. 实时记录功能
    st.markdown("---")
    if st.button("💾 记录当前 50 期实时频率快照"):
        # 记录到 CSV 账本
        log_data = {
            "记录时间": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
            "最新期号": latest['期号'],
            "高频号": " ".join([f"{x:02d}" for x in sorted(mapping[max(mapping.keys())])])
        }
        # 自动生成历史记录文件
        log_df = pd.DataFrame([log_data])
        log_df.to_csv("tank_history.csv", mode='a', header=not os.path.exists("tank_history.csv"), index=False)
        st.balloons()
        st.success("实时快照已记入账本！")

else:
    st.warning("🚨 正在等待数据源响应...")
    if st.button("♻️ 点击手动唤醒实时同步"):
        st.cache_data.clear()
        st.rerun()

st.caption("数据演算终端 · 实时50期滚动版")
