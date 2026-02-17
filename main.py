import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0", 
    "Assets": "1068342666", 
    "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"

COLOR_BG = "#ffffff"
COLOR_TEXT = "#000000"
COLOR_ASSET = "#4dabf7"  
COLOR_DEBT = "#ff922b"   

RECOMMENDED = {
    "칼로리": 2900, "지방": 70, "콜레스테롤": 300, "나트륨": 2300, 
    "탄수화물": 350, "식이섬유": 30, "당": 50, "단백질": 170, "수분(ml)": 2000
}

# --- [2. 유틸리티 함수 (중복 제거 및 최적화)] ---
def format_krw(val): 
    return f"{int(val):,}".rjust(15) + " 원"

def to_numeric(val):
    if pd.isna(val) or val == "": return 0
    s = re.sub(r'[^0-9.-]', '', str(val))
    try: return float(s) if '.' in s else int(s)
    except: return 0

def load_sheet_data(gid):
    ts = datetime.now().timestamp()
    # f-string 중첩 오류 수정
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={ts}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(d_date, d_hour, d_type, cat_main, content, value, method, corpus="Log"):
    full_time = f"{d_date} {d_hour:02d}시"
    payload = {
        "time": full_time, "corpus": corpus, "type": d_type, 
        "cat_main": cat_main, "cat_sub": "-", 
        "item": content, "value": value, "method": method, "user": "정원"
    }
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# [지능형 추론] 이미지 데이터 기반 식재료 기한 로직 고도화
def infer_shelf_life(item_name):
    # 엽채류/신선식품 (이미지의 계란, 요거트, 채소류 등)
    if any(k in item_name for k in ["계란", "요거트", "우유", "케일", "루꼴라", "샐러드", "애호박"]):
        return 7
    # 뿌리채소 및 오래가는 신선식품 (이미지의 감자, 당근, 양파 등)
    elif any(k in item_name for k in ["감자", "당근", "양파", "파스닙", "비트"]):
        return 21
    # 육류/생선 (이미지의 삼겹살, 목살, 닭다리살, 삼치 등)
    elif any(k in item_name for k in ["삼겹살", "목살", "닭", "고기", "생선", "해산물"]):
        return 5
    # 냉동식품 (이미지의 냉동 베리, 우동사리, 사골육수 등)
    elif any(k in item_name for k in ["냉동", "우동사리", "만두"]):
        return 180
    # 실온/가공/양념 (이미지의 햇반, 라면, 토마토 페이스트, 고형 카레 등)
    elif any(k in item_name for k in ["햇반", "라면", "캔", "페이스트", "카레", "초콜릿", "미역"]):
        return 365
    # 의약품
    elif any(k in item_name for k in ["약", "정", "제", "눈물", "시럽"]):
        return 730
    return 14

# --- [3. UI 스타일 및 세션 설정] ---
st.set_page_config(page_title="JARVIS Prime v64.1", layout="wide")

