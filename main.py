import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 원칙 준수] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0", 
    "Assets": "1068342666", 
    "Report": "308599580",
    "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 디자인 원칙: 다크모드(#0e1117) 및 자산(파랑)/부채(주황) 색상 규정
COLOR_BG = "#0e1117"
COLOR_ASSET = "#4dabf7"  
COLOR_DEBT = "#ff922b"   

# 정원 님 맞춤 일일 권장량 (체중 125kg 기준)
RECOMMENDED = {
    "칼로리": 2500, "지방": 60, "콜레스테롤": 300, "나트륨": 2300, 
    "탄수화물": 300, "식이섬유": 30, "당": 50, "단백질": 150
}

# --- [2. 스마트 결제 로직: 정원 님 카드 혜택] ---
def get_payment_advice(category):
    advices = {
        "식비": "현대카드 (M경차 Ed2: 음식점/카페 포인트 적립)",
        "생활용품": "현대카드 (이마트 e카드 ED2: 신세계포인트/이마트 할인)",
        "주거/통신": "우리카드 (We'll Rich 주거래II: 공과금 실적 확보)",
        "교통": "하나카드 (ONE K-패스: 대중교통 할인)",
        "건강": "하나카드 (MG+ S: 병원/약국 할인)",
        "금융": "현금/계좌이체 (수수료 절약)",
        "경조사": "현금 (계좌이체)"
    }
    return advices.get(category, "KB ALL 카드 (국민 WE:SH All: 전 가맹점 할인)")

# --- [3. 유틸리티 함수] ---
def format_krw(val): 
    # 원칙: 숫자는 3자리 콤마 + 우측 정렬 필수
    return f"{int(val):,}".rjust(20) + " 원"

def to_numeric(val):
    try:
        if pd.isna(val) or val == "": return 0
        s = "".join(filter(lambda x: x.isdigit() or x == '-', str(val)))
        return int(s) if s else 0
    except: return 0

def get_current_time():
    # KST 한국 표준시 보정
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def get_weather():
    try:
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=36.99&longitude=127.11&current_weather=true&timezone=auto"
        res = requests.get(w_url, timeout=2).json()
        temp = res['current_weather']['temperature']
        return f"☀️ {temp}°C"
    except: return "날씨 로드 실패"

def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(d_type, cat_main, cat_sub, content, value, method, corpus="Log"):
    payload = {
        "time": get_current_time().split(' ')[0],
        "corpus": corpus, "type": d_type, "cat_main": cat_main, 
        "cat_sub": cat_sub, "item": content, "value": value, 
        "method": method, "user": "정원"
    }
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

