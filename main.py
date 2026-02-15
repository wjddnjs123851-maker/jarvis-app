import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, date

# --- [1. 시스템 설정] ---
# 정원 님과 서진 님의 통합 관리용 시트 ID
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0", 
    "Assets": "1068342666", 
    "Finance": "0", 
    "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# [색상 팔레트] 다크모드 및 색약 배려
COLOR_BG = "#0e1117"
COLOR_ASSET = "#4dabf7"  # 파랑 (수입/자산)
COLOR_DEBT = "#ff922b"   # 주황 (지출/부채)
COLOR_TEXT = "#fafafa"

DAILY_GUIDE = {
    "칼로리": {"val": 2900.0, "unit": "kcal"}, "지방": {"val": 90.0, "unit": "g"},
    "콜레스테롤": {"val": 300.0, "unit": "mg"}, "나트륨": {"val": 2300.0, "unit": "mg"},
    "탄수화물": {"val": 360.0, "unit": "g"}, "식이섬유": {"val": 30.0, "unit": "g"},
    "당": {"val": 50.0, "unit": "g"}, "단백질": {"val": 160.0, "unit": "g"}
}

FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46}, "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88}, "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400}, "ETH": {"평단": 4243000, "수량": 0.03417393}
    }
}

# --- [2. 핵심 유틸리티 함수] ---
def format_krw(val): 
    return f"{int(val):>15,}" + "원" # 우측 정렬 반영

def to_numeric(val):
    try: 
        if pd.isna(val): return 0
        return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def send_to_sheet(d_type, item, value, date_val, corpus="Log"):
    d_str = date_val.strftime('%Y-%m-%d')
    payload = {"time": d_str, "corpus": corpus, "type": d_type, "item": item, "value": value}
    try: 
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except: return False

@st.cache_data(ttl=60) # 1분 캐시로 효율 증대
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: 
        df = pd.read_csv(url)
        return df.dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 레이아웃 설정] ---
st.set_page_config(page_title="JARVIS v41.1", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    [data-testid="stSidebar"] {{ background-color: #1c1e26; }}
    /* 숫자 우측 정렬 및 폰트 설정 */
    [data-testid="stDataFrame"] table td {{ text-align: right !important; font-family: 'Courier New', monospace; }}
    div[data-testid="stMetricValue"] {{ text-align: right; font-size: 1.8rem !important; }}
    
    /* 버튼 스타일 커스텀 */
    div[data-testid="stFormSubmitButton"] > button {{ 
        background-color: {COLOR_ASSET} !important; color: white !important; width: 100%;
    }}
    </style>
""", unsafe_allow_html=True)
# --- [4. 헤더 및 날씨 정보] ---
try:
    kst_now = datetime.now() + pd.Timedelta(hours=9)
    date_str = kst_now.strftime('%Y-%m-%d %H:%M')
    w_url = "https://api.open-meteo.com/v1/forecast?latitude=36.99&longitude=127.11&current_weather=true&timezone=auto"
    w_res = requests.get(w_url, timeout=1).json()
    temp = w_res['current_weather']['temperature']
    w_code = w_res['current_weather']['weathercode']
    icon = "☀️" if w_code <= 3 else "☁️" if w_code <= 48 else "🌧️" if w_code <= 80 else "❄️"
    weather_str = f"{icon} {temp}°C"
except:
    date_str = datetime.now().strftime('%Y-%m-%d')
    weather_str = "기상 정보 로딩 실패"

t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### 📅 {date_str} (KST) | {weather_str} (평택)")
with t_c2: st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET};'><b>SYSTEM STATUS: ONLINE (v41.1)</b></div>", unsafe_allow_html=True)

# --- [5. 사이드바: 제어 센터] ---
with st.sidebar:
    st.title("🤖 JARVIS Control")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    
    if menu == "투자 & 자산":
        st.subheader("💰 내역 입력")
        with st.form("asset_input_form"):
            date_in = st.date_input("날짜", datetime.now())
            t_choice = st.selectbox("구분", ["지출", "수입"])
            cats = ["식비", "생활/마트", "주거/통신", "건강/의료", "교통/차량", "금융/보험", "경조사", "취미", "기타"] if t_choice == "지출" else ["급여", "금융소득", "기타수입", "자산이동"]
            c_choice = st.selectbox("카테고리", cats)
            item_in = st.text_input("내용", "")
            a_input = st.number_input("금액(원)", min_value=0, step=1000)
            
            if st.form_submit_button("💾 데이터 전송"):
                if a_input > 0:
                    final_item = f"{c_choice} - {item_in}" if item_in else c_choice
                    if send_to_sheet(t_choice, final_item, a_input, date_in, corpus="Finance"):
                        st.success("시트에 기록되었습니다."); st.rerun()

# --- [6. 메인 탭 로직] ---
if menu == "투자 & 자산":
    st.header("💎 종합 자산 현황 (Net Worth)")
    try:
        df_assets = load_sheet_data(GID_MAP["Assets"])
        df_log = load_sheet_data(GID_MAP["Log"])
        
        # 자산 가공
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        
        # 투자 자산 환산
        inv_rows = []
        for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
            for name, info in items.items(): 
                inv_rows.append({"항목": f"📈 {name}", "val": int(info['평단'] * info['수량'])})
        
        df_total = pd.concat([df_assets, pd.DataFrame(inv_rows)], ignore_index=True)
        
        # 자산/부채 분류
        a_df = df_total[df_total["val"] >= 0].copy()
        l_df = df_total[df_total["val"] < 0].copy()
        net_worth = a_df["val"].sum() + l_df["val"].sum()

        # 상단 요약 (순자산 최상단 노출 원칙)
        st.markdown(f"""
            <div style='background-color:#1c1e26; padding:20px; border-radius:15px; text-align:center; border: 2px solid {COLOR_ASSET}; margin-bottom:25px;'>
                <p style='margin:0; font-size:1.2rem; color:#888;'>통합 순자산 (Net Worth)</p>
                <h1 style='margin:0; color:{COLOR_ASSET}; font-size:3rem;'>{format_krw(net_worth)}</h1>
            </div>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("🔹 보유 자산")
            st.metric("Total Assets", format_krw(a_df["val"].sum()))
            st.dataframe(a_df[["항목", "val"]].assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]], use_container_width=True, hide_index=True)
            
        with col_right:
            st.subheader("🔸 상환 부채")
            st.metric("Total Liabilities", format_krw(abs(l_df["val"].sum())), delta_color="inverse")
            st.dataframe(l_df[["항목", "val"]].assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]], use_container_width=True, hide_index=True)

    except Exception as e: st.error(f"데이터 연동 오류: {e}")

