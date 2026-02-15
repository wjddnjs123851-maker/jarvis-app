import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
# 가계부 2.0 파일 연동 준비 (Sheet ID 및 GID 업데이트 필요 시 수정 가능)
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {
    "Log": "1716739583",      # 전체 입출력 로그
    "Finance": "1790876407",  # 월별 지출/수입 통계용
    "Assets": "1666800532",   # 기초 자산 데이터 (가계부 2.0)
    "Health": "123456789"     # 식단 데이터
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 색상 가이드 (화이트톤 & 색약 배려)
COLOR_ASSET = "#4dabf7"  # 자산/수입 (파랑)
COLOR_DEBT = "#ff922b"   # 부채/지출 (주황)

# 식단 가이드 (순서: 칼로리, 단백질, 탄수화물, 지방, 당류, 나트륨, 식이섬유, 콜레스테롤)
NUTRI_ORDER = ["칼로리", "단백질", "탄수화물", "지방", "당류", "나트륨", "식이섬유", "콜레스테롤"]

FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46}, "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88}, "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400}, "ETH": {"평단": 4243000, "수량": 0.03417393}
    }
}

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}".rjust(15) + " 원"

def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def send_to_sheet(d_type, item, value, corpus="Log"):
    payload = {
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
        "corpus": corpus, "type": d_type, "item": item, "value": value
    }
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 레이아웃 및 시간 표시 수정] ---
st.set_page_config(page_title="JARVIS v42.0", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; color: #212529; }}
    [data-testid="stMetricValue"] {{ text-align: right !important; }}
    [data-testid="stTable"] td {{ text-align: right !important; }}
    .main-summary {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    </style>
""", unsafe_allow_html=True)

# 상단 바 (시간 표시 문제 해결)
t_c1, t_c2 = st.columns([7, 3])
with t_c1: 
    # 실시간 시간 반영
    st.markdown(f"### {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Pyeongtaek")
with t_c2: 
    st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold;'>SYSTEM STATUS: ONLINE</div>", unsafe_allow_html=True)

# --- [4. 사이드바: 통합 입력 센터 (제어영역)] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("CATEGORY", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    
    if menu == "투자 & 자산":
        st.subheader("지출/수입 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        cats = ["식비(집밥)", "식비(외식)", "생활용품", "건강", "주거/통신", "교통", "보험", "경조사", "자산이동", "기타"] if t_choice == "지출" else ["급여", "금융소득", "자산이동", "기타"]
        c_choice = st.selectbox("카테고리", cats)
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        if st.button("내역 전송", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_choice, a_input, corpus="Log"):
                st.success("입력 성공"); st.rerun()

# --- [5. 메인 화면: 투자 & 자산 대시보드] ---
if menu == "투자 & 자산":
    st.header("투자 및 종합 자산 관리")
    
    # 데이터 로딩
    df_assets = load_sheet_data(GID_MAP["Assets"])
    df_log = load_sheet_data(GID_MAP["Log"])
    
    # 실시간 자산 영향 계산 로직
    cash_diff, card_debt = 0, 0
    if not df_log.empty:
        df_log.columns = ["날짜", "구분", "항목", "수치"]
        for _, row in df_log.iterrows():
            val = to_numeric(row["수치"])
            if row["구분"] == "지출":
                if row["항목"] == "자산이동": cash_diff -= val
                else: card_debt += val
            elif row["구분"] == "수입":
                if row["항목"] != "자산이동": cash_diff += val

    # 자산 데이터 구성 (가계부 2.0 기반)
    if not df_assets.empty:
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        if not df_assets.empty: df_assets.iloc[0, df_assets.columns.get_loc("val")] += cash_diff
    
    # 투자 자산 합산
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
    
    df_total = pd.concat([df_assets, pd.DataFrame(inv_rows)], ignore_index=True)
    if card_debt > 0: df_total = pd.concat([df_total, pd.DataFrame([{"항목": "카드 미결제(지출)", "val": -card_debt}])], ignore_index=True)

    a_df, l_df = df_total[df_total["val"] >= 0].copy(), df_total[df_total["val"] < 0].copy()
    net_worth = a_df["val"].sum() - abs(l_df["val"].sum())

    # 순자산 상단 노출
    st.markdown(f"""<div class="main-summary"><small>통합 순자산 (Net Worth)</small><br><span style="font-size:2.5em; color:{COLOR_ASSET}; font-weight:bold;">{format_krw(net_worth)}</span></div>""", unsafe_allow_html=True)

    # 섹션 분할: 자산/부채 및 월별 지출/수입관리
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("자산 및 부채 현황")
        st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        if not l_df.empty:
            st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
    
    with col2:
        st.subheader("월별 지출 및 수입 분석")
        if not df_log.empty:
            # 월별 통계 간략 구현
            st.metric("이번 달 총 지출", format_krw(card_debt), delta_color="inverse")
            st.metric("이번 달 총 수입", format_krw(cash_diff if cash_diff > 0 else 0))
            st.info("가계부 2.0 상세 분석 섹션 연동 대기 중")
            # --- [6. 사이드바: 건강 및 재고 입력 섹션 (추가)] ---
with st.sidebar:
    if menu == "식단 & 건강":
        st.subheader("식단 및 신체 입력")
        with st.form("health_input_form"):
            in_w = st.number_input("체중 (kg)", 50.0, 150.0, 125.0, step=0.1)
            st.divider()
            # 팻시크릿 기반 순서 적용
            in_kcal = st.number_input("칼로리 (kcal)", 0, 5000, 0)
            in_prot = st.number_input("단백질 (g)", 0, 300, 0)
            in_carb = st.number_input("탄수화물 (g)", 0, 500, 0)
            in_fat = st.number_input("지방 (g)", 0, 200, 0)
            in_sugar = st.number_input("당류 (g)", 0, 200, 0)
            in_na = st.number_input("나트륨 (mg)", 0, 5000, 0)
            in_fiber = st.number_input("식이섬유 (g)", 0, 100, 0)
            in_chole = st.number_input("콜레스테롤 (mg)", 0, 1000, 0)
            
            if st.form_submit_button("건강 데이터 저장", use_container_width=True):
                # 체중 및 영양소 개별 전송 로직
                send_to_sheet("건강", "체중", in_w, corpus="Health")
                nutris = {
                    "칼로리": in_kcal, "단백질": in_prot, "탄수화물": in_carb, 
                    "지방": in_fat, "당류": in_sugar, "나트륨": in_na, 
                    "식이섬유": in_fiber, "콜레스테롤": in_chole
                }
                for k, v in nutris.items():
                    if v > 0: send_to_sheet("식단", k, v, corpus="Health")
                st.success("기록 완료"); st.rerun()

    elif menu == "재고 관리":
        st.subheader("재고 변동 기록")
        with st.form("inv_form"):
            inv_item = st.text_input("품목명")
            inv_qty = st.text_input("수량/상태")
            inv_note = st.text_input("비고")
            if st.form_submit_button("재고 리스트 업데이트"):
                # 세션 데이터에 우선 반영 (추후 시트 연동 가능)
                new_data = pd.DataFrame([{"항목": inv_item, "수량": inv_qty, "비고": inv_note}])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_data], ignore_index=True)
                st.rerun()

# --- [7. 메인 화면: 식단 & 건강 대시보드] ---
if menu == "식단 & 건강":
    st.header("영양 섭취 및 건강 지표 분석")
    
    # 데이터 로드
    df_log = load_sheet_data(GID_MAP["Log"])
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 현재 섭취량 계산
    cur_nutri = {k: 0 for k in NUTRI_ORDER}
    if not df_log.empty:
        df_log['날짜'] = df_log['날짜'].astype(str)
        df_today = df_log[df_log['날짜'].str.contains(today_str)]
        for k in NUTRI_ORDER:
            cur_nutri[k] = df_today[(df_today['구분'] == '식단') & (df_today['항목'] == k)]['수치'].apply(to_numeric).sum()

    # 우측 대시보드 레이아웃
    col_stat, col_guide = st.columns([6, 4])
    
    with col_stat:
        st.subheader("오늘의 영양 섭취 현황")
        # 테이블 형태 우측 정렬 표시
        stat_df = pd.DataFrame([
            {"영양소": k, "섭취량": f"{cur_nutri[k]:,.1f}"} for k in NUTRI_ORDER
        ])
        st.table(stat_df.set_index("영양소"))

    with col_guide:
        st.subheader("일일 권장 가이드")
        for name in ["칼로리", "단백질", "탄수화물", "지방"]:
            val = cur_nutri[name]
            guide = 2900 if name == "칼로리" else 150 # 임시 가이드값
            st.caption(f"{name} 충족도")
            st.progress(min(val / guide, 1.0))
            st.write(f"{val:,.0f} / {guide:,.0f}")

# --- [8. 메인 화면: 재고 관리 대시보드] ---
elif menu == "재고 관리":
    st.header("식재료 및 소모품 재고 현황")
    
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"항목": "냉동 삼치", "수량": "4팩", "비고": "26-05-10까지"},
            {"항목": "냉동닭다리살", "수량": "3팩", "비고": "냉동보관"},
            {"항목": "카무트", "수량": "2kg", "비고": "혼합곡용"}
        ])

    st.subheader("실시간 재고 목록")
    # 메인 화면에서 직접 수정도 가능하도록 에디터 배치
    st.session_state.inventory = st.data_editor(
        st.session_state.inventory, 
        num_rows="dynamic", 
        use_container_width=True
    )
    
    st.divider()
    st.subheader("소모품 교체 알림")
    supplies = pd.DataFrame([
        {"품목": "칫솔(정원)", "최근교체": "2026-02-01", "주기": 30},
        {"품목": "면도날", "최근교체": "2026-02-10", "주기": 14}
    ])
    st.table(supplies.set_index("품목"))

# --- [9. 시스템 하단] ---
st.divider()
if st.button("캐시 클리어 및 시스템 리셋"):
    st.cache_data.clear()
    st.rerun()
