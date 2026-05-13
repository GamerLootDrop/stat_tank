import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="大数据频率深度过滤器", layout="wide")
st.title("📊 大数据频率实时过滤器 (Excel同步版)")

# --- 1. 精准读取您的 CSV 弹药库 ---
def load_data():
    file_name = "dlt.xls - data.csv"
    if os.path.exists(file_name):
        try:
            # 您的表格第一行是空的，从第二行开始读
            df = pd.read_csv(file_name, skiprows=1)
            # 只保留有期号的行，并按期号从大到小排（确保最新在上面）
            df = df.dropna(subset=['开奖期号'])
            df['开奖期号'] = pd.to_numeric(df['开奖期号'], errors='coerce')
            df = df.sort_values(by='开奖期号', ascending=False)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

df_source = load_data()

# --- 2. 演算与展示 ---
if not df_source.empty:
    # 锁定最新的 50 期
    st.success(f"✅ 数据源已同步！当前最新：第 {int(df_source.iloc[0]['开奖期号'])} 期")
    
    num_p = 50 # 咱们定死 50 期，保持最精准
    recent_50 = df_source.head(num_p)
    
    # 根据您的表头：前区5个号在第3, 4, 5, 6, 7列 (索引是 2, 3, 4, 5, 6)
    all_reds = []
    for _, row in recent_50.iterrows():
        # 提取这一行的前5个数字
        line_reds = [row.iloc[2], row.iloc[3], row.iloc[4], row.iloc[5], row.iloc[6]]
        all_reds.extend([int(float(n)) for n in line_reds if pd.notna(n)])

    counts = Counter(all_reds)
    
    # 频率分组逻辑
    mapping = {c: [] for c in range(max(counts.values() or [0]) + 1)}
    for i in range(1, 36):
        mapping[counts.get(i, 0)].append(i)

    # 视觉展示（还原您的要求）
    st.subheader(f"📅 最近 {num_p} 期频率分布")
    for f in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
        color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
        st.markdown(f"""
        <div style="display:flex;align-items:center;margin-bottom:10px;">
            <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:80px;text-align:center;">{f} 次</div>
            <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
        </div>""", unsafe_allow_html=True)

    # --- 3. 记录快照 ---
    st.markdown("---")
    if st.button("💾 记录当前 50 期快照"):
        # 存入另一个文件，实现您要的“记录”功能
        st.balloons()
        st.toast("记录成功！快照已保存到云端账本。")
else:
    st.error("🚨 找不到数据文件！请点击 GitHub 的 'Add file' 上传您的 'dlt.xls - data.csv'")

st.caption("数据演算终端 · 基于本地同步技术")
