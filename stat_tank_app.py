import streamlit as st
import pandas as pd
from collections import Counter

st.set_page_config(page_title="数据频率演算终端", layout="wide")
st.title("📊 大数据频率深度过滤器 (实操版)")

# --- 1. 手动进水口 ---
st.info("💡 广琦老师，由于云端访问官网受限，请在下方贴入最近几期的号码，演算即刻开始！")
raw_input = st.text_area("👉 请在此贴入开奖号码 (每期一行，红球即可)", 
                         placeholder="05 12 18 26 31\n02 08 15 22 29\n...",
                         height=200)

# --- 2. 核心演算逻辑 ---
if raw_input:
    # 把您贴进来的文字变成数据
    try:
        lines = [line.strip() for line in raw_input.split('\n') if line.strip()]
        all_nums = []
        for l in lines:
            all_nums.extend([int(n) for n in l.split() if n.isdigit()])
        
        if all_nums:
            st.success(f"✅ 已成功载入 {len(lines)} 期数据，正在演算频率...")
            counts = Counter(all_nums)
            
            # 分组展示
            mapping = {}
            for i in range(1, 36):
                c = counts.get(i, 0)
                mapping.setdefault(c, []).append(i)
            
            # 倒序显示红框
            for f in sorted(mapping.keys(), reverse=True):
                nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
                color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
                st.markdown(f"""
                <div style="display:flex;align-items:center;margin-bottom:10px;">
                    <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:80px;text-align:center;">{f} 次</div>
                    <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
                </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"格式好像不太对，请检查：{e}")
else:
    st.warning("👈 请先在上面框里贴点开奖号，我就能为您分析啦！")
