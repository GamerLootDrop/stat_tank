import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="坦克频率终端", layout="wide")
st.title("🚀 坦克大数据频率过滤器 (终极版)")

# 1. 扫描所有文件
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]

if not csv_files:
    st.error("🚨 仓库文件夹里没看到 CSV 文件！请确认文件已上传。")
else:
    target = st.sidebar.selectbox("🎯 选择数据源", csv_files)
    
    try:
        # 强制读取
        df = pd.read_csv(target, skiprows=1)
        # 清理空行
        df = df.dropna(how='all').dropna(subset=[df.columns[0], df.columns[1]], how='all')
        
        # 自动识别：双色球还是大乐透
        is_ssq = "ssq" in target.lower() or "双色球" in target
        num_balls = 6 if is_ssq else 5
        max_val = 33 if is_ssq else 35
        
        st.sidebar.write(f"当前识别：{'双色球' if is_ssq else '大乐透'}")
        num_p = st.sidebar.number_input("统计期数", value=50, min_value=1)

        # 核心抓取：从第2或第3列开始找数字
        all_found = []
        subset = df.head(num_p)
        
        for _, row in subset.iterrows():
            row_vals = []
            # 扫描整行，只要是数字就拿走
            for item in row.values:
                try:
                    v = int(float(str(item).strip()))
                    if 1 <= v <= max_val:
                        row_vals.append(v)
                except: continue
            # 排除掉期号（期号通常很大），每行取最后出现的几个号或者特定位置
            # 这里优化为：取这一行里 1-35 之间的前几个有效数字
            all_found.extend(row_vals[-num_balls:] if is_ssq else row_vals[:5])

        # 统计
        counts = Counter(all_found)
        if not counts:
            st.warning("⚠️ 读到了文件，但没数出号码。请检查表格格子是否对齐。")
        else:
            # 绘图
            for f in sorted(set(counts.values()), reverse=True):
                nums = [i for i in range(1, max_val+1) if counts[i] == f]
                if nums:
                    nums_str = "  ".join([f"{x:02d}" for x in sorted(nums)])
                    color = "#FF4B4B" if f >= 5 else "#31333F"
                    st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:10px;"><div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:120px;text-align:center;">{f} 次出现</div><div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div></div>', unsafe_allow_html=True)
            
            # 显示遗漏（0次的）
            missing = [i for i in range(1, max_val+1) if counts[i] == 0]
            if missing:
                ms_str = "  ".join([f"{x:02d}" for x in sorted(missing)])
                st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:10px;"><div style="background-color:#9FA8DA;color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:120px;text-align:center;">0 次出现</div><div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{ms_str}</div></div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"出错啦：{e}")
