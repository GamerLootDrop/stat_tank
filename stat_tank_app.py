import streamlit as st
import pandas as pd
from collections import Counter
import os
import re

st.set_page_config(page_title="坦克频率终端", layout="wide")
st.title("🚀 坦克大数据频率过滤器 (碎石机版)")

# 1. 扫描所有文件
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]

if not csv_files:
    st.error("🚨 仓库文件夹里没看到 CSV 文件！请确认已上传。")
else:
    target = st.sidebar.selectbox("🎯 选择数据源", csv_files)
    
    try:
        # 强制用最原始的方式读取文本，不让 Pandas 乱猜格式
        with open(target, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # 自动识别：双色球还是大乐透
        is_ssq = "ssq" in target.lower() or "双色球" in target
        ball_count = 6 if is_ssq else 5
        max_val = 33 if is_ssq else 35
        
        num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1)
        
        all_balls = []
        # 跳过前两行（空行和表头），从第三行开始捞
        count_lines = 0
        for line in lines[2:]:
            if count_lines >= num_p: break
            
            # 使用正则：把这一行里所有的纯数字全部抠出来
            # 比如 "2026048.0, 09, 15.0" 会变成 ['2026048', '0', '09', '15', '0']
            raw_numbers = re.findall(r'\d+', line)
            
            row_numbers = []
            for n in raw_numbers:
                val = int(n)
                # 过滤掉期号（比如2026048）和年份，只要 1 到 max_val 之间的
                if 1 <= val <= max_val:
                    row_numbers.append(val)
            
            # 关键：大乐透取前5个，双色球取前6个（排除掉后面重复的或奖金数）
            if len(row_numbers) >= ball_count:
                all_balls.extend(row_numbers[:ball_count])
                count_lines += 1

        # --- 绘图 ---
        counts = Counter(all_balls)
        if not counts:
            st.warning("⚠️ 碎石机也没捞出号码！请确认表格里确实有开奖数字。")
        else:
            st.success(f"✅ 成功打捞！当前模式：{'双色球' if is_ssq else '大乐透'}")
            
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

    except Exception as e:
        st.error(f"出错啦：{e}")
