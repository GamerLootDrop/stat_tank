import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="坦克频率终端", layout="wide")
st.title("🚀 坦克大数据频率过滤器 (最终修正版)")

# 1. 扫描所有 CSV 文件
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]

if not csv_files:
    st.error("🚨 仓库文件夹里没看到 CSV 文件！请确保文件已上传到 stat_tank 文件夹。")
else:
    target = st.sidebar.selectbox("🎯 选择数据源", csv_files)
    
    try:
        # 读取表格（跳过第一行空行）
        df = pd.read_csv(target, skiprows=1)
        
        # 自动识别：双色球 (SSQ) 还是大乐透 (DLT)
        is_ssq = "ssq" in target.lower() or "双色球" in target
        ball_count = 6 if is_ssq else 5
        max_val = 33 if is_ssq else 35
        
        # --- 核心修复：智能定位红球起始列 ---
        start_col = -1
        # 扫描所有表头，寻找“前”或者“红”字
        for i, col_name in enumerate(df.columns):
            name = str(col_name)
            if "前" in name or "红" in name:
                start_col = i
                break
        
        # 如果没找到表头（您的表头有时是空格），就用暴力索引
        if start_col == -1:
            start_col = 4 if is_ssq else 2

        st.sidebar.info(f"模式：{'双色球' if is_ssq else '大乐透'} | 起始列：第{start_col+1}列")
        
        num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1)
        subset = df.dropna(how='all').head(num_p)
        
        all_balls = []
        for _, row in subset.iterrows():
            # 从智能定位的起始列开始，抓取对应数量的球
            row_slice = row.iloc[start_col : start_col + ball_count].values
            for b in row_slice:
                try:
                    # 处理 13.0 这种带小数点的脏数据
                    v = int(float(str(b).strip()))
                    if 1 <= v <= max_val:
                        all_balls.append(v)
                except: continue

        # --- 绘图逻辑 ---
        counts = Counter(all_balls)
        if not counts:
            st.warning("⚠️ 还是没数出号码！请确认文件是否为 CSV 格式，且号码在正确格子里。")
        else:
            st.success(f"✅ 成功提取 {len(all_balls)} 个号码进行演算")
            # 频率分组显示
            max_f = max(counts.values())
            for f in range(max_f, -1, -1):
                nums = [i for i in range(1, max_val + 1) if counts.get(i, 0) == f]
                if nums:
                    nums_str = "  ".join([f"{x:02d}" for x in sorted(nums)])
                    # 颜色：高频红，0次灰，其他黑
                    color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;margin-bottom:10px;">
                        <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:120px;text-align:center;">{f} 次出现</div>
                        <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
                    </div>""", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"解析出错：{e}")