# 세션 초기화 로직
# --- [수정된 초기화 로직: 파트 1의 해당 구간에 덮어쓰기] ---
if 'food_df_state' not in st.session_state:
    # 정원 님의 이미지 데이터를 기반으로 전체 리스트 자동 구성
    initial_food = [
        {"품목": "계란", "수량": "15알", "기한": (now + timedelta(days=7)).strftime('%Y-%m-%d')},
        {"품목": "그릭 요거트", "수량": "400g * 2개", "기한": (now + timedelta(days=7)).strftime('%Y-%m-%d')},
        {"품목": "우유(멸균)", "수량": "1L * 5개", "기한": (now + timedelta(days=14)).strftime('%Y-%m-%d')},
        {"품목": "삼겹살", "수량": "600g", "기한": (now + timedelta(days=5)).strftime('%Y-%m-%d')},
        {"품목": "목살", "수량": "300g", "기한": (now + timedelta(days=5)).strftime('%Y-%m-%d')},
        {"품목": "닭다리살", "수량": "1팩", "기한": (now + timedelta(days=5)).strftime('%Y-%m-%d')},
        {"품목": "감자", "수량": "3개", "기한": (now + timedelta(days=21)).strftime('%Y-%m-%d')},
        {"품목": "당근", "수량": "3개", "기한": (now + timedelta(days=21)).strftime('%Y-%m-%d')},
        {"품목": "애호박", "수량": "1개", "기한": (now + timedelta(days=7)).strftime('%Y-%m-%d')},
        {"품목": "양파", "수량": "2개(대)", "기한": (now + timedelta(days=21)).strftime('%Y-%m-%d')},
        {"품목": "사골육수", "수량": "2팩", "기한": (now + timedelta(days=180)).strftime('%Y-%m-%d')},
        {"품목": "냉동 생선(삼치)", "수량": "4마리", "기한": (now + timedelta(days=180)).strftime('%Y-%m-%d')},
        {"품목": "냉동 베리 믹스", "수량": "2kg", "기한": (now + timedelta(days=180)).strftime('%Y-%m-%d')},
        {"품목": "우동사리", "수량": "200g * 3봉", "기한": (now + timedelta(days=180)).strftime('%Y-%m-%d')},
        {"품목": "햇반", "수량": "1개", "기한": (now + timedelta(days=365)).strftime('%Y-%m-%d')},
        {"품목": "봉지 라면류", "수량": "9봉", "기한": (now + timedelta(days=365)).strftime('%Y-%m-%d')},
        {"품목": "토마토 페이스트", "수량": "170g * 10캔", "기한": (now + timedelta(days=365)).strftime('%Y-%m-%d')},
        {"품목": "고형 카레(S&B)", "수량": "1박스", "기한": (now + timedelta(days=365)).strftime('%Y-%m-%d')},
        {"품목": "라도유(리버스 시어링용)", "수량": "1개", "기한": (now + timedelta(days=365)).strftime('%Y-%m-%d')},
        {"품목": "미역", "수량": "50g", "기한": (now + timedelta(days=365)).strftime('%Y-%m-%d')}
    ]
    st.session_state.food_df_state = pd.DataFrame(initial_food)
# (이어서 2/3 파트에서 UI 구현부 제공 예정)
# --- [파트 2 시작] ---

# 세션 추가 초기화 (자산/식단용)
if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}

if 'med_df_state' not in st.session_state:
    st.session_state.med_df_state = pd.DataFrame([{"품목": "타이레놀", "수량": "8정", "기한": "2027-12-31"}])

if 'maintenance' not in st.session_state:
    st.session_state.maintenance = [
        {"항목": "칫솔", "주기": 90, "마지막": "2025-11-20"},
        {"항목": "샤워기필터", "주기": 60, "마지막": "2026-01-10"}
    ]

# [스타일 주입] 테이블 인덱스 숨기기 및 커스텀 디자인
st.markdown(f"""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * {{ font-family: 'Pretendard', sans-serif !important; }}
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    /* 테이블 인덱스(행 번호) 숨기기 */
    thead tr th:first-child {{ display:none; }}
    tbody th {{ display:none; }}
    .stButton>button {{
        background-color: #ffffff !important; color: #000000 !important;
        border: 1px solid #dee2e6 !important; border-radius: 8px; font-weight: bold; width: 100%; height: 3.5em;
    }}
    .net-box {{ background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ padding: 15px; border: 1px solid #eee; border-radius: 10px; background: #fafafa; }}
    </style>
""", unsafe_allow_html=True)

# [상단 바] 시간 및 백업
now = datetime.utcnow() + timedelta(hours=9)
top_col1, top_col2 = st.columns([3, 1])
with top_col1:
    st.markdown(f"### {now.strftime('%Y-%m-%d %H:%M:%S')} | JARVIS Prime")

