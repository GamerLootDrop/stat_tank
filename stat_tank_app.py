import streamlit as st
import pandas as pd
from collections import Counter
import os
import re

st.set_page_config(page_title="坦克频率终端", layout="wide")
st.title("🚀 坦克大数据频率过滤器 (全兼容终极版)")

# 1. 扫描所有 CSV 文件
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]

if not csv_files:
    st.error("🚨 仓库里没看到 CSV 文件！请确认上传到了 stat_tank 文件夹。")
else:
    target = st.sidebar.selectbox("🎯 选择数据文件", csv_files)
    
    try:
        # 使用更稳健的方式读取，忽略可能的编码问题
        df = pd.read_csv(target, skiprows=1, encoding_errors='ignore')
        
        # 自动识别模式
        is_ssq = "ssq" in target.lower() or "双色球" in target
        ball_count = 6 if is_ssq else 5
        max_val = 33 if is_ssq else 35
        
        num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1)
        # 清理掉完全空的行
        subset = df.dropna(how='all').head(num_p)
        
        all_balls = []
        
        # --- 暴力打捞逻辑 ---
        for _, row in subset.iterrows():
            row_numbers = []
            # 扫描这一行所有的格子
            for item in row.values:
                try:
                    # 强力提取：只保留数字和小数点
                    s = str(item).strip()
                    clean_s = re.sub(r'[^0-9.]', '', s)
                    if clean_s:
                        val = int(float(clean_s))
                        # 核心过滤：期号一般很大（比如202401），我们只要 1-35 之间的
                        if 1 <= val <= max_val:
                            row_numbers.append(val)
                except:
                    continue
            
            # 关键：大乐透一般在前，双色球也在前。
            # 为了防止抓到后区的蓝球，我们只取这一行里最先出现的 5 个或 6 个数字
            if len(row_numbers) >= ball_count:
                all_balls.extend(row_numbers[:ball_count])

        # --- 统计绘图 ---
        counts = Counter(all_balls)
        if not counts:
            st.warning("⚠️ 警告：读到了文件，但没捞出号码。请确保表格里有开奖数字。")
        else:
            st.success(f"✅ 成功连接：{target} | 模式：{'双色球' if is_ssq else '大乐透'}")
            
            # 频率分组显示
            max_f = max(counts.values()) if counts else 0
            for f in range(max_f, -1, -1):
                nums = [i for i in range(1, max_val + 1) if counts.get(i, 0) == f]
                if nums:
                    nums_str = "  ".join([f"{x:02d}" for x in sorted(nums)])
                    color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;margin-bottom:10px;">
                        <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:120px;text-align:center;">{f} 次出现</div>
                        <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
                    </div>""", unsafe_allow_html=True)
            
            if st.button("💾 记录快照"):
                st.balloons()

    except Exception as e:
        st.error(f"解析出错：{e}")
