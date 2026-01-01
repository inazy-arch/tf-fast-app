import streamlit as st
import datetime
import re
import base64
from PIL import Image
import io

# --- 📋 定数リスト ---
BLOCKS_LIST = ["短距離・跳躍・投擲", "中距離", "長距離", "マネージャー"]
ROLES_LIST = ["なし", "主将", "副主将", "長距離ブロック長","短距離ブロック長","中距離パート長", "広報", "競技会", "外務","内務","会計","イベント","合宿","管理者"]
EVENT_OPTIONS = ["100m", "200m", "400m", "800m", "1500m", "5000m", "10000m", "ハーフマラソン", "フルマラソン", "110mH", "400mH", "3000mSC", "4x100mR", "4x400mR", "走高跳", "棒高跳", "走幅跳", "三段跳", "砲丸投", "円盤投", "ハンマー投", "やり投", "十種競技"]

AFFILIATIONS_UG = [
    "情報理工学域 I類 (情報系)",
    "情報理工学域 II類 (融合系)",
    "情報理工学域 III類 (理工系)",
    "情報理工学域 K課程",
    "その他"
]
AFFILIATIONS_GRAD = [
    "情報理工学研究科 情報・ネットワーク工学専攻",
    "情報理工学研究科 機械知能システム学専攻",
    "情報理工学研究科 基盤理工学専攻",
    "情報理工学研究科 情報学専攻",
    "その他"
]

# --- 🧮 便利関数 ---
def calculate_grade(grad_year, univ_cat):
    try:
        today = datetime.date.today()
        current_fiscal_year = today.year if today.month >= 4 else today.year - 1
        gy = int(grad_year)
        grad_fiscal_year = gy - 1
        years_left = grad_fiscal_year - current_fiscal_year
        
        if univ_cat == "学部":
            grade_num = 4 - years_left
            if 1 <= grade_num <= 4: return f"B{grade_num}"
            else: return "-"
        elif univ_cat == "修士":
            grade_num = 2 - years_left
            if 1 <= grade_num <= 2: return f"M{grade_num}"
            else: return "-"
        elif univ_cat == "博士":
            grade_num = 3 - years_left
            if 1 <= grade_num <= 3: return f"D{grade_num}"
            else: return "-"
    except:
        pass
    return "-"

def get_short_grade(grad_year, univ_cat):
    return calculate_grade(grad_year, univ_cat)

def is_track_event(event_name):
    field_keywords = ["跳", "投", "得点", "競技"] 
    for k in field_keywords:
        if k in event_name: return False
    return True

def parse_record_to_float(record_str):
    if not record_str: return None
    s = str(record_str).strip()
    if s.upper() in ["DNS", "DNF", "DQ", "NM", "UK", "-", ""]: return None
    try:
        s = re.sub(r'\(.*?\)', '', s)
        s = re.sub(r'（.*?）', '', s)
        s = s.replace("m", ".").replace("M", ".").replace("ｍ", ".")
        s = s.replace("'", ":").replace("’", ":")
        s = s.replace('"', '.').replace('”', '.')
        s = s.replace("：", ":")
        parts = s.split(":")
        if len(parts) == 3: return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
        elif len(parts) == 2: return float(parts[0])*60 + float(parts[1])
        else: return float(s)
    except: return None

def get_better_record(val1_str, val2_str, event_name):
    v1 = parse_record_to_float(val1_str)
    v2 = parse_record_to_float(val2_str)
    if v1 is None and v2 is None: return "-"
    if v1 is None: return val2_str
    if v2 is None: return val1_str
    is_track = is_track_event(event_name)
    if is_track: return val1_str if v1 <= v2 else val2_str
    else: return val1_str if v1 >= v2 else val2_str

def find_best_result(results_list, event_name):
    if not results_list: return None
    is_track = is_track_event(event_name)
    best_record = None
    best_val = None
    for r in results_list:
        val_str = r.get("result", "")
        val_float = parse_record_to_float(val_str)
        if val_float is None: continue
        if best_val is None:
            best_val = val_float
            best_record = r
            continue
        if is_track:
            if val_float < best_val:
                best_val = val_float
                best_record = r
        else:
            if val_float > best_val:
                best_val = val_float
                best_record = r
    return best_record

def process_image_to_base64(uploaded_file):
    try:
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"): image = image.convert("RGB")
        image.thumbnail((300, 300))
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=70)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"
    except: return None

# --- CSS デザイン ---
def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Noto Sans JP', sans-serif;
            color: #333333;
        }
        
        /* サイドバー */
        section[data-testid="stSidebar"] {
            background-color: #f4f6f9;
            border-right: 1px solid #ddd;
        }

        /* H1: 下線との距離を空ける */
        h1 {
            color: #003366;
            font-weight: 700;
            padding-bottom: 0.8rem;
            border-bottom: 3px solid #003366;
            margin-bottom: 2rem; /* 下の要素との距離 */
        }
        /* H2: 左線のデザイン調整 */
        h2 {
            color: #0056b3;
            border-left: 6px solid #0056b3;
            padding-left: 15px; /* 文字との距離 */
            margin-top: 2.5rem;
            margin-bottom: 1.5rem;
        }
        h3 {
            color: #444;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
        }

        /* ボタン */
        .stButton > button {
            background-color: #003366;
            color: white;
            border-radius: 6px;
            font-weight: bold;
            padding: 0.5rem 1rem;
            transition: 0.3s;
        }
        .stButton > button:hover {
            background-color: #0056b3;
            color: white;
            border-color: #0056b3;
        }
        
        /* カードデザイン */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            background-color: white;
            padding: 15px;
            margin-bottom: 10px;
        }

        /* ▼▼▼ 修正: 以下の行を削除するか、コメントアウトしてください ▼▼▼ */
        MainMenu {visibility: hidden;} 
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)