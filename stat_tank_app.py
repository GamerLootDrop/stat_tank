import streamlit as st
import pandas as pd
from collections import Counter
import os
import re

# 设置页面：加入自定义 CSS 样式
st.set_page_config(page_title="坦克频率分析终端", layout="wide")

# --- 🚀 豪华装修 CSS ---
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stApp {
        background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
        color: #ffffff;
    }
    .freq-card {
        background: rgba(255, 255, 255, 0.05);
        border-left: 5px solid #ff4b4b;
        padding: 15px 25px;
        margin-bottom: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
    }
    .freq-label {
        font-size: 1.2rem;
        font-weight: bold;
        min-width: 100px;
        color: #ff4b4b;
    }
    .num-display {
        font-family: 'Courier New', monospace;
        font-size: 24px;
        font-weight: 900;
        letter-spacing: 5px;
        color: #00ffcc;
        margin-left: 30px;
    }
    .zero-freq { border-left: 5px solid #6c757d; }
    .zero-freq .freq-label { color: #aaa; }
    .zero-freq .num-display { color: #6c757d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ 坦克频率实时演算大屏")
st.markdown("---")

# --- 1. 扫描文件并汉化 ---
all_files = os.listdir('.')
data_map = {}
for f in all_files:
    if f.lower().endswith('.csv'):
        if "ssq" in f.lower() or "双色球" in f:
            data_map["🔴 双色球数据终端"] = f
        elif "dlt" in f.lower() or "data" in f:
            data_map["🟢 大乐透数据终端"] = f

if not data_map:
    st.error("🚨 找不着弹药（CSV文件）！请确认已上传到 stat_tank 文件夹。")
else:
    # 2. 侧边栏：美化配置
    with st.sidebar:
        st.header("📊 控制台")
        display_name = st.selectbox("🎯 切换彩种：", list(data_map.keys()))
        num_p = st.number_input("📉 统计最近期数：", value=50, min_value=1)
        st.markdown("---")
        st.info("提示：系统已自动去除小数点及乱码。")

    target_file = data_map[display_name]
    
    try:
        # 使用碎石机模式提取数据
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        is_ssq = "双色球" in display_name
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

        # --- 3. 结果展示 ---
        counts = Counter(all_balls)
        if counts:
            st.write(f"正在分析：{display_name} | 期数规模：{count_lines}期")
            
            # 按频率从高到低排列
            max_f = max(counts.values())
            for f in range(max_f, -1, -1):
                nums = sorted([i for i in range(1, max_val + 1) if counts.get(i, 0) == f])
                if not nums: continue
                
                nums_str = " ".join([f"{x:02d}" for x in nums])
                
                # 区分高频、中频、遗漏样式
                card_class = "freq-card"
                if f == 0: card_class += " zero-freq"
                
                st.markdown(f"""
                    <div class="{card_class}">
                        <div class="freq-label">{f} 次出现</div>
                        <div class="num-display">{nums_str}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            if st.button("📸 记录当前快照"):
                st.balloons()
        else:
            st.warning("⚠️ 数据源为空，请检查文件内容。")

    except Exception as e:
        st.error(f"解析出错：{e}")
