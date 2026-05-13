import streamlit as st
import pandas as pd
from collections import Counter
import os
import re

# 设置页面
st.set_page_config(page_title="坦克频率分析终端", layout="wide")

# --- 🚀 豪华装修 CSS (深色科技风) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        color: #ffffff;
    }
    .freq-card {
        background: rgba(255, 255, 255, 0.07);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
        transition: transform 0.3s;
    }
    .freq-card:hover {
        transform: scale(1.01);
        background: rgba(255, 255, 255, 0.1);
    }
    .freq-label {
        font-size: 1.4rem;
        font-weight: bold;
        min-width: 120px;
        text-align: center;
        padding-right: 20px;
        border-right: 2px solid rgba(255,255,255,0.1);
    }
    .num-display {
        font-family: 'Consolas', monospace;
        font-size: 28px;
        font-weight: bold;
        color: #00f2fe;
        padding-left: 30px;
        letter-spacing: 4px;
    }
    .high-f { border-left: 6px solid #ff4b4b; }
    .high-f .freq-label { color: #ff4b4b; }
    .mid-f { border-left: 6px solid #f9d423; }
    .mid-f .freq-label { color: #f9d423; }
    .zero-f { border-left: 6px solid #6c757d; opacity: 0.6; }
    .zero-f .freq-label { color: #aaa; }
    .zero-f .num-display { color: #888; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ 坦克数据频率演算大屏")
st.markdown("---")

# --- 1. 扫描文件 (模糊匹配逻辑) ---
all_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
data_map = {}

for f in all_files:
    fname = f.lower()
    # 只要名字里带这些词，就强行分类
    if "ssq" in fname or "双色球" in fname:
        data_map["🔴 双色球核心数据"] = f
    elif "dlt" in fname or "data" in fname:
        data_map["🟢 大乐透核心数据"] = f

if not data_map:
    # 如果还是找不到，列出文件夹里所有CSV让用户自己选
    if all_files:
        for f in all_files: data_map[f"未知文件: {f}"] = f
    else:
        st.error("🚨 文件夹里真的没有 CSV 文件！请确认上传到了 stat_tank 文件夹。")

if data_map:
    with st.sidebar:
        st.header("📊 控制台")
        display_name = st.selectbox("🎯 切换彩种数据：", list(data_map.keys()))
        num_p = st.sidebar.number_input("📉 统计最近期数：", value=50, min_value=1)
        st.markdown("---")
        st.write("已成功适配长文件名读取逻辑")

    target_file = data_map[display_name]
    
    try:
        # 使用碎石机模式读取
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        is_ssq = "🔴" in display_name
        ball_count = 6 if is_ssq else 5
        max_val = 33 if is_ssq else 35
        
        all_balls = []
        count_lines = 0
        for line in lines[2:]:
            if count_lines >= num_p: break
            raw_numbers = re.findall(r'\d+', line)
            row_numbers = [int(n) for n in raw_numbers if 1 <= int(n) <= max_val]
            if len(row_numbers) >= ball_count:
                all_balls.extend(row_numbers[:ball_count])
                count_lines += 1

        # --- 2. 炫酷展示 ---
        counts = Counter(all_balls)
        if counts:
            st.markdown(f"### 📡 正在演算：<span style='color:#00f2fe'>{display_name}</span> | <span style='color:#00f2fe'>{count_lines}</span> 期样本", unsafe_allow_html=True)
            
            max_f = max(counts.values())
            for f in range(max_f, -1, -1):
                nums = sorted([i for i in range(1, max_val + 1) if counts.get(i, 0) == f])
                if not nums: continue
                
                nums_str = " ".join([f"{x:02d}" for x in nums])
                
                # 样式判断
                if f >= 5: style_class = "high-f"
                elif f == 0: style_class = "zero-f"
                else: style_class = "mid-f"
                
                st.markdown(f"""
                    <div class="freq-card {style_class}">
                        <div class="freq-label">{f} 次出现</div>
                        <div class="num-display">{nums_str}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ 该文件内未提取到有效号码。")
    except Exception as e:
        st.error(f"解析出错：{e}")
