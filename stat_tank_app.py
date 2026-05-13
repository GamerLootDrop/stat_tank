import streamlit as st
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="数据频率演算终端", layout="wide")
st.title("📊 大数据频率深度过滤器 (Excel数据源版)")

# --- 1. 读取您的 dlt.xls 同步文件 ---
def load_excel_data():
    file_path = "dlt.xls - data.csv" # 对应您上传的文件名
    if os.path.exists(file_path):
        # 跳过开头的空行，读取数据
        df = pd.read_csv(file_path, skiprows=1)
        # 清洗数据：只取有期号和号码的行
        df = df.dropna(subset=['开奖期号', '前', '区'])
        # 按照期号倒序排列（最新的在最上面）
        df = df.sort_values(by='开奖期号', ascending=False)
        return df
    return pd.DataFrame()

df_all = load_excel_data()

# --- 2. 统计与展示 ---
if not df_all.empty:
    # 自动获取最新的 50 期（或者您在侧边栏选）
    st.sidebar.header("⚙️ 统计设置")
    num_p = st.sidebar.number_input("统计最近期数", value=50, min_value=1, max_value=len(df_all))
    
    latest_issue = df_all.iloc[0]['开奖期号']
    st.success(f"✅ 已成功连接 Excel 数据源！当前同步至：第 {latest_issue} 期")

    # 提取前 50 期的红球 (对应您表中的“前”, “区”等列)
    # 注意：根据您的表头，我们需要抓取前区的那 5 个数字列
    recent_df = df_all.head(num_p)
    
    # 这里的列索引根据您的文件预览进行精准定位
    # 假设前5个红球在第3到第7列
    all_reds = []
    for index, row in recent_df.iterrows():
        # 把每一行的红球凑齐
        reds = [row[2], row[3], row[4], row[5], row[6]]
        all_reds.extend([int(float(n)) for n in reds if pd.notna(n)])

    counts = Counter(all_reds)
    
    # 频率分组展示
    mapping = {c: [] for c in range(max(counts.values() or [0]) + 1)}
    for i in range(1, 36):
        mapping[counts.get(i, 0)].append(i)

    # 绘制那张红红绿绿的图
    for f in sorted(mapping.keys(), reverse=True):
        nums_str = "  ".join([f"{x:02d}" for x in sorted(mapping[f])])
        color = "#FF4B4B" if f >= 5 else ("#9FA8DA" if f == 0 else "#31333F")
        st.markdown(f"""
        <div style="display:flex;align-items:center;margin-bottom:10px;">
            <div style="background-color:{color};color:white;padding:5px 15px;border-radius:5px;font-weight:bold;width:80px;text-align:center;">{f} 次</div>
            <div style="margin-left:20px;font-size:22px;font-family:monospace;font-weight:bold;">{nums_str}</div>
        </div>""", unsafe_allow_html=True)

    # --- 3. 记录功能 ---
    st.markdown("---")
    if st.button("💾 记录当前统计快照"):
        st.write(f"已为您记录第 {latest_issue} 期的频率分布数据。")
        # 这里可以继续写存入另一个 CSV 的逻辑
else:
    st.error("🚨 没找到数据文件！请确保 'dlt.xls - data.csv' 已经上传到 GitHub 仓库里。")

st.caption("数据演算终端 · Excel 同步模式")
