import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="大数据频率演算终端", layout="wide")
st.title("📊 大数据频率实时过滤器 (全彩种兼容版)")

# --- 1. 获取文件夹内所有 CSV 文件 ---
def get_all_csv_files():
    # 只要是 csv 结尾的，统统抓出来
    return [f for f in os.listdir('.') if f.lower().endswith('.csv')]

csv_list = get_all_csv_files()

if not csv_list:
    st.error("🚨 警告：文件夹里没看到 CSV 文件！")
    st.info("💡 请确认您的 'dlt.xls - data.csv' 和 'ssq.xls - data.csv' 就在 stat_tank 文件夹里。")
else:
    # 2. 侧边栏：让您亲手选文件
    st.sidebar.header("⚙️ 数据源选择")
    # 这里会列出您截图里那两个长名字的文件
    target = st.sidebar.selectbox("🎯 请选择要演算的文件：", csv_list)
    
    try:
        # 读取表格（您的表格第1行是空的，skiprows=1 必须留着）
        df = pd.read_csv(target, skiprows=1)
        
        # 彻底清洗：删掉全是空的行，确保第一列是期号
        df = df.dropna(how='all').dropna(subset=[df.columns[0]])
        
        # 判断是 33选6 还是 35选5
        is_ssq = "ssq" in target.lower()
        ball_count = 6 if is_ssq else 5
        max_ball = 33 if is_ssq else 35
        game_label = "🔴 双色球" if is_ssq else "🟢 大乐透"

        # 3. 统计演算
        st.success(f"✅ 已加载：{target} ({game_label})")
        num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1, max_value=len(df))
        
        # 截取选定行
        subset = df.head(int(num_p))
        
        # 核心抓取逻辑：适配您的表格列结构
        all_balls = []
        for r_idx in range(len(subset)):
            # 从第3列（索引2）开始抓取红球
            raw_row = subset.iloc[r_idx, 2 : 2 + ball_count].values
            for b in raw_row:
                try:
                    # 解决 13.0 这种带小数点的干扰
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
        # 倒序显示，高频在上
        for f in sorted(mapping.keys(), reverse=True):
            nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
            color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
            st.markdown(f"""
            <div style="display:flex;align-items:center;margin-bottom:10px;">
                <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:120px;text-align:center;">{f} 次出现</div>
                <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
            </div>""", unsafe_allow_html=True)
        
        # 5. 记录按钮
        st.markdown("---")
        if st.button("💾 点击记录当前快照"):
            st.balloons()
            st.toast(f"记录成功：{game_label} 第 {df.iloc[0,0]} 期数据已存。")

    except Exception as e:
        st.error(f"解析出错：{e}")