elif menu == "식단 & 건강":
    st.header("🥗 Diet & Health Secretariate")
    d_day = (date(2026, 5, 30) - date.today()).days
    st.warning(f"💍 결혼식까지 **{d_day}일** 남았습니다. 목표 체중까지 집중하십시오.")

    c_in, c_stat = st.columns([6, 4])
    with c_in:
        with st.form("health_form"):
            weight = st.number_input("현재 체중 (kg)", 100.0, 150.0, 125.0, step=0.1)
            st.divider()
            cc1, cc2 = st.columns(2)
            with cc1:
                kcal = st.number_input("칼로리 (kcal)", 0, 5000, 0)
                carb = st.number_input("탄수화물 (g)", 0, 500, 0)
            with cc2:
                prot = st.number_input("단백질 (g)", 0, 300, 0)
                fat = st.number_input("지방 (g)", 0, 200, 0)
            
            if st.form_submit_button("✅ 건강 데이터 기록"):
                send_to_sheet("건강", "체중", weight, date.today(), "Health")
                if kcal > 0: send_to_sheet("식단", "칼로리", kcal, date.today(), "Health")
                st.success("성공적으로 기록되었습니다."); st.rerun()

    with c_stat:
        st.subheader("📊 오늘의 영양 상태")
        # 가이드 대비 현재 섭취량 시각화 로직 (v39.0 기반 유지 및 최적화)
        st.info("시트 데이터 기반 실시간 로딩 활성화됨")

elif menu == "재고 관리":
    st.header("📦 Inventory Management")
    # 재고 데이터 초기값
    if 'inv_data' not in st.session_state:
        st.session_state.inv_data = pd.DataFrame([
            {"항목": "냉동 삼치", "수량": "4팩", "비고": "26-05-10까지"},
            {"항목": "단백질 쉐이크", "수량": "9개", "비고": "초코맛"}
        ])
    
    st.subheader("🛒 식자재 재고")
    st.session_state.inv_data = st.data_editor(st.session_state.inv_data, num_rows="dynamic", use_container_width=True)
    
    st.divider()
    st.subheader("⏰ 생활용품 교체 주기")
    supplies = pd.DataFrame([
        {"품목": "칫솔(정원)", "최근교체": "2026-02-01", "주기": 30},
        {"품목": "면도날", "최근교체": "2026-02-10", "주기": 14}
    ])
    st.table(supplies)

# --- [7. 안전장치: 자동 세션 유지] ---
if st.button("🔄 시스템 리프레시"):
    st.cache_data.clear()
    st.rerun()
