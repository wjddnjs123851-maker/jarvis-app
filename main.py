import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {
    "Log": "0",            # 첫 번째 탭 (이미지 1)
    "Assets": "1068342666", # 자산 현황 (이미지 2)
    "Report": "308599580",  # 연간 리포트 (이미지 3)
    "Health": "123456789"   # 건강 데이터 (별도 관리)
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 화이트톤 디자인 가이드
COLOR_ASSET = "#4dabf7"  # 자산 (파랑)
COLOR_DEBT = "#ff922b"   # 부채 (주황)

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

def send_to_sheet(d_type, cat_main, cat_sub, content, value, corpus="Log"):
    # 가계부 2.0 시트 컬럼 순서: 날짜, 구분, 대분류, 소분류, 내용, 금액, 결제수단, 작성자
    payload = {
        "time": datetime.now().strftime('%Y-%m-%d'),
        "corpus": corpus,
        "type": d_type,       # 구분 (수입/지출)
        "cat_main": cat_main, # 대분류
        "cat_sub": cat_sub,   # 소분류
        "item": content,      # 내용
        "value": value,       # 금액
        "method": "자비스",    # 결제수단
        "user": "정원"         # 작성자
    }
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 레이아웃] ---
st.set_page_config(page_title="JARVIS v42.1", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; color: #212529; }}
    [data-testid="stMetricValue"] {{ text-align: right !important; }}
    [data-testid="stTable"] td {{ text-align: right !important; }}
    .net-wealth-box {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid {COLOR_ASSET}; margin-bottom: 25px; }}
    </style>
""", unsafe_allow_html=True)

# 상단 바: 시간 표시 문제 해결
t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 가계부 2.0 연동 중")
with t_c2: st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold;'>JARVIS: ONLINE</div>", unsafe_allow_html=True)

# --- [4. 사이드바: 통합 제어 센터] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    
    if menu == "투자 & 자산":
        st.subheader("가계부 데이터 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        c_sub = st.text_input("소분류 (예: 외식, 마트)")
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        
        if st.button("가계부 전송", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input):
                st.success("데이터 전송 완료"); st.rerun()

# --- [5. 메인 화면: 투자 & 자산 대시보드] ---
if menu == "투자 & 자산":
    st.header("투자 및 종합 자산 관리")
    
    # 데이터 로딩
    df_assets = load_sheet_data(GID_MAP["Assets"])
    df_log = load_sheet_data(GID_MAP["Log"])
    
    # 1. 시트 데이터 기반 자산 계산 (이미지 2번 구조 반영)
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, :2] # 항목, 금액(원) 컬럼만 사용
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
    
    # 2. 실시간 로그 반영 (이미지 1번 구조 반영)
    cash_diff, card_debt = 0, 0
    if not df_log.empty:
        # 컬럼: 날짜, 구분, 대분류, 소분류, 내용, 금액 ...
        for _, row in df_log.iterrows():
            val = to_numeric(row.iloc[5]) # 6번째 컬럼이 '금액'
            dtype = row.iloc[1]          # 2번째 컬럼이 '구분'
            main_cat = row.iloc[2]       # 3번째 컬럼이 '대분류'
            
            if dtype == "지출":
                if main_cat == "자산이동": cash_diff -= val
                else: card_debt += val
            elif dtype == "수입":
                if main_cat != "자산이동": cash_diff += val

    # 3. 통합 자산 산출
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
    
    df_final_assets = pd.concat([df_assets, pd.DataFrame(inv_rows)], ignore_index=True)
    
    # 가용현금(리스트 4번째 줄 추정) 보정 및 카드빚 추가
    if not df_final_assets.empty:
        cash_idx = df_final_assets[df_final_assets['항목'] == '가용현금'].index
        if not cash_idx.empty:
            df_final_assets.at[cash_idx[0], 'val'] += cash_diff
    
    if card_debt > 0:
        df_final_assets = pd.concat([df_final_assets, pd.DataFrame([{"항목": "카드 미결제액", "val": -card_debt}])], ignore_index=True)

    a_df, l_df = df_final_assets[df_final_assets["val"] >= 0].copy(), df_final_assets[df_final_assets["val"] < 0].copy()
    net_worth = a_df["val"].sum() - abs(l_df["val"].sum())

    # 순자산 디스플레이
    st.markdown(f"""<div class="net-wealth-box"><small>가계부 2.0 통합 순자산</small><br><span style="font-size:2.5em; color:{COLOR_ASSET}; font-weight:bold;">{format_krw(net_worth)}</span></div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("현재 자산 분포")
        st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
    with c2:
        st.subheader("부채 및 지출 관리")
        if not l_df.empty:
            st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
        st.metric("이번 달 누적 지출", format_krw(card_debt), delta_color="inverse")
        # --- [6. 사이드바: 건강 및 재고 입력 섹션 (추가)] ---
