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

# 디자인 원칙: 다크모드(#0e1117) 및 자산(파랑)/부채(주황) 색상 규정
COLOR_BG = "#0e1117"
COLOR_ASSET = "#4dabf7"  
COLOR_DEBT = "#ff922b"   
COLOR_TEXT = "#ffffff"

# --- [2. 스마트 결제 가이드: 정원 님 카드 데이터] ---
def get_payment_advice(category):
    advices = {
        "식비": "현대카드 (M경차 Ed2: 음식점/카페 포인트 적립)",
        "생활용품": "현대카드 (이마트 e카드 ED2: 신세계포인트/이마트 할인)",
        "월 구독료": "국민카드 (WE:SH All: 전월 실적 채우기용 추천)",
        "주거/통신": "우리카드 (We'll Rich 주거래II: 공과금 실적 확보)",
        "교통": "하나카드 (ONE K-패스: 대중교통 할인)",
        "건강": "하나카드 (MG+ S: 병원/약국 할인)",
        "금융": "현금/계좌이체 (수수료 절감)",
        "경조사": "현금 (계좌이체)"
    }
    return advices.get(category, "KB ALL 카드 (국민 WE:SH All)")
}
    }
    return advices.get(category, "KB ALL 카드 (국민 WE:SH All)")

# --- [3. 유틸리티 함수] ---
def format_krw(val): 
    return f"{int(val):,}".rjust(20) + " 원"

def to_numeric(val):
    try:
        if pd.isna(val) or val == "": return 0
        s = "".join(filter(lambda x: x.isdigit() or x == '-', str(val)))
        return int(s) if s else 0
    except: return 0

