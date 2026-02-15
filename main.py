import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 원칙 준수] ---
# 정원 님 가계부 2.0 시트 ID 및 GID 맵
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

# --- [2. 스마트 결제 가이드 로직: 정원 님 보유 카드 혜택] ---
def get_payment_advice(category):
    advices = {
        "식비": "현대카드 (M경차 Ed2: 음식점/카페 포인트 적립)",
        "생활용품": "현대카드 (이마트 e카드 ED2: 이마트 할인 및 신세계포인트)",
        "주거/통신": "우리카드 (We'll Rich 주거래II: 통신비/공과금 실적 확보)",
        "교통": "하나카드 (ONE K-패스: 대중교통 할인) / 국민카드 (하이패스)",
        "건강": "하나카드 (MG+ S: 병원 및 약국 할인)",
        "금융": "현금/계좌이체 (수수료 절감 및 자산 이동)",
        "경조사": "현금 (경조사비 지출)"
    }
    return advices.get(category, "국민카드 (WE:SH All: 전 가맹점 무난한 할인)")

# --- [3. 유틸리티 함수: 규정 준수] ---
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
    # 캐시 무시를 위한 타임스탬프 파라미터 적용
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- [4. 메인 UI 및 고대비 디자인 원칙 적용] ---
st.set_page_config(page_title="JARVIS v55.0", layout="wide")
st.markdown(f"""
    <style>
    /* 다크모드 배경 및 글자색 */
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    h1, h2, h3, p, span, label, div {{ color: {COLOR_TEXT} !important; }}
    
    /* 버튼: 하얗다면 글씨는 검게 */
    .stButton>button {{
        background-color: #ffffff !important;
        color: #000000 !important;
        border-radius: 8px;
        font-weight: bold;
        border: 2px solid #ffffff;
        width: 100%;
    }}
    
    /* 레이아웃 디자인 박스 */
    .net-box {{ background-color: #1d2129; padding: 25px; border-radius: 12px; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ background-color: #1d2129; padding: 20px; border-radius: 10px; border-bottom: 3px solid #333; text-align: right; }}
    .advice-box {{ background-color: #1c2e36; padding: 15px; border-radius: 8px; border-left: 5px solid {COLOR_ASSET}; margin-top: 10px; }}
    
    /* 테이블 우측 정렬 및 숫자 가독성 */
    td {{ text-align: right !important; color: {COLOR_TEXT} !important; }}
    </style>
""", unsafe_allow_html=True)

# 최상단 헤더
t_c1, t_c2 = st.columns([7, 3])
with t_c1:
    st.markdown(f"### {get_current_time()} | 평택 {get_weather()}")
with t_c2:
    st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold; font-size:1.2em;'>JARVIS v55.0 ONLINE</div>", unsafe_allow_html=True)

