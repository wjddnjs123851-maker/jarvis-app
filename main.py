import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 시트 GID] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0", 
    "Assets": "1068342666", 
    "Report": "308599580",
    "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 화이트 테마 색상 (글씨는 무조건 검정)
COLOR_BG = "#ffffff"
COLOR_TEXT = "#000000"
COLOR_ASSET = "#4dabf7" # 자산 (파랑)
COLOR_DEBT = "#ff922b"  # 부채 (주황)

# 영양소 및 생활용품 데이터 초기화
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

# --- [2. 유틸리티 함수 (생략 없음)] ---
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
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

# --- [3. 화이트 테마 전용 UI 스타일 (고대비 검은 글씨)] ---
st.set_page_config(page_title="JARVIS v60.0", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    h1, h2, h3, p, span, label, div {{ color: {COLOR_TEXT} !important; }}
    
    /* 버튼: 검은색 배경에 하얀 글씨 */
    .stButton>button {{
        background-color: #000000 !important;
        color: #ffffff !important;
        border-radius: 8px; font-weight: bold; border: none; width: 100%;
    }}
    
    /* 입력창: 배경 밝은 회색, 글씨 검정 */
    input, select, textarea, div[data-baseweb="select"] {{
        background-color: #f8f9fa !important;
        color: {COLOR_TEXT} !important;
        border: 1px solid #dee2e6 !important;
    }}
    div[data-baseweb="select"] * {{ color: {COLOR_TEXT} !important; }}

    .net-box {{ background-color: #f1f3f5; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ background-color: #f1f3f5; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; text-align: right; }}
    .advice-box {{ background-color: #e7f5ff; padding: 15px; border-radius: 8px; border-left: 5px solid {COLOR_ASSET}; margin-top: 10px; }}
    td {{ text-align: right !important; color: {COLOR_TEXT} !important; }}
    th {{ color: #495057 !important; }}
    </style>
""", unsafe_allow_html=True)

# 메인 헤더
st.markdown(f"### {get_current_time()} | 평택 온라인 (White Theme)")
# --- [4. 사이드바 메뉴 및 입력 시스템] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("SELECT MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])
    st.divider()

# (1) 투자 & 자산 모듈
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
        method_choice = st.selectbox("결제 수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(K-패스)", "하나카드(MG+)", "현금", "계좌이체"])
        if st.button("시트 데이터 전송"):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input, method_choice):
                st.cache_data.clear(); st.rerun()

    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]; df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df = df_assets[df_assets["val"] > 0]; l_df = df_assets[df_assets["val"] < 0]
        sum_asset = a_df["val"].sum(); sum_debt = l_df["val"].sum(); net_worth = sum_asset + sum_debt

        st.markdown(f"""<div class="net-box"><small>통합 순자산 (Net Worth)</small><br><span style="font-size:2.8em; font-weight:bold;">{net_worth:,.0f} 원</span></div>""", unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        with tc1: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_ASSET};'>자산 총계</small><br><h3>{sum_asset:,.0f} 원</h3></div>""", unsafe_allow_html=True)
        with tc2: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_DEBT};'>부채 총계</small><br><h3>{abs(sum_debt):,.0f} 원</h3></div>""", unsafe_allow_html=True)
        st.divider()
        col1, col2 = st.columns(2)
        with col1: st.subheader("자산 내역"); st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with col2: st.subheader("부채 내역"); st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

# (2) 식단 & 건강 모듈 (정밀 소수점 2자리 적용)
elif menu == "식단 & 건강":
    st.header("🥗 정밀 영양 분석")
    with st.sidebar:
        st.subheader("오늘의 섭취량 입력")
        with st.form("health_form"):
            # 정원 님 요청: 모든 영양소 소수점 2자리(0.01) 입력 지원
            f_in = []
            for k in RECOMMENDED.keys():
                f_in.append(st.number_input(f"{k}", value=0.00, step=0.01, format="%.2f"))
            if st.form_submit_button("영양 데이터 합산"):
                for idx, k in enumerate(RECOMMENDED.keys()):
                    st.session_state.daily_nutri[k] += f_in[idx]
                st.rerun()
        if st.button("♻️ 일일 식단 초기화"):
            st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}; st.rerun()

    curr = st.session_state.daily_nutri
    mc1, mc2 = st.columns(2)
    with mc1: st.markdown(f"""<div class="net-box"><small>칼로리 현황</small><br><h2>{curr['칼로리']:.2f} / {RECOMMENDED['칼로리']} kcal</h2></div>""", unsafe_allow_html=True)
    with mc2: st.markdown(f"""<div class="net-box"><small>단백질 현황</small><br><h2>{curr['단백질']:.2f} / {RECOMMENDED['단백질']} g</h2></div>""", unsafe_allow_html=True)
    
    st.divider()
    # 상세 테이블 역시 소수점 2자리(%.2f)로 표시
    analysis_data = [{"영양소": k, "현재량": f"{curr[k]:,.2f}", "권장량": f"{RECOMMENDED[k]:,.2f}", "남은량": f"{max(0, RECOMMENDED[k]-curr[k]):,.2f}"} for k in RECOMMENDED.keys()]
    st.table(pd.DataFrame(analysis_data).set_index("영양소"))

# (3) 재고 & 교체관리 모듈
elif menu == "재고 & 교체관리":
    st.header("🏠 생활 시스템 관리")
    today = datetime.now()
    st.subheader("🚨 교체 임박 알림")
    for item in st.session_state.maintenance:
        rem = (datetime.strptime(item["마지막"], "%Y-%m-%d") + timedelta(days=item["주기"]) - today).days
        if rem <= 7:
            st.warning(f"**[알람] {item['항목']}** 교체 시기가 {rem}일 남았습니다. (마지막: {item['마지막']})")
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📦 창고 재고 (금 16g 포함)")
        inventory = [{"항목": "금(실물)", "수량": "16g"}, {"항목": "토마토 페이스트", "수량": "10캔"}, {"항목": "단백질 쉐이크", "수량": "9개"}]
        st.table(pd.DataFrame(inventory))
    with c2:
        st.subheader("⚙️ 관리 주기 설정")
        st.table(pd.DataFrame(st.session_state.maintenance))
        target = st.selectbox("교체 완료 품목", [i["항목"] for i in st.session_state.maintenance])
        if st.button(f"{target} 교체 완료"):
            for i in st.session_state.maintenance:
                if i["항목"] == target: i["마지막"] = today.strftime("%Y-%m-%d")
            st.rerun()

st.sidebar.button("데이터 동기화", on_click=st.cache_data.clear)
