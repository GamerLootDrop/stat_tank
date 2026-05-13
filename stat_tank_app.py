import streamlit as st
import pandas as pd
from collections import Counter
import os
import re

# 1. 基础配置：深色主题沉浸式体验
st.set_page_config(page_title="坦克频率终端-尊享版", layout="wide")

# --- 🚀 顶级黑金 UI 装修 ---
st.markdown("""
    <style>
    /* 全局深色底色 */
    .stApp {
        background: #0a0a12;
        color: #e0e0e0;
    }
    
    /* 侧边栏彻底黑化美化 */
    [data-testid="stSidebar"] {
        background-color: #11111d !important;
        border-right: 1px solid #333;
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: #ffb400;
        text-align: center;
        border-bottom: 2px solid #ffb400;
        padding-bottom: 10px;
    }
    
    /* 核心频率卡片 */
    .freq-box {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #2e2e4a;
        box-shadow: 5px 5px 15px #05050a;
        display: flex;
        align-items: center;
    }
    
    /* 频率标签样式 */
    .f-label {
        font-size: 1.5rem;
        font-weight: 800;
        color: #ffb400;
        min-width: 130px;
        border-right: 2px solid #333;
        text-shadow: 0 0 10px rgba(255, 180, 0, 0.3);
    }
    
    /* 号码球样式 */
    .ball-row {
        padding-left: 25px;
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
    }
    .ball {
        background: #0f3460;
        color: #00fff2;
        border-radius: 50%;
        width: 45px;
        height: 45px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 1.2rem;
        border: 1px solid #00fff2;
        box-shadow: inset 0 0 10px rgba(0, 255, 242, 0.2);
    }
    
    /* 状态颜色 */
    .hot { border-left: 8px solid #ff4b4b; }
    .cold { border-left: 8px solid #4a4e69; opacity: 0.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心逻辑：强制汉化 ---
all_f = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
menu = {}

# 只要包含关键字，强制在菜单显示中文
for f in all_f:
    low_f = f.lower()
    if "ssq" in low_f or "双色球" in low_f:
        menu["🏆 双色球专业分析版"] = f
    elif "dlt" in low_f or "data" in low_f:
        menu["💎 大乐透专业分析版"] = f

# 如果都没对上，把剩下的文件也列出来，防止漏掉
for f in all_f:
    if f not in menu.values():
        menu[f"📂 未知数据: {f}"] = f

# --- 3. 侧边栏布局 ---
with st.sidebar:
    st.markdown("## 坦克指挥中心")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 强制中文下拉框
    choice = st.selectbox("🛸 切换演算频道", list(menu.keys()))
    current_file = menu[choice]
    
    num_p = st.slider("📅 统计期数深度", 5, 200, 50)
    
    st.markdown("---")
    st.write("📊 算法状态: 正常")
    st.write("📡 数据同步: 实时")

# --- 4. 主内容演算 ---
st.title(f"正在读取：{choice}")

try:
    with open(current_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    is_ssq = "双色球" in choice
    balls_needed = 6 if is_ssq else 5
    max_num = 33 if is_ssq else 35
    
    all_data = []
    processed = 0
    for line in lines[2:]:
        if processed >= num_p: break
        # 碎石机提取数字
        nums = [int(n) for n in re.findall(r'\d+', line) if 1 <= int(n) <= max_num]
        if len(nums) >= balls_needed:
            all_data.extend(nums[:balls_needed])
            processed += 1

    counts = Counter(all_data)
    if counts:
        max_f = max(counts.values())
        for f in range(max_f, -1, -1):
            target_nums = sorted([i for i in range(1, max_num + 1) if counts.get(i, 0) == f])
            if not target_nums: continue
            
            style_class = "hot" if f >= 5 else ("cold" if f == 0 else "")
            
            # 渲染卡片
            balls_html = "".join([f'<div class="ball">{n:02d}</div>' for n in target_nums])
            st.markdown(f"""
                <div class="freq-box {style_class}">
                    <div class="f-label">{f} 次出现</div>
                    <div class="ball-row">{balls_html}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("数据打捞失败，请检查 CSV 格式。")

except Exception as e:
    st.error(f"终端故障: {e}")
