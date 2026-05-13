import streamlit as st
import pandas as pd
from collections import Counter
import os
import re

# 1. 顶级配置
st.set_page_config(page_title="指挥官专用数据终端", layout="wide")

# --- 🚀 纯黑金沉浸式 UI 装修 ---
st.markdown("""
    <style>
    /* 1. 强制主背景 */
    .stApp {
        background: radial-gradient(circle, #1b2735 0%, #090a0f 100%);
        color: #ffffff;
    }
    
    /* 2. 彻底改造左侧面板 */
    [data-testid="stSidebar"] {
        background: rgba(10, 10, 20, 0.95) !important;
        border-right: 2px solid #333;
        box-shadow: 10px 0 30px rgba(0,0,0,0.5);
    }
    
    /* 3. 侧边栏内的文字和组件 */
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: #00d2ff;
        font-family: "Microsoft YaHei";
        text-shadow: 0 0 10px rgba(0,210,255,0.5);
        border-bottom: 2px solid #00d2ff;
        padding-bottom: 10px;
    }
    
    /* 4. 频率卡片 - 尊享金属质感 */
    .freq-box {
        background: linear-gradient(145deg, #16213e, #0f3460);
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 8px 8px 20px #05050a, -2px -2px 10px rgba(255,255,255,0.05);
        display: flex;
        align-items: center;
    }
    
    /* 5. 频率数字 */
    .f-label {
        font-size: 1.8rem;
        font-weight: 900;
        color: #f9d423; /* 黄金色 */
        min-width: 150px;
        text-align: center;
        border-right: 3px solid rgba(255,255,255,0.1);
    }
    
    /* 6. 号码球效果 */
    .ball {
        background: radial-gradient(circle at 30% 30%, #00f2fe, #0077be);
        color: white;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 1.3rem;
        margin: 0 8px;
        box-shadow: 0 5px 15px rgba(0,242,254,0.4);
        border: 2px solid #ffffff;
    }
    
    .hot { border-left: 10px solid #ff416c; }
    .cold { border-left: 10px solid #485563; opacity: 0.5; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 文件强行识别与汉化 ---
all_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
menu_data = {}

for f in all_files:
    # 模糊识别
    if "ssq" in f.lower() or "双色球" in f:
        menu_data["🔴 双色球·大数据分析中心"] = f
    elif "dlt" in f.lower() or "data" in f:
        menu_data["🟢 大乐透·大数据分析中心"] = f
    else:
        menu_data[f"📂 其它数据: {f}"] = f

# --- 3. 侧边栏布局 ---
with st.sidebar:
    st.markdown("## 坦克指挥控制台")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 这里是您要的中文选项
    select_label = st.selectbox("🛸 切换演算频道", list(menu_data.keys()))
    target_csv = menu_data[select_label]
    
    num_p = st.slider("📅 深度扫描期数", 5, 200, 50)
    st.markdown("---")
    st.write("🔧 系统状态: 极佳")
    st.write("🛡️ 加固逻辑: 碎石机3.0版")

# --- 4. 主演算逻辑 ---
st.markdown(f"### 🚀 当前正在执行：{select_label}")

try:
    with open(target_csv, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    is_ssq = "双色球" in select_label
    balls_limit = 6 if is_ssq else 5
    max_num = 33 if is_ssq else 35
    
    # 暴力提取
    data_pool = []
    processed_count = 0
    for line in lines[2:]:
        if processed_count >= num_p: break
        nums = [int(n) for n in re.findall(r'\d+', line) if 1 <= int(n) <= max_num]
        if len(nums) >= balls_limit:
            data_pool.extend(nums[:balls_limit])
            processed_count += 1

    counts = Counter(data_pool)
    if counts:
        # 按照出现次数从高到低展示
        for f in range(max(counts.values()), -1, -1):
            target_list = sorted([i for i in range(1, max_num + 1) if counts.get(i, 0) == f])
            if not target_list: continue
            
            box_class = "hot" if f >= 5 else ("cold" if f == 0 else "")
            balls_html = "".join([f'<div class="ball">{n:02d}</div>' for n in target_list])
            
            st.markdown(f"""
                <div class="freq-box {box_class}">
                    <div class="f-label">{f} 次出现</div>
                    <div style="display: flex; flex-wrap: wrap;">{balls_html}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("数据扫描完毕，未发现有效号码。")

except Exception as e:
    st.error(f"终端运行异常: {e}")
