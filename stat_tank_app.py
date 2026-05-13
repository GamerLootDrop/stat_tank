import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="大数据频率演算终端", layout="wide")
st.title("📊 大数据频率实时过滤器 (全自动版)")

# --- 1. 获取所有数据文件 ---
def get_files():
    # 强制只找 CSV 结尾的文件
    return [f for f in os.listdir('.') if f.endswith('.csv')]

csv_list = get_files()

if not csv_list:
    st.error("🚨 文件夹里没看到 CSV 文件！请确保双色球和大乐透的表格都在 stat_tank 文件夹里。")
else:
    # 2. 侧边栏：选彩种
    st.sidebar.header("⚙️ 核心设置")
    target = st.sidebar.selectbox("🎯 确认当前数据源文件", csv_list)
    
    try:
        # 读取表格（跳过第1行空行）
        df = pd.read_csv(target, skiprows=1)
        # 删掉全是空的行
        df = df.dropna(how='all').dropna(subset=[df.columns[0]])
        
        # 判断彩种（根据文件名）
        is_ssq = "ssq" in target.lower() or "双色球" in target
        ball_count = 6 if is_ssq else 5
        max_ball = 33 if is_ssq else 35
        game_label = "🔴 双色球" if is_ssq else "🟢 大乐透"

        # 3. 统计演算
        num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1, max_value=len(df))
        st.success(f"✅ 已加载 {game_label} | 文件：{target} | 最新期：{df.iloc[0, 0]}")

        # 截取选定行
        subset = df.head(int(num_p))
        
        # 【暴力清洗数字】不管表格多乱，只抓数字
        all_balls = []
        for r_idx in range(len(subset)):
            # 抓取第3列开始的球（索引2开始）
            raw_row = subset.iloc[r_idx, 2 : 2 + ball_count].values
            for b in raw_row:
                try:
                    # 关键修复：先转浮点再转整，解决 13.0 的问题
                    val = int(float(str(b).strip()))
                    if 1 <= val <= max_ball:
                        all_balls.append(val)
                except: continue

        # 计算频率
        counts = Counter(all_balls)
        max_f = max(counts.values()) if counts else 0
        mapping = {c: [] for c in range(max_f + 1)}
        for i in range(1, max_ball + 1):
            mapping[counts.get(i, 0)].append(i)

        # 4. 出图
        st.subheader(f"📅 {game_label} 最近 {num_p} 期频率分布图")
        for f in sorted(mapping.keys(), reverse=True):
            nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
            color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
            st.markdown(f"""
            <div style="display:flex;align-items:center;margin-bottom:10px;">
                <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:120px;text-align:center;">{f} 次出现</div>
                <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
            </div>""", unsafe_allow_html=True)
        
        # 5. 记录器
        st.markdown("---")
        if st.button("💾 记录当前快照"):
            st.balloons()
            st.toast(f"已记录：{game_label} 第 {df.iloc[0, 0]} 期快照")

    except Exception as e:
        st.error(f"解析出错，请确认表格格式：{e}")