# --- [4. 메인 UI 설정] ---
st.set_page_config(page_title="JARVIS v52.0", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; color: #ffffff; }}
    .net-box {{ background-color: #1d2129; padding: 25px; border-radius: 12px; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .status-card {{ background-color: #1d2129; padding: 20px; border-radius: 10px; border-top: 4px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ background-color: #1d2129; padding: 20px; border-radius: 10px; border-bottom: 3px solid #333; text-align: right; }}
    .advice-box {{ background-color: #1c2e36; padding: 15px; border-radius: 8px; border-left: 5px solid {COLOR_ASSET}; margin-top: 10px; }}
    td {{ text-align: right !important; }}
    </style>
""", unsafe_allow_html=True)

# 헤더
t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### {get_current_time()} | 평택 {get_weather()}")
with t_c2: st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold;'>JARVIS v52.0 ONLINE</div>", unsafe_allow_html=True)

# --- [5. 세션 상태 관리 (식단 리셋)] ---
if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}

# --- [6. 사이드바: 통합 입력 제어 (좌측)] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    
    if menu == "투자 & 자산":
        st.subheader("데이터 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        if t_choice == "지출":
            st.markdown(f"""<div class="advice-box"><small>🛡️ 결제 가이드</small><br><b>{get_payment_advice(c_main)}</b></div>""", unsafe_allow_html=True)
        c_sub = st.text_input("소분류")
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        method_choice = st.selectbox("지출 수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(K-패스)", "하나카드(MG+)", "현금", "계좌이체"])
        if st.button("시트 데이터 전송"):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input, method_choice):
                st.cache_data.clear(); st.rerun()

    elif menu == "식단 & 건강":
        st.subheader("영양소 입력 (FatSecret)")
        with st.form("health_form"):
            f_cal = st.number_input("칼로리 (kcal)", 0)
            f_fat = st.number_input("지방 (g)", 0)
            f_chole = st.number_input("콜레스테롤 (mg)", 0)
            f_na = st.number_input("나트륨 (mg)", 0)
            f_carb = st.number_input("탄수화물 (g)", 0)
            f_fiber = st.number_input("식이섬유 (g)", 0)
            f_sugar = st.number_input("당 (g)", 0)
            f_prot = st.number_input("단백질 (g)", 0)
            if st.form_submit_button("섭취량 추가"):
                st.session_state.daily_nutri["칼로리"] += f_cal
                st.session_state.daily_nutri["지방"] += f_fat
                st.session_state.daily_nutri["콜레스테롤"] += f_chole
                st.session_state.daily_nutri["나트륨"] += f_na
                st.session_state.daily_nutri["탄수화물"] += f_carb
                st.session_state.daily_nutri["식이섬유"] += f_fiber
                st.session_state.daily_nutri["당"] += f_sugar
                st.session_state.daily_nutri["단백질"] += f_prot
                st.rerun()
        if st.button("♻️ 일일 식단 초기화"):
            st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
            st.rerun()

# --- [7. 메인 화면: 결과 및 분석 (우측)] ---

# (1) 투자 & 자산 탭
if menu == "투자 & 자산":
    st.header("종합 자산 대시보드")
    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]; df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df = df_assets[df_assets["val"] > 0]; l_df = df_assets[df_assets["val"] < 0]
        sum_asset = a_df["val"].sum(); sum_debt = l_df["val"].sum(); net_worth = sum_asset + sum_debt

        st.markdown(f"""<div class="net-box"><small>통합 순자산 (Net Worth)</small><br><span style="font-size:2.8em; color:{COLOR_ASSET}; font-weight:bold;">{net_worth:,.0f} 원</span></div>""", unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        with tc1: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_ASSET};'>자산 총계</small><br><h3>{sum_asset:,.0f} 원</h3></div>""", unsafe_allow_html=True)
        with tc2: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_DEBT};'>부채 총계</small><br><h3>{abs(sum_debt):,.0f} 원</h3></div>""", unsafe_allow_html=True)
        st.divider()
        col1, col2 = st.columns(2)
        with col1: st.subheader("세부 자산 내역"); st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with col2: st.subheader("세부 부채 내역"); st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

# (2) 식단 & 건강 탭
elif menu == "식단 & 건강":
    st.header("오늘의 영양 분석 리포트")
    curr = st.session_state.daily_nutri
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        diff_cal = RECOMMENDED["칼로리"] - curr["칼로리"]
        st.markdown(f"""<div class="status-card"><small>칼로리 현황</small><br><h2>{int(curr['칼로리'])} / {RECOMMENDED['칼로리']} kcal</h2><small>{'부족' if diff_cal >= 0 else '초과'}: {abs(int(diff_cal))} kcal</small></div>""", unsafe_allow_html=True)
    with sc2:
        diff_prot = RECOMMENDED["단백질"] - curr["단백질"]
        st.markdown(f"""<div class="status-card"><small>단백질 현황</small><br><h2>{int(curr['단백질'])} / {RECOMMENDED['단백질']} g</h2><small>{'부족' if diff_prot >= 0 else '달성'}: {abs(int(diff_prot))} g</small></div>""", unsafe_allow_html=True)
    with sc3:
        avg_ratio = (min(1, curr['칼로리']/RECOMMENDED['칼로리']) + min(1, curr['단백질']/RECOMMENDED['단백질'])) / 2 * 100
        st.markdown(f"""<div class="status-card"><small>영양 달성도</small><br><h2>{int(avg_ratio)}%</h2><small>정원 님, 건강한 식단입니다.</small></div>""", unsafe_allow_html=True)
    st.divider()
    st.subheader("영양소별 세부 분석 (FatSecret 순서)")
    analysis_data = []
    for k, rec in RECOMMENDED.items():
        val = curr[k]
        diff = rec - val
        status = "✅ 적정" if abs(diff) < (rec * 0.1) else ("⚠️ 부족" if diff > 0 else "❌ 초과")
        analysis_data.append({"영양소": k, "현재량": f"{val:,.1f}", "권장량": f"{rec:,.1f}", "상태": status, "남은양": f"{max(0, diff):,.1f}"})
    st.table(pd.DataFrame(analysis_data).set_index("영양소"))

# (3) 재고 관리 탭
elif menu == "재고 관리":
    st.header("창고 전수조사 리스트")
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"구분": "자산", "항목": "금(실물)", "수량": "16g", "비고": "금고"},
            {"구분": "상온", "항목": "올리브유/알룰로스/스테비아/사과식초", "수량": "보유", "비고": "조미료"},
            {"구분": "상온", "항목": "진간장/국간장/맛술/굴소스/저당케찹", "수량": "보유", "비고": "조미료"},
            {"구분": "상온", "항목": "하이라이스 가루/황설탕/고춧가루/후추/통깨/김", "수량": "보유", "비고": "조미료"},
            {"구분": "곡물", "항목": "카무트/현미/쌀", "수량": "보유", "비고": "잡곡"},
            {"구분": "냉장", "항목": "계란/대파/양파/마늘/청양고추", "수량": "보유", "비고": "냉장"},
            {"구분": "냉동", "항목": "삼치/닭다리살/닭가슴살 스테이크", "수량": "보유", "비고": "단백질"},
            {"구분": "냉동", "항목": "토마토 페이스트(10캔)/쉐이크(9개)", "수량": "보유", "비고": "가공"}
        ])
    st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True)

st.sidebar.button("데이터 동기화", on_click=st.cache_data.clear)