# --- [5. 사이드바 메뉴: 입력 (좌측)] ---
with st.sidebar:
    st.title("JARVIS SYSTEM")
    menu = st.radio("SELECT MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])
    st.divider()

# --- [6. 모듈 A 메인 기능: 투자 & 자산] ---
if menu == "투자 & 자산":
    st.header("📈 종합 자산 대시보드")
    
    # 1. 데이터 로드 및 가공
    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        # A열(항목), B열(금액) 강제 매핑
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        
        a_df = df_assets[df_assets["val"] > 0].copy()
        l_df = df_assets[df_assets["val"] < 0].copy()
        
        sum_asset = a_df["val"].sum()
        sum_debt = l_df["val"].sum()
        net_worth = sum_asset + sum_debt

        # 2. 최상단 합계 노출 (원칙)
        st.markdown(f"""
            <div class="net-box">
                <small style='color:#888;'>통합 순자산 (Net Worth)</small><br>
                <span style="font-size:2.8em; color:{COLOR_ASSET}; font-weight:bold;">{net_worth:,.0f} 원</span>
            </div>
        """, unsafe_allow_html=True)

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown(f"""<div class="total-card"><small style='color:{COLOR_ASSET};'>자산 총계</small><br><h3 style='color:{COLOR_ASSET};'>{sum_asset:,.0f} 원</h3></div>""", unsafe_allow_html=True)
        with t_col2:
            st.markdown(f"""<div class="total-card"><small style='color:{COLOR_DEBT};'>부채 총계</small><br><h3 style='color:{COLOR_DEBT};'>{abs(sum_debt):,.0f} 원</h3></div>""", unsafe_allow_html=True)

        st.divider()

        # 3. 상세 결과 (우측 배치)
        res_c1, res_c2 = st.columns(2)
        with res_c1:
            st.subheader("세부 자산 내역 (Assets)")
            st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with res_c2:
            st.subheader("세부 부채 내역 (Liabilities)")
            if not l_df.empty:
                st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
    else:
        st.error("Assets 시트 연동 실패. 시트 공유 설정 및 ID를 확인하십시오.")

# 다음 파트(식단/재고/교체주기)는 'Module B'에서 이어집니다.
# --- [Module B 시작: Module A의 하단에 이어서 배치] ---

# --- [7. 데이터 정의: 영양 및 교체 주기] ---
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

# --- [8. 메인 화면 로직: 식단 & 건강] ---
if menu == "식단 & 건강":
    st.header("🥗 영양 분석 및 건강 관리")
    
    # 영양소 입력 (사이드바 또는 메인 좌측)
    with st.container():
        st.subheader("영양소 섭취 기록")
        with st.form("health_form"):
            c1, c2, c3, c4 = st.columns(4)
            with c1: f_cal = st.number_input("칼로리 (kcal)", 0)
            with c2: f_fat = st.number_input("지방 (g)", 0)
            with c3: f_chole = st.number_input("콜레스테롤 (mg)", 0)
            with c4: f_na = st.number_input("나트륨 (mg)", 0)
            
            c5, c6, c7, c8 = st.columns(4)
            with c5: f_carb = st.number_input("탄수화물 (g)", 0)
            with c6: f_fiber = st.number_input("식이섬유 (g)", 0)
            with c7: f_sugar = st.number_input("당 (g)", 0)
            with c8: f_prot = st.number_input("단백질 (g)", 150) # 정원 님 고단백 지향
            
            if st.form_submit_button("영양 데이터 합산"):
                inputs = [f_cal, f_fat, f_chole, f_na, f_carb, f_fiber, f_sugar, f_prot]
                for k, v in zip(RECOMMENDED.keys(), inputs):
                    st.session_state.daily_nutri[k] += v
                st.success("오늘의 섭취 데이터가 갱신되었습니다.")
                st.rerun()

    st.divider()

    # 결과 분석 (우측 배치 개념)
    curr = st.session_state.daily_nutri
    st.subheader("오늘의 영양 리포트")
    
    # 핵심 지표 최상단 노출
    mc1, mc2 = st.columns(2)
    with mc1:
        st.markdown(f"""<div class="net-box"><small>칼로리</small><br><span style="font-size:2em;">{int(curr['칼로리'])} / {RECOMMENDED['칼로리']} kcal</span></div>""", unsafe_allow_html=True)
    with mc2:
        st.markdown(f"""<div class="net-box" style="border-left-color:#2ecc71;"><small>단백질 (목표 150g)</small><br><span style="font-size:2em;">{int(curr['단백질'])} / {RECOMMENDED['단백질']} g</span></div>""", unsafe_allow_html=True)

    # 8종 영양소 상세 테이블
    analysis_data = []
    for k in RECOMMENDED.keys():
        rem = max(0, RECOMMENDED[k] - curr[k])
        status = "✅ 달성" if curr[k] >= RECOMMENDED[k] else "⏳ 부족"
        analysis_data.append({"영양소": k, "현재량": f"{curr[k]:,.1f}", "권장량": f"{RECOMMENDED[k]:,.1f}", "남은량": f"{rem:,.1f}", "상태": status})
    
    st.table(pd.DataFrame(analysis_data).set_index("영양소"))
    
    if st.button("♻️ 일일 식단 초기화"):
        st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
        st.rerun()

# --- [9. 메인 화면 로직: 재고 & 교체관리] ---
elif menu == "재고 & 교체관리":
    st.header("🏠 생활 시스템 관리")
    
    # 알림 로직 (가장 눈에 띄게)
    st.subheader("🚨 JARVIS Maintenance Alert")
    today = datetime.now()
    alert_count = 0
    
    for item in st.session_state.maintenance:
        last_date = datetime.strptime(item["마지막"], "%Y-%m-%d")
        next_date = last_date + timedelta(days=item["주기"])
        remaining = (next_date - today).days
        
        if remaining <= 7:
            alert_count += 1
            color = "#ff4b4b" if remaining <= 0 else "#ff922b"
            msg = "즉시 교체 필요" if remaining <= 0 else f"{remaining}일 후 교체"
            st.markdown(f"""
                <div style="background-color: #2d1a1a; padding: 15px; border-radius: 8px; border-left: 5px solid {color}; margin-bottom: 10px;">
                    <b style="color:{color};">[교체 알람] {item['항목']}</b><br>
                    <small>주기: {item['주기']}일 | 마지막 교체: {item['마지막']}</small><br>
                    <b>상태: {msg}</b>
                </div>
            """, unsafe_allow_html=True)
            
    if alert_count == 0:
        st.info("모든 생활용품이 양호한 상태입니다.")

    st.divider()

    # 재고 및 주기 상세
    col_inv, col_maint = st.columns(2)
    with col_inv:
        st.subheader("📦 창고 재고 현황")
        inventory = [
            {"항목": "금(실물)", "수량": "16g", "비고": "안전자산"},
            {"항목": "토마토 페이스트", "수량": "10캔", "비고": "양식 식재료"},
            {"항목": "단백질 쉐이크", "수량": "9개", "비고": "건강보조"},
            {"항목": "종량제 봉투", "수량": "15매", "비고": "생활소모품"}
        ]
        st.table(pd.DataFrame(inventory))

    with col_maint:
        st.subheader("⚙️ 관리 주기 설정")
        m_df = pd.DataFrame(st.session_state.maintenance)
        st.table(m_df)
        
        # 교체 완료 버튼 (고대비 적용됨)
        target_item = st.selectbox("교체 완료 품목 선택", [i["항목"] for i in st.session_state.maintenance])
        if st.button(f"{target_item} 교체 완료 처리"):
            for i in st.session_state.maintenance:
                if i["항목"] == target_item:
                    i["마지막"] = today.strftime("%Y-%m-%d")
            st.success(f"{target_item}의 주기가 오늘 날짜로 갱신되었습니다.")
            st.rerun()