with top_col2:
    if st.button("💾 전체 데이터 백업", use_container_width=True):
        backup_log = []
        if 'maintenance' in st.session_state:
            for m in st.session_state.maintenance:
                backup_log.append(["일정", m['항목'], f"주기:{m['주기']}, 마지막:{m['마지막']}"])
        if 'food_df_state' in st.session_state:
            for _, row in st.session_state.food_df_state.iterrows():
                backup_log.append(["식재료", row['품목'], f"{row['수량']} (기한:{row['기한']})"])
        
        success_count = 0
        for entry in backup_log:
            if send_to_sheet(now.date(), now.hour, entry[0], "백업", entry[1], 0, entry[2], corpus="Log"):
                success_count += 1
        if success_count > 0: st.success(f"{success_count}건 백업 완료")

# --- [사이드바 메뉴] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("SELECT MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])
    st.divider()

# --- [모듈 1: 투자 & 자산] ---
if menu == "투자 & 자산":
    st.header("📈 종합 자산 대시보드")
    with st.sidebar:
        st.subheader("데이터 입력")
        sel_date = st.date_input("날짜", value=now.date())
        sel_hour = st.slider("시간 (시)", 0, 23, now.hour)
        t_choice = st.selectbox("구분", ["지출", "수입"])
        # [정원 님 요청] '사회적 관계(친구)' 카테고리 추가
        c_main = st.selectbox("대분류", ["식비", "생활용품", "사회적 관계(친구)", "월 구독료", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        method_choice = st.selectbox("결제 수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(MG+)", "현금", "계좌이체"])
        
        if st.button("시트 데이터 전송"):
            if a_input > 0:
                if send_to_sheet(sel_date, sel_hour, t_choice, c_main, content, a_input, method_choice):
                    st.success("로그 기록 완료"); st.cache_data.clear(); st.rerun()

    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]; df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df = df_assets[df_assets["val"] > 0]; l_df = df_assets[df_assets["val"] < 0]
        
        net_worth = a_df["val"].sum() + l_df["val"].sum()
        st.markdown(f"""<div class="net-box"><small>통합 순자산</small><br><span style="font-size:2.8em; font-weight:bold;">{net_worth:,.0f} 원</span></div>""", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        # [정원 님 요청] 인덱스(번호) 없이 테이블 출력
        with col1: 
            st.subheader("자산 내역")
            st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with col2: 
            st.subheader("부채 내역")
            st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
            # --- [파트 3 시작: 189행] ---

# --- [모듈 2: 식단 & 건강] ---
elif menu == "식단 & 건강":
    st.header("🥗 정밀 영양 분석 (목표: 2900 kcal)")
    with st.sidebar:
        st.subheader("식사 기록")
        with st.form("health_form"):
            f_in = {k: st.number_input(k, value=0.00, step=0.01, format="%.2f") for k in RECOMMENDED.keys()}
            if st.form_submit_button("영양 데이터 추가"):
                for k in RECOMMENDED.keys(): st.session_state.daily_nutri[k] += f_in[k]
                st.rerun()
        
        if st.button("🏁 오늘의 식단 마감 및 리셋"):
            # 영양 데이터 시트 전송
            for k, v in st.session_state.daily_nutri.items():
                if v > 0:
                    send_to_sheet(now.date(), now.hour, "식단", "건강", k, v, "자동기록", corpus="Health")
            st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
            st.success("데이터 시트 전송 및 초기화 완료"); st.rerun()

    curr = st.session_state.daily_nutri
    hc1, hc2, hc3, hc4 = st.columns(4)
    with hc1: st.markdown(f"""<div class="net-box"><small>칼로리 잔여</small><br><h3>{max(0, 2900 - curr.get('칼로리', 0)):.0f} kcal</h3></div>""", unsafe_allow_html=True)
    with hc2: st.markdown(f"""<div class="net-box"><small>단백질 잔여</small><br><h3>{max(0, 170 - curr.get('단백질', 0)):.1f} g</h3></div>""", unsafe_allow_html=True)
    with hc3: st.markdown(f"""<div class="net-box"><small>식이섬유 잔여</small><br><h3>{max(0, 30 - curr.get('식이섬유', 0)):.1f} g</h3></div>""", unsafe_allow_html=True)
    with hc4: st.markdown(f"""<div class="net-box"><small>수분 잔여</small><br><h3>{max(0, 2000 - curr.get('수분(ml)', 0)):.0f} ml</h3></div>""", unsafe_allow_html=True)

    analysis_data = []
    for k in RECOMMENDED.keys():
        c_val = curr.get(k, 0.0)
        rem = max(0, RECOMMENDED[k] - c_val)
        analysis_data.append({"영양소": k, "현재 섭취": f"{c_val:.2f}", "권장량": f"{RECOMMENDED[k]:.2f}", "남은 양": f"{rem:.2f}"})
    
    st.table(pd.DataFrame(analysis_data))

# --- [모듈 3: 재고 & 교체관리] ---
elif menu == "재고 & 교체관리":
    st.header("🏠 생활 시스템 및 스마트 물품 관리")
    
    # 알림 섹션
    st.subheader("🚨 수행 필요 알림")
    alert_found = False
    if 'maintenance' in st.session_state:
        for item in st.session_state.maintenance:
            try:
                due = datetime.strptime(str(item["마지막"]), "%Y-%m-%d") + timedelta(days=int(item["주기"]))
                rem = (due - now).days
                if rem <= 7:
                    st.warning(f"**{item['항목']}**: {rem}일 남음 ({due.strftime('%Y-%m-%d')})")
                    alert_found = True
            except: continue
    if not alert_found: st.info("현재 임박한 교체 항목이 없습니다.")

    st.divider()
    
    # 지능형 등록 섹션 (이미지 기반 데이터 대응)
    st.subheader("🚀 지능형 품목 등록")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1: q_name = st.text_input("품목명 (이미지 내 품목 참고)", key="q_name")
    with c2: q_qty = st.text_input("수량/용량", value="1", key="q_qty")
    with c3:
        p_days = infer_shelf_life(q_name)
        p_date = (now + timedelta(days=p_days)).strftime('%Y-%m-%d')
        if st.button("JARVIS 분석 후 추가", use_container_width=True):
            if q_name:
                new_item = {"품목": q_name, "수량": q_qty, "기한": p_date}
                # 의약품 여부 판별 후 분기 저장
                if any(k in q_name for k in ["약", "정", "제", "눈물", "시럽"]):
                    st.session_state.med_df_state = pd.concat([st.session_state.med_df_state, pd.DataFrame([new_item])], ignore_index=True)
                else:
                    st.session_state.food_df_state = pd.concat([st.session_state.food_df_state, pd.DataFrame([new_item])], ignore_index=True)
                st.success(f"'{q_name}' 등록 완료 (권장 기한: {p_days}일)"); st.rerun()

    # 데이터 에디터 섹션
    tab1, tab2, tab3 = st.tabs(["🍎 식재료 관리", "💊 의약품 관리", "⚙️ 일정/주기 관리"])
    
    with tab1:
        # 정원 님 요청: 식재료 데이터도 시트와 연동 가능한 구조로 저장 버튼 배치
        edited_food = st.data_editor(st.session_state.food_df_state, num_rows="dynamic", use_container_width=True, key="f_ed")
        if st.button("💾 식재료 데이터 시트 백업"):
            st.session_state.food_df_state = edited_food
            success = 0
            for _, row in edited_food.iterrows():
                if send_to_sheet(now.date(), now.hour, "재고", "식재료", row['품목'], 0, f"{row['수량']}|기한:{row['기한']}", corpus="Log"):
                    success += 1
            st.success(f"{success}개 항목 시트 동기화 완료")

    with tab2:
        edited_med = st.data_editor(st.session_state.med_df_state, num_rows="dynamic", use_container_width=True, key="m_ed")
        if st.button("💾 의약품 데이터 저장"): 
            st.session_state.med_df_state = edited_med
            st.success("의약품 목록 업데이트 완료")

    with tab3:
        m_df = pd.DataFrame(st.session_state.maintenance)
        edited_m = st.data_editor(m_df, num_rows="dynamic", use_container_width=True, key="mt_ed")
        if st.button("💾 일정/주기 저장"):
            st.session_state.maintenance = edited_m.to_dict('records')
            st.success("교체 주기 업데이트 완료")