def get_current_time():
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
        "time": get_current_time().split(' ')[0], "corpus": corpus, "type": d_type, 
        "cat_main": cat_main, "cat_sub": cat_sub, "item": content, 
        "value": value, "method": method, "user": "정원"
    }
    try: return requests.post("https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec", data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

# --- [4. 메인 UI 설정: 고대비 및 입력창 검은 글씨] ---
st.set_page_config(page_title="JARVIS v57.0", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    
    /* 하얀 버튼 및 입력창: 글씨는 무조건 검게 */
    .stButton>button {{
        background-color: #ffffff !important;
        color: #000000 !important;
        border-radius: 8px; font-weight: bold; border: none; width: 100%;
    }}
    
    /* 입력 바, 선택 바 배경 하양 & 글씨 검정 */
    input, select, textarea, div[data-baseweb="select"] {{
        background-color: #ffffff !important;
        color: #000000 !important;
    }}
    div[data-baseweb="select"] * {{ color: #000000 !important; }}

    .net-box {{ background-color: #1d2129; padding: 25px; border-radius: 12px; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ background-color: #1d2129; padding: 20px; border-radius: 10px; border-bottom: 3px solid #333; text-align: right; }}
    .advice-box {{ background-color: #1c2e36; padding: 15px; border-radius: 8px; border-left: 5px solid {COLOR_ASSET}; margin-top: 10px; color: {COLOR_TEXT} !important; }}
    td {{ text-align: right !important; color: {COLOR_TEXT} !important; }}
    </style>
""", unsafe_allow_html=True)

# 헤더
t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### {get_current_time()} | 평택 {get_weather()}")
with t_c2: st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold;'>JARVIS v57.0 ONLINE</div>", unsafe_allow_html=True)

# --- [5. 사이드바 메뉴] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("SELECT MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])
    st.divider()

# --- [6. 기능 A: 투자 & 자산] ---
if menu == "투자 & 자산":
    st.header("📈 종합 자산 대시보드")
    
    with st.sidebar:
        st.subheader("데이터 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
c_main = st.selectbox("대분류", ["식비", "생활용품", "월 구독료", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        if t_choice == "지출":
            st.markdown(f"""<div class="advice-box"><small>🛡️ 결제 가이드</small><br><b>{get_payment_advice(c_main)}</b></div>""", unsafe_allow_html=True)
        c_sub = st.text_input("소분류"); content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        method_choice = st.selectbox("지출 수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(K-패스)", "하나카드(MG+)", "현금", "계좌이체"])
        if st.button("시트 데이터 전송"):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input, method_choice):
                st.cache_data.clear(); st.rerun()

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
            # --- [7. 데이터 정의: 영양 및 유지보수] ---
RECOMMENDED = {
    "칼로리": 2500, "지방": 60, "콜레스테롤": 300, "나트륨": 2300, 
    "탄수화물": 300, "식이섬유": 30, "당": 50, "단백질": 150
}

if 'maintenance' not in st.session_state:
    st.session_state.maintenance = [
        {"항목": "칫솔", "주기": 90, "마지막": "2025-11-20"},
        {"항목": "샤워기필터", "주기": 60, "마지막": "2026-01-10"},
        {"항목": "수건", "주기": 365, "마지막": "2025-06-01"},
        {"항목": "면도날", "주기": 14, "마지막": "2026-02-10"}
    ]

if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}

# --- [8. 기능 B: 식단 & 건강] ---
elif menu == "식단 & 건강":
    st.header("🥗 영양 분석 리포트")
    
    with st.sidebar:
        st.subheader("영양소 입력 (FatSecret)")
        with st.form("health_form"):
            inputs = []
            for k in RECOMMENDED.keys():
                inputs.append(st.number_input(f"{k}", 0))
            if st.form_submit_button("섭취량 추가"):
                for idx, k in enumerate(RECOMMENDED.keys()):
                    st.session_state.daily_nutri[k] += inputs[idx]
                st.rerun()
        if st.button("♻️ 일일 식단 초기화"):
            st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
            st.rerun()

    curr = st.session_state.daily_nutri
    mc1, mc2 = st.columns(2)
    with mc1: st.markdown(f"""<div class="net-box"><small>오늘의 칼로리</small><br><h2>{int(curr['칼로리'])} / {RECOMMENDED['칼로리']} kcal</h2></div>""", unsafe_allow_html=True)
    with mc2: st.markdown(f"""<div class="net-box"><small>오늘의 단백질</small><br><h2>{int(curr['단백질'])} / {RECOMMENDED['단백질']} g</h2></div>""", unsafe_allow_html=True)
    
    st.divider()
    analysis_data = []
    for k, rec in RECOMMENDED.items():
        rem = max(0, rec - curr[k])
        status = "✅ 달성" if curr[k] >= rec else "⏳ 부족"
        analysis_data.append({"영양소": k, "현재량": f"{curr[k]:,.1f}", "권장량": f"{rec:,.1f}", "남은량": f"{rem:,.1f}", "상태": status})
    st.table(pd.DataFrame(analysis_data).set_index("영양소"))

# --- [9. 기능 C: 재고 & 교체관리] ---
elif menu == "재고 & 교체관리":
    st.header("🏠 생활 시스템 관리")
    
    st.subheader("🚨 JARVIS 교체 알림")
    today = datetime.now()
    for item in st.session_state.maintenance:
        rem = (datetime.strptime(item["마지막"], "%Y-%m-%d") + timedelta(days=item["주기"]) - today).days
        if rem <= 7:
            color = "#ff4b4b" if rem <= 0 else "#ff922b"
            st.markdown(f"""<div style="background-color: #2d1a1a; padding: 15px; border-radius: 8px; border-left: 5px solid {color}; margin-bottom: 10px;">
                <b style="color:{color};">[알람] {item['항목']} 교체 시기</b> (D-{rem})</div>""", unsafe_allow_html=True)
    
    st.divider()
    col_inv, col_maint = st.columns(2)
    with col_inv:
        st.subheader("📦 창고 재고 현황 (금 16g 포함)")
        inventory = [{"항목": "금(실물)", "수량": "16g"}, {"항목": "토마토 페이스트", "수량": "10캔"}, {"항목": "쉐이크", "수량": "9개"}]
        st.table(pd.DataFrame(inventory))
    
    with col_maint:
        st.subheader("⚙️ 관리 주기")
        st.table(pd.DataFrame(st.session_state.maintenance))
        target = st.selectbox("교체 완료 품목", [i["항목"] for i in st.session_state.maintenance])
        if st.button(f"{target} 교체 완료"):
            for i in st.session_state.maintenance:
                if i["항목"] == target: i["마지막"] = today.strftime("%Y-%m-%d")
            st.rerun()

st.sidebar.button("데이터 동기화", on_click=st.cache_data.clear)