with st.sidebar:
    if menu == "식단 & 건강":
        st.subheader("신체 및 영양 기록")
        with st.form("health_input_form"):
            in_w = st.number_input("현재 체중 (kg)", 50.0, 150.0, 125.0, step=0.1)
            st.divider()
            # 팻시크릿(FatSecret) 표준 입력 순서 적용
            in_kcal = st.number_input("칼로리 (kcal)", 0, 5000, 0)
            in_prot = st.number_input("단백질 (g)", 0, 300, 0)
            in_carb = st.number_input("탄수화물 (g)", 0, 500, 0)
            in_fat = st.number_input("지방 (g)", 0, 200, 0)
            in_sugar = st.number_input("당류 (g)", 0, 200, 0)
            in_na = st.number_input("나트륨 (mg)", 0, 5000, 0)
            in_fiber = st.number_input("식이섬유 (g)", 0, 100, 0)
            in_chole = st.number_input("콜레스테롤 (mg)", 0, 1000, 0)
            
            if st.form_submit_button("건강 데이터 저장", use_container_width=True):
                # Health 시트 전송 (체중 및 영양소)
                send_to_sheet("건강", "기록", "체중", "정원", in_w, corpus="Health")
                nutris = {
                    "칼로리": in_kcal, "단백질": in_prot, "탄수화물": in_carb, 
                    "지방": in_fat, "당류": in_sugar, "나트륨": in_na, 
                    "식이섬유": in_fiber, "콜레스테롤": in_chole
                }
                for k, v in nutris.items():
                    if v > 0:
                        # API 구조에 맞춰 corpus="Health"로 개별 전송
                        send_to_sheet("식단", "영양소", k, "정원", v, corpus="Health")
                st.success("건강 데이터 기록 완료"); st.rerun()

    elif menu == "재고 관리":
        st.subheader("재고 업데이트")
        with st.form("inv_form"):
            inv_item = st.text_input("품목명")
            inv_qty = st.text_input("수량 및 상태")
            inv_note = st.text_input("유통기한/비고")
            if st.form_submit_button("재고 리스트 추가", use_container_width=True):
                new_item = pd.DataFrame([{"항목": inv_item, "수량": inv_qty, "비고": inv_note}])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_item], ignore_index=True)
                st.rerun()

# --- [7. 메인 화면: 식단 & 건강 대시보드] ---
if menu == "식단 & 건강":
    st.header("영양 섭취 및 신체 지표 분석")
    
    # 데이터 로드 (Health 관련 로그 필터링)
    df_log = load_sheet_data(GID_MAP["Log"]) # 실제 운영 시 Health GID 사용 권장
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 팻시크릿 순서 리스트
    NUTRI_ORDER = ["칼로리", "단백질", "탄수화물", "지방", "당류", "나트륨", "식이섬유", "콜레스테롤"]
    
    cur_nutri = {k: 0 for k in NUTRI_ORDER}
    if not df_log.empty:
        # 가계부 2.0 구조에 따라 6번째 컬럼(금액/수치) 활용
        df_today = df_log[df_log.iloc[:, 0].astype(str).str.contains(today_str)]
        for k in NUTRI_ORDER:
            # 구분(1번 컬럼)이 '식단'이고 소분류(3번 컬럼)가 영양소 명칭인 경우 합산
            cur_nutri[k] = df_today[(df_today.iloc[:, 1] == '식단') & (df_today.iloc[:, 3] == k)].iloc[:, 5].apply(to_numeric).sum()

    col_stat, col_vis = st.columns([5, 5])
    
    with col_stat:
        st.subheader("일일 영양 섭취 현황")
        # 팻시크릿 순서대로 데이터프레임 구성
        stat_data = []
        for k in NUTRI_ORDER:
            unit = "kcal" if k == "칼로리" else ("mg" if k in ["나트륨", "콜레스테롤"] else "g")
            stat_data.append({"영양소": k, "현재 섭취량": f"{cur_nutri[k]:,.1f} {unit}"})
        
        st.table(pd.DataFrame(stat_data).set_index("영양소"))

    with col_vis:
        st.subheader("주요 영양소 밸런스")
        for name in ["칼로리", "단백질", "탄수화물", "지방"]:
            val = cur_nutri[name]
            target = 2900 if name == "칼로리" else (160 if name == "단백질" else 150) # 정원님 목표치
            st.caption(f"{name} 충족률 ({val:,.1f} / {target:,.1f})")
            st.progress(min(val / target, 1.0) if target > 0 else 0)

# --- [8. 메인 화면: 재고 관리 대시보드] ---
elif menu == "재고 관리":
    st.header("식재료 및 소모품 관리 시스템")
    
    if 'inventory' not in st.session_state:
        # 정원님이 공유해주신 식재료 정보 초기 세팅
        st.session_state.inventory = pd.DataFrame([
            {"항목": "냉동 삼치", "수량": "4팩", "비고": "2026-05-10"},
            {"항목": "냉동닭다리살", "수량": "3팩", "비고": "냉동보관"},
            {"항목": "단백질 쉐이크", "수량": "9개", "비고": "초코맛"},
            {"항목": "카무트/쌀", "수량": "2kg", "비고": "-"},
            {"항목": "토마토 페이스트", "수량": "10캔", "비고": "2027-05-15"}
        ])

    st.subheader("현재 재고 리스트")
    # 메인 화면에서 직접 수정 가능 (수정 후 시트 동기화 버튼 추가 가능)
    st.session_state.inventory = st.data_editor(
        st.session_state.inventory, 
        num_rows="dynamic", 
        use_container_width=True
    )
    
    st.divider()
    st.subheader("생활 소모품 교체 주기")
    supplies = pd.DataFrame([
        {"품목": "칫솔(정원)", "최근교체": "2026-02-01", "주기(일)": 30},
        {"품목": "면도날", "최근교체": "2026-02-10", "주기(일)": 14},
        {"품목": "정수기 필터", "최근교체": "2025-12-10", "주기(일)": 120}
    ])
    st.table(supplies.set_index("품목"))

# --- [9. 시스템 종료 및 유지보수] ---
st.divider()
if st.button("전체 캐시 초기화 및 시스템 재시작", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
