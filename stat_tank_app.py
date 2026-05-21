import streamlit as st
import pandas as pd
from collections import Counter
import math
import os
import random
import requests
from bs4 import BeautifulSoup
import time  # 引入时间戳，用来击穿网站的反爬缓存
import re
import itertools
import base64
import json

# ==========================================
# 0. 百度 AI 视觉大脑 (OCR) 接口配置
# ==========================================
BAIDU_API_KEY = "F6lfslP94zn49B90NXSv5NhV"
BAIDU_SECRET_KEY = "589HERNjnrxX17w4CKdqMVUrJeKGRryR"

def get_baidu_token(api_key, secret_key):
    """获取百度AI的通行令牌"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try:
        res = requests.post(url, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=5)
        return res.json().get("access_token")
    except Exception:
        return None

def baidu_ocr(image_bytes, token):
    """调用百度网络图片文字识别提取文本"""
    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/webimage?access_token=" + token
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    # 转换为 Base64 编码
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')
    data = {'image': img_b64}
    
    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            words_result = result.get('words_result', [])
            return [item.get('words') for item in words_result if item.get('words')]
    except Exception:
        pass
    return []


# ==========================================
# 1. 网页样式与核心数据爬虫层
# ==========================================

st.set_page_config(
    page_title="坦克战略指挥部-高维热力版",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入极客黑钢高精UI皮肤（适配移动端与大屏）
st.markdown("""
<style>
    /* 全局背景暗黑风 */
    .stApp {
        background-color: #0B0F19;
        color: #E2E8F0;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
    
    /* 强力隐藏 Streamlit 默认的白边和顶部 */
    [data-testid="stHeader"] {display: none;}
    .block-container {padding-top: 2rem !important; padding-bottom: 2rem !important;}
    
    /* 大标题立体科幻效果 */
    h1 {
        text-shadow: 0 0 12px rgba(255, 75, 43, 0.4);
        font-size: 2.2rem !important;
    }
    
    /* 容器控制台皮肤 */
    div[data-testid="stVerticalBlock"] > div {
        background: #111827;
        border-radius: 12px;
        padding: 6px;
        border: 1px solid #1F2937;
        margin-bottom: 5px;
    }
    
    /* 侧边栏样式重写 */
    [data-testid="stSidebar"] {
        background-color: #0d1321 !important;
        border-right: 1px solid #1F2937;
    }
    
    /* 自定义高能按钮 */
    .stButton>button {
        background: linear-gradient(135deg, #FF4B2B 0%, #FF416C 100%);
        color: white !important;
        border: none;
        padding: 8px 20px;
        border-radius: 6px;
        font-weight: bold;
        transition: all 0.3s ease;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255, 75, 43, 0.4);
    }
    
    /* =======================================
       🔥 核心展示组件：球体、数字矩阵、频次条
       ======================================= */
    
    .ball-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 5px;
    }
    .ball {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 15px;
        color: white;
        user-select: none;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    .ball-red { background: radial-gradient(circle at 10px 10px, #FF4B2B, #B31217); box-shadow: 0 0 6px rgba(255, 75, 43, 0.5); }
    .ball-blue { background: radial-gradient(circle at 10px 10px, #6FB1FC, #0052D4); box-shadow: 0 0 6px rgba(0, 82, 212, 0.5); }
    .ball-yellow { background: radial-gradient(circle at 10px 10px, #FFD700, #F39C12); color: #333; text-shadow: none; box-shadow: 0 0 6px rgba(243, 156, 18, 0.5); }

    /* 频次横条在手机和电脑上都能自适应紧凑排列 */
    .freq-tag {
        background-color: #2b2b2b; color: #00E676; padding: 4px 8px;
        border-radius: 5px; font-weight: bold; margin-right: 10px;
        border-left: 4px solid #00E676; min-width: 65px; text-align: center; font-size: 13px;
    }
    .stat-row { display: flex; align-items: center; margin-bottom: 8px; background: #1E1E1E; padding: 8px; border-radius: 8px;}
    .filter-box { background: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-bottom: 12px;}

    /* 彻底封死顶部区域 */
    [data-testid="stHeader"], .stApp > header { display: none !important; pointer-events: none !important; height: 0px !important; }
    #MainMenu, footer, .stDeployButton, .stAppDeployButton, [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }

    .ratio-badge { background-color: #262626; border: 1px solid #444; padding: 6px 12px; border-radius: 6px; font-weight: bold; text-align: center; font-size: 14px; flex: 1;}
</style>
""", unsafe_allow_html=True)


# 页面头部文案
st.markdown("<h1 style='text-align: center; color: #FF4B2B; margin-top: 10px;'>🚀 坦克战略指挥部</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888;'>此系统为内部绝密版本，未授权人员请立即退出。</p>", unsafe_allow_html=True)

# -------------------------
# 数据层功能
# -------------------------
@st.cache_data(ttl=600)  # 缓存10分钟，避免高频请求导致被502封禁
def fetch_lottery_data(game_type="ssq", limit=100):
    """从公共接口拉取最新的双色球或大乐透历史开奖数据(带防缓存机制)"""
    timestamp = int(time.time())
    if game_type == "ssq":
        url = f"https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize={limit}&pageNo=1&_={timestamp}"
    else:
        url = f"https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize={limit}&pageNo=1&_={timestamp}"
        
    try:
        # 伪造全套高级浏览器请求头防止反爬劫持
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.sporttery.cn/"
        }
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            list_data = data.get("value", {}).get("list", [])
            parsed_rows = []
            for item in list_data:
                term = item.get("lotteryDrawNum", "")
                result_str = item.get("lotteryDrawResult", "")
                if term and result_str:
                    all_balls = result_str.split(" ")
                    if len(all_balls) >= 7:
                        if game_type == "dlt":
                            front = all_balls[:5]
                            back = all_balls[5:7]
                        else:
                            # 模拟兼容双色球格式转换
                            front = all_balls[:6]
                            back = all_balls[6:7]
                        parsed_rows.append([term] + front + back)
            if parsed_rows:
                return pd.DataFrame(parsed_rows)
    except Exception:
        pass
        
    # 备用方案：若官方网网络断开，尝试备用爬虫引擎抓取50彩票网
    try:
        url_back = f"http://kaijiang.500.com/shtml/{game_type}/20000.shtml?_={timestamp}"
        res_back = requests.get(url_back, timeout=5)
        res_back.encoding = "gb2312"
        soup = BeautifulSoup(res_back.text, "html.parser")
        
        # 针对 500彩票网的特殊解析，需要过滤掉多余的日期等字符
        tr_list = soup.find_all("tr")
        parsed_rows = []
        for tr in tr_list:
            tds = tr.find_all("td")
            if len(tds) >= 8:
                txt = tds[0].text.strip()
                # 判断这行是否是合法的期号（纯数字）
                if txt.isdigit() and len(txt) >= 5:
                    # 尝试从这行中提取所有球号（要求也是纯数字）
                    balls = []
                    for td in tds[1:]:
                        b_txt = td.text.strip()
                        if b_txt.isdigit() and len(b_txt) <= 2:
                             balls.append(b_txt)
                        # 防止把奖金等后面的大数字也加进来，最多取7个
                        if len(balls) == 7:
                            break
                    if len(balls) == 7:
                        parsed_rows.append([txt] + balls)
        if parsed_rows:
            return pd.DataFrame(parsed_rows)
    except Exception:
        pass
        
    return None

def clean_excel_data(df, is_dlt=False):
    """
    全自动数据清洗引擎：
    不看行头，不要列名，自动锁定包含开奖号码的核心区域！
    兼容任何用户的杂乱表格。
    """
    valid_rows = []
    # 强制将所有数据转为字符串以便正则匹配
    df = df.astype(str)
    
    required_len = 7 if is_dlt else 7  # 都是前区+后区共7个球
    front_max = 35 if is_dlt else 33
    back_max = 12 if is_dlt else 16
    front_count = 5 if is_dlt else 6
    back_count = 2 if is_dlt else 1

    for idx, row in df.iterrows():
        nums = []
        for cell in row:
            # 删掉所有非数字字符（比如空格、汉字、小数点）
            cleaned = re.sub(r'\D', '', cell)  
            
            # 过滤掉像“期号”这种特别长的数字，还有日期等
            # 开奖号码通常是 1-2 位数字
            if cleaned and len(cleaned) <= 2:
                try:
                    val = int(cleaned)
                    nums.append(val)
                except:
                    pass
        
        # 检查这行是不是包含了一整期的数据（至少要包含7个球）
        if len(nums) >= required_len:
            # 取这行的最后 required_len 个数字作为当期开奖号
            potential_balls = nums[-required_len:]
            front_part = potential_balls[:front_count]
            back_part = potential_balls[front_count:]
            
            # 校验数字范围是否完全合规
            if all(1 <= x <= front_max for x in front_part) and all(1 <= x <= back_max for x in back_part):
                # 校验前区是否包含重复数字（正常开奖不可能重复）
                if len(set(front_part)) == front_count:
                    # 格式化存入
                    valid_rows.append([str(x).zfill(2) for x in potential_balls])
                    
    if len(valid_rows) == 0:
        return None
        
    # 转换回DataFrame格式给后续使用
    return pd.DataFrame(valid_rows)


# ==========================================
# 2. 战术分析核心算法层
# ==========================================

def calculate_bets(n, r):
    """快速计算组合数 (nCr)"""
    if r > n or r < 0: return 0
    return math.comb(n, r)

def parse_ocr_text_to_numbers(words_list, is_dlt=False):
    """
    智能AI大脑解析：
    从百度OCR识别出的散乱字符串列表中，提取出符合彩种范围的干净数字。
    """
    all_nums = []
    for word in words_list:
        # 使用正则把所有连续数字提取出来
        found = re.findall(r'\d+', word)
        for num_str in found:
            val = int(num_str)
            # 过滤掉非常离谱的大数字（如日期、期号）
            if 1 <= val <= 35:
                all_nums.append(val)
                
    # 去重并排序
    valid_nums = sorted(list(set(all_nums)))
    max_front = 35 if is_dlt else 33
    
    # 按照彩种强行分割为前后区数字
    front_balls = [x for x in valid_nums if 1 <= x <= max_front]
    back_balls = [x for x in valid_nums if 1 <= x <= (12 if is_dlt else 16)]
    
    return front_balls, back_balls

def render_balls(counts_dict, ball_class):
    """生成带有频次分层的高亮HTML排版 (支持暗黑风)"""
    if not counts_dict:
        return "<p style='color:#666;'>暂无分析数据</p>"
        
    # 按出现频次从大到小倒序排列
    sorted_items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
    
    # 将相同频次的球归类到一起展示
    grouped = {}
    for num, freq in sorted_items:
        if freq not in grouped:
            grouped[freq] = []
        grouped[freq].append(num)
        
    html_str = ""
    for freq, nums in grouped.items():
        nums_sorted = sorted(nums)
        balls_html = "".join([f"<div class='ball {ball_class}'>{str(x).zfill(2)}</div>" for x in nums_sorted])
        html_str += f"<div class='stat-row'><div class='freq-tag'>{freq} 次</div><div class='ball-container' style='margin-bottom:0;'>{balls_html}</div></div>"
    return html_str

# ==========================================
# 3. 侧边栏与数据初始化
# ==========================================
with st.sidebar:
    st.markdown("### 🛠️ 战略基本配置")
    game_mode = st.radio("📡 选择当前推演彩种", ["超级大乐透 🟢", "双色球 🔴"])
    is_dlt = "超级大乐透" in game_mode
    
    st.markdown("---")
    data_source_mode = st.radio("📥 数据载入渠道", ["本地Excel文件投喂 (推荐)", "智能网络自动拉取"])
    
    source = None
    if "本地Excel文件" in data_source_mode:
        uploaded_file = st.file_uploader("临时投喂本地开奖文件", type=['csv', 'xls', 'xlsx'])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    source = pd.read_csv(uploaded_file, header=None, dtype=str)
                else:
                    source = pd.read_excel(uploaded_file, header=None, dtype=str)
                st.success("🎯 战术开奖包投喂成功！")
            except Exception as e:
                st.error(f"❌ 载入失败，请检查文件: {e}")
        else:
            # 为了防止初次进入报错，默认提供占位提示
            st.info("👈 请在上方选择本地号码记录表")
            
    else:
        # 网络爬虫模式
        with st.spinner("正在呼叫总台爬取最新数据..."):
            limit = st.slider("抓取期数", min_value=10, max_value=200, value=50, step=10)
            source = fetch_lottery_data("dlt" if is_dlt else "ssq", limit=limit)
        if source is not None:
            st.success(f"📡 成功对接云端最新 {len(source)} 期数据！")
        else:
            st.error("⚠️ 云端网络阻塞或反爬被拦截，请尝试刷新或改用本地文件投喂！")


# ==========================================
# 4. 主面板展示核心层
# ==========================================
if source is not None:
    # 激活全自动清洗引擎
    cleaned_df = clean_excel_data(source, is_dlt=is_dlt)
    
    if cleaned_df is None:
        st.error("🚨 战略库解析失败！上传的文件内找不到连续7个数字的合规开奖记录，请检查文件。")
    else:
        # 分离前后区并进行数据统计
        f_len = 5 if is_dlt else 6
        df_front = cleaned_df.iloc[:, :f_len]
        df_back = cleaned_df.iloc[:, f_len:7]
        
        # 将表格数据压平为列表
        list_front = [int(x) for x in df_front.values.flatten().tolist()]
        list_back = [int(x) for x in df_back.values.flatten().tolist()]
        
        # 统计频次
        counts_red = dict(Counter(list_front))
        counts_blue = dict(Counter(list_back))
        
        # 计算总体大样本排序
        sorted_red = sorted(counts_red.items(), key=lambda x: x[1], reverse=True)
        sorted_blue = sorted(counts_blue.items(), key=lambda x: x[1], reverse=True)
        
        
        # -------------------------
        # 大盘核心：多维热力矩阵选号盘
        # -------------------------
        st.markdown("### 📊 大众玩家多维热力热度选号矩阵")
        
        # 动态计算热力颜色函数
        def get_heat_color(ball_num, count_dict, is_blue_ball=False):
            freq = count_dict.get(ball_num, 0)
            if freq == 0:
                return "#1e293b" # 盲区冷号（高级深灰）
            else:
                max_freq = max(count_dict.values()) if count_dict else 1
                ratio = freq / max_freq
                if not is_blue_ball:
                    # 红球热力：根据占比从浅橘红到深血红
                    if ratio > 0.7: return "#B31217" # 爆热（深血红）
                    elif ratio > 0.4: return "#FF4B2B" # 炽热（火红）
                    else: return "#FF8A75" # 温热（浅红）
                else:
                    # 蓝球热力：从浅蓝到深海蓝
                    if ratio > 0.7: return "#002266" # 爆热蓝
                    elif ratio > 0.4: return "#0052D4" # 炽热蓝
                    else: return "#64B5F6" # 温热蓝

        tc1, tc2 = st.columns(2)
        with tc1:
            st.markdown("#### 🔴 前区红球大众热力选号矩阵")
            max_red_num = 35 if is_dlt else 33
            html_red_matrix = "<div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; max-width: 450px;'>"
            for i in range(1, max_red_num + 1):
                freq = counts_red.get(i, 0)
                bg_color = get_heat_color(i, counts_red, is_blue_ball=False)
                border_style = "border: 2px solid #FF4B2B;" if freq > 0 else "border: 1px solid #475569;"
                html_red_matrix += f"<div style='background:{bg_color}; {border_style} border-radius:6px; padding:8px 4px; text-align:center; color:white;'><b style='font-size:15px;'>{str(i).zfill(2)}</b><br><span style='font-size:11px; opacity:0.85;'>{freq}次</span></div>"
            html_red_matrix += "</div>"
            st.markdown(html_red_matrix, unsafe_allow_html=True)
            
        with tc2:
            st.markdown("#### 🔵 后区蓝球大众热力选号矩阵")
            max_blue_num = 12 if is_dlt else 16
            html_blue_matrix = "<div style='display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; max-width: 450px;'>"
            for i in range(1, max_blue_num + 1):
                freq = counts_blue.get(i, 0)
                bg_color = get_heat_color(i, counts_blue, is_blue_ball=True)
                border_style = "border: 2px solid #0052D4;" if freq > 0 else "border: 1px solid #475569;"
                html_blue_matrix += f"<div style='background:{bg_color}; {border_style} border-radius:6px; padding:8px 4px; text-align:center; color:white;'><b style='font-size:15px;'>{str(i).zfill(2)}</b><br><span style='font-size:11px; opacity:0.85;'>{freq}次</span></div>"
            html_blue_matrix += "</div>"
            st.markdown(html_blue_matrix, unsafe_allow_html=True)

        # -------------------------
        # AI 视觉大脑辅助输入模块 (OCR)
        # -------------------------
        st.markdown("---")
        st.markdown("### 👁️ AI 视觉大脑辅助输入（可选项）")
        st.info("💡 如果你有灵感号码，或者手里有现成红球的截图，可以直接上传！系统将自动提取里面的数字注入冷号盲区进行优先组合！")
        
        ocr_image = st.file_uploader("📸 拍照或选择灵感号码图片（支持截图、手写等）", type=['png', 'jpg', 'jpeg'])
        ocr_front_balls, ocr_back_balls = [], []
        
        if ocr_image is not None:
            with st.spinner("🧠 正在调用百度AI视觉大脑进行高精准文字识别..."):
                img_bytes = ocr_image.read()
                token = get_baidu_token(BAIDU_API_KEY, BAIDU_SECRET_KEY)
                if token:
                    words = baidu_ocr(img_bytes, token)
                    if words:
                        ocr_front_balls, ocr_back_balls = parse_ocr_text_to_numbers(words, is_dlt=is_dlt)
                        if ocr_front_balls:
                            st.success(f"🎯 AI 视觉大脑识别成功！提取到灵感红球: {ocr_front_balls}")
                        else:
                            st.warning("⚠️ 提取成功但未在图片里识别出符合范围的数字，请确保图片字迹清晰。")
                    else:
                        st.error("❌ 未从图片中识别到清晰文字。")
                else:
                    st.error("❌ 百度 AI 鉴权令牌获取失败，请检查网络或 API Key 是否正确。")
                    

        # 划定红球炮灰区 (取热度最高的前6个)
        hot_nums = [x[0] for x in sorted_red[:6]]

        # 划定红球潜伏区 (频次为0的球)
        all_possible_reds = list(range(1, 36 if is_dlt else 34))
        potential_nums = [x for x in all_possible_reds if counts_red.get(x, 0) == 0]

        # 注入 AI 识别到的灵感球进入潜伏优先队列
        if ocr_front_balls:
            potential_nums = list(set(ocr_front_balls + potential_nums))

        st.markdown("---")
        st.markdown("### 🎛️ 坦克三段式热力动态过滤罗盘")

        # 将动态合并的数据池传入过滤面板
        dan_source = [x for x in potential_nums if x not in hot_nums]
        if len(dan_source) < 5:
            # 如果极端情况下冷号不足，拿温热号来补，优先拿较冷的
            all_remaining = [x[0] for x in sorted_red[::-1] if x[0] not in hot_nums]
            dan_source = list(set(dan_source + all_remaining))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔥 大热炮灰区（强烈拦截、严禁选作胆码）")
            st.markdown("<div class='filter-box' style='border-color:#FF4B2B;'>", unsafe_allow_html=True)
            hot_str = " ".join([f"<span class='ball ball-red' style='display:inline-flex;margin:2px;'>{str(x).zfill(2)}</span>" for x in hot_nums])
            st.markdown(hot_str, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("#### 🍀 盲区潜伏区（主力选号池、冷门突袭）")
            st.markdown("<div class='filter-box' style='border-color:#00E676;'>", unsafe_allow_html=True)
            potential_nums_sorted = sorted(potential_nums)
            pot_str = " ".join([f"<span class='ball ball-yellow' style='display:inline-flex;margin:2px;color:#111;'>{str(x).zfill(2)}</span>" for x in potential_nums_sorted[:15]])
            st.markdown(pot_str + ("..." if len(potential_nums)>15 else ""), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # 增加一档展示：0次频段冷号直接作为独立组合策略展示
        # ----------------------------------------------------
        zero_freq_nums = [x for x in all_possible_reds if counts_red.get(x, 0) == 0]
        if zero_freq_nums:
            z_str = " ".join([str(x).zfill(2) for x in sorted(zero_freq_nums)])
            z_count = len(zero_freq_nums)
            req_balls = 5 if is_dlt else 6
            if z_count >= req_balls:
                z_bets = calculate_bets(z_count, req_balls)
                offset_str = f"🎯 **【特种突击策略】**：当前盲区共有 {z_count} 个绝对冷号（**{z_str}**）。若它们内部直接成号，总共仅有 **{z_bets}** 注组合！"
            else:
                offset_str = f"🎯 **【特种突击策略】**：当前盲区仅有 {z_count} 个冷号（不足{req_balls}个，必须搭配温热号）。"
            
            st.markdown(f"<div style='background:#2b2b2b; padding:15px; border-radius:10px; text-align:center;'>{offset_str}</div>", unsafe_allow_html=True)


        # ----------------------------------------------------
        # 精准分流：依据彩种展示各种组合策略
        # ----------------------------------------------------
        st.markdown("---")
        if is_dlt:
            # 大乐透：四胆全托 与 三胆全托 分别列出
            
            # 【策略1：四胆全托】
            d4_nums = (dan_source + [1, 2, 3, 4])[:4]
            d4_str = " ".join([str(x).zfill(2) for x in d4_nums])
            
            st.markdown("<div class='filter-box' style='border-color:#FFD700; background:#1b1b10;'>", unsafe_allow_html=True)
            st.markdown("#### 🌟 【策略一】超级大乐透 · 四胆全托（最少投入组合）")
            st.markdown(f"* **🎯 建议红球胆码**：<span style='color:#FFD700; font-weight:bold;'>{d4_str}</span> （系统优先从盲区冷号精选4个）", unsafe_allow_html=True)
            st.markdown(f"* **🚜 红球拖码**：包揽其余所有 **{35 - 4}** 个红球（全托）")
            st.markdown(f"* **📊 红球组合注数**：固定为 **31 注** 红球组合")
            st.markdown("* **💰 战术实战预算**：")
            st.markdown("  1. **后区精选组合**：若锁定后区2个心水蓝球 → **共 31 注 (62元)**")
            st.markdown("  2. **后区全托组合**：若后区12个蓝球也全包(66注) → **共 2,046 注 (4,092元)**")
            st.markdown("</div>", unsafe_allow_html=True)

            # 【策略2：三胆全托】
            d3_nums = (dan_source + [1, 2, 3])[:3]
            d3_str = " ".join([str(x).zfill(2) for x in d3_nums])
            
            st.markdown("<div class='filter-box' style='border-color:#FFD700; background:#101b1b;'>", unsafe_allow_html=True)
            st.markdown("#### 🌟 【策略二】超级大乐透 · 三胆全托（覆盖率较高组合）")
            st.markdown(f"* **🎯 建议红球胆码**：<span style='color:#FFD700; font-weight:bold;'>{d3_str}</span> （系统优先从盲区冷号精选3个）", unsafe_allow_html=True)
            st.markdown(f"* **🚜 红球拖码**：包揽其余所有 **{35 - 3}** 个红球（全托）")
            st.markdown(f"* **📊 红球组合注数**：固定为 **496 注** 红球组合")
            st.markdown("* **💰 战术实战预算**：")
            st.markdown("  1. **后区精选组合**：若锁定后区2个心水蓝球 → **共 496 注 (992元)**")
            st.markdown("  2. **后区全托组合**：若后区12个蓝球也全包(66注) → **共 32,736 注 (65,472元)**")
            st.markdown("</div>", unsafe_allow_html=True)
            
        else:
            # 双色球：五胆全托 单独列出
            d5_nums = (dan_source + [1, 2, 3, 4, 5])[:5]
            d5_str = " ".join([str(x).zfill(2) for x in d5_nums])
            
            st.markdown("<div class='filter-box' style='border-color:#FF4B2B; background:#1b1010;'>", unsafe_allow_html=True)
            st.markdown("#### 🌟 【独家定制】双色球 · 五胆全托红球组合（极限最少组合）")
            st.markdown(f"* **🎯 建议红球胆码**：<span style='color:#FF4B2B; font-weight:bold;'>{d5_str}</span> （系统优先从盲区冷号精选5个）", unsafe_allow_html=True)
            st.markdown(f"* **🚜 红球拖码**：包揽其余所有 **{33 - 5}** 个红球（全托）")
            st.markdown(f"* **📊 红球组合注数**：固定为 **28 注** 红球组合")
            st.markdown("* **💰 战术实战预算**：")
            st.markdown("  1. **后区精选组合**：若锁定后区1个心水蓝球 → **共 28 注 (56元)**")
            st.markdown("  2. **后区全托组合**：若后区16个蓝球全包(16注) → **共 448 注 (896元)**")
            st.markdown("</div>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # 4. 高级战术过滤罗盘：012路阻击阵地
        # ----------------------------------------------------
        st.markdown("### 📊 高级战术过滤罗盘：012路阻击阵地")
        
        # 按012路划分号码池（红球）
        max_r_num = 35 if is_dlt else 33
        f_0 = [x for x in range(1, max_r_num+1) if x % 3 == 0]
        f_1 = [x for x in range(1, max_r_num+1) if x % 3 == 1]
        f_2 = [x for x in range(1, max_r_num+1) if x % 3 == 2]

        max_b_num = 12 if is_dlt else 16
        b_0 = [x for x in range(1, max_b_num+1) if x % 3 == 0]
        b_1 = [x for x in range(1, max_b_num+1) if x % 3 == 1]
        b_2 = [x for x in range(1, max_b_num+1) if x % 3 == 2]

        st.markdown("#### 🔍 012路形态出号个数自定义配置（组合过滤核心）")
        
        col_f0, col_f1, col_f2 = st.columns(3)
        with col_f0:
            f_req_0 = st.number_input("🔴 前区 0 路球个数", min_value=0, max_value=f_len, value=2)
        with col_f1:
            f_req_1 = st.number_input("🔴 前区 1 路球个数", min_value=0, max_value=f_len, value=2)
        with col_f2:
            f_req_2 = st.number_input("🔴 前区 2 路球个数", min_value=0, max_value=f_len, value=1 if is_dlt else 2)

        col_b0, col_b1, col_b2 = st.columns(3)
        with col_b0:
            b_req_0 = st.number_input("🔵 后区 0 路球个数", min_value=0, max_value=2, value=1 if is_dlt else 0)
        with col_b1:
            b_req_1 = st.number_input("🔵 后区 1 路球个数", min_value=0, max_value=2, value=1 if is_dlt else 0)
        with col_b2:
            b_req_2 = st.number_input("🔵 后区 2 路球个数", min_value=0, max_value=2, value=0 if is_dlt else 1)

        # 动态验证形态总和
        req_f = 5 if is_dlt else 6
        req_b = 2 if is_dlt else 1
        sum_f = f_req_0 + f_req_1 + f_req_2
        sum_b = b_req_0 + b_req_1 + b_req_2

        if sum_f != req_f or sum_b != req_b:
            st.error("⚠️ **校验失败**：请确保前区和后区的012路设定总数正确！")
        else:
            total_filtered_bets = calculate_bets(len(f_0), f_req_0) * calculate_bets(len(f_1), f_req_1) * calculate_bets(len(f_2), f_req_2) * calculate_bets(len(b_0), b_req_0) * calculate_bets(len(b_1), b_req_1) * calculate_bets(len(b_2), b_req_2)
            st.success(f"🔥 形态验证成功：当前配置形态理论极限组合总数为 **{total_filtered_bets}** 注！")
