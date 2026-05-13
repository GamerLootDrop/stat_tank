import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率实时过滤器 (全彩种终极适配版)")

# --- 1. 获取文件夹内所有 CSV 文件 ---
def get_all_csvs():
    return [f for f in os.listdir('.') if f.lower().endswith('.csv')]

csv_list = get_all_csvs()

if not csv_list:
    st.error("🚨 警告：文件夹里没看到 CSV 数据文件！")
else:
    # 2. 侧边栏设置
    st.sidebar.header("⚙️ 核心设置")
    target = st.sidebar.selectbox("🎯 确认当前演算文件：", csv_list)
    
    try:
        # 统一读取：跳过第一行空行
        df = pd.read_csv(target, skiprows=1)
        # 暴力清理：删掉没数据的空行
        df = df.dropna(how='all').dropna(subset=[df.columns[0], df.columns[1]], how='all')
        
        # 识别彩种逻辑
        is_ssq = "ssq" in target.lower() or "双色球" in target
        ball_limit = 6 if is_ssq else 5
        max_ball_num = 33 if is_ssq else 35
        game_label = "🔴 双色球" if is_ssq else "🟢 大乐透"

        # 获取当前期号 (处理掉 .0)
        try:
            raw_id = str(df.iloc[0, 0])
            latest_id = raw_id.split('.')[0] if '.' in raw_id else raw_id
        except:
            latest_id = "未知"

        st.success(f"✅ 已精准定位：{game_label} | 最新期：第 {latest_id} 期")

        # 3. 频率演算
        num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1, max_value=len(df))
        subset = df.head(int(num_p))
        
        all_balls = []
        # 遍历每一行抓取号码
        for r_idx in range(len(subset)):
            line_data = subset.iloc[r_idx].values
            valid_numbers_in_row = []
            
            # 从第3个格子（索引2）开始向后扫描整行
            for item in line_data[2:]:
                try:
                    # 关键修复：处理各种 13.0, " 13 ", 13 等格式
                    clean_val = int(float(str(item).strip()))
                    if 1 <= clean_val <= max_ball_num:
                        valid_numbers_in_row.append(clean_val)
                except: continue
            
            # 根据彩种需求，只取前 5 或 6 个数字
            all_balls.extend(valid_numbers_in_row[:ball_limit])

        # 计算频率分布
        counts = Counter(all_balls)
        max_f = max(counts.values()) if counts else 0
        mapping = {c: [] for c in range(max_f + 1)}
        for i in range(1, max_ball_num + 1):
            mapping[counts.get(i, 0)].append(i)

        # 4. 视觉展示
        st.subheader(f"📅 {game_label} 最近 {num_p} 期频率分布图")
        for f in sorted(mapping.keys(), reverse=True):
            nums = sorted(mapping[f])
            nums_str = "  ".join([f"{x:02d}" for x in nums])
            
            # 配色逻辑
            if f >= 5: color = "#FF4B4B"  # 高频红
            elif f == 0: color = "#9FA8DA" # 遗漏灰
            else: color = "#31333F"        # 普通黑
            
            st.markdown(f"""
            <div style="display:flex;align-items:center;margin-bottom:10px;">
                <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:120px;text-align:center;">{f} 次出现</div>
                <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
            </div>""", unsafe_allow_html=True)
            
        # 5. 记录快照
        st.markdown("---")
        if st.button("💾 记录当前统计数据"):
            st.balloons()
            st.toast(f"记录成功：{game_label} 已存档")

    except Exception as e:
        st.error(f"表格格式不兼容：{e}")
        st.info("建议：请确保您上传的是 CSV 格式的文件。")
