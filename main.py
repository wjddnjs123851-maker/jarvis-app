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

# --- [2. 유틸리티 및 지능형 추론 함수] ---

def format_krw(val): 
    try: return f"{int(val):,}".rjust(15) + " 원"
    except: return "0 원"

def to_numeric(val):
    if pd.isna(val) or val == "": return 0
    s = re.sub(r'[^0-9.-]', '', str(val))
    try: return float(s) if '.' in s else int(s)
    except: return 0

def load_sheet_data(gid):
    ts = datetime.now().timestamp()
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

def infer_shelf_life(item_name):
    if any(k in item_name for k in ["케일", "잎", "시금치", "루꼴라", "허브", "고수", "샐러드"]): return 7
    elif any(k in item_name for k in ["파스닙", "뿌리", "비트", "마", "연근", "우엉", "감자", "당근", "양파"]): return 21
    elif any(k in item_name for k in ["고기", "살", "닭", "소", "돼지", "삼겹살", "목살", "생선", "회", "해산물"]): return 5
    elif any(k in item_name for k in ["약", "정", "제", "눈물", "시럽"]): return 730
    else: return 10

# --- [3. UI 스타일 및 세션 설정] ---
st.set_page_config(page_title="JARVIS v64.0", layout="wide")

if 'daily_nutri' not in st.session_state or set(st.session_state.daily_nutri.keys()) != set(RECOMMENDED.keys()):
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}

if 'maintenance' not in st.session_state:
    st.session_state.maintenance = [
        {"항목": "칫솔", "주기": 90, "마지막": "2025-11-20"},
        {"항목": "샤워기필터", "주기": 60, "마지막": "2026-01-10"}
    ]

# [정원 님 요청] 식재료 데이터 초기 대량 반영
if 'food_df_state' not in st.session_state:
    st.session_state.food_df_state = pd.DataFrame([
        {"품목": "계란", "수량": "15알", "기한": "2026-03-10"},
        {"품목": "삼겹살", "수량": "600g", "기한": "2026-02-23"},
        {"품목": "목살", "수량": "300g", "기한": "2026-02-23"},
        {"품목": "닭다리살", "수량": "1팩", "기한": "2026-02-23"},
        {"품목": "감자", "수량": "3개", "기한": "2026-03-15"},
        {"품목": "양파", "수량": "2개(대)", "기한": "2026-03-10"},
        {"품목": "고형 카레(S&B 아주매운맛)", "수량": "1박스", "기한": "2027-01-01"},
        {"품목": "봉지 라면류", "수량": "9봉", "기한": "2026-08-01"}
    ])

if 'med_df_state' not in st.session_state:
    st.session_state.med_df_state = pd.DataFrame([
        {"품목": "타이레놀", "수량": "8정", "기한": "2027-12-31"},
        {"품목": "인공눈물", "수량": "1박스", "기한": "2026-05-10"}
    ])

st.markdown(f"""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * {{ font-family: 'Pretendard', sans-serif !important; }}
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    .stButton>button {{
        background-color: #ffffff !important; color: #000000 !important;
        border: 1px solid #dee2e6 !important; border-radius: 8px; font-weight: bold; width: 100%; height: 3.5em;
    }}
    .net-box {{ background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; text-align: right; }}
    td {{ text-align: right !important; color: {COLOR_TEXT} !important; }}
    </style>
""", unsafe_allow_html=True)
# [전체 백업 및 시간 표시 섹션]
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
        if 'med_df_state' in st.session_state:
            for _, row in st.session_state.med_df_state.iterrows():
                backup_log.append(["의약품", row['품목'], f"{row['수량']} (기한:{row['기한']})"])
        
        success_count = 0
        for entry in backup_log:
            if send_to_sheet(now.date(), now.hour, entry[0], "백업", entry[1], 0, entry[2], corpus="Log"):
                success_count += 1
        
        if success_count > 0:
            st.success(f"총 {success_count}건 백업 완료")
        else:
            st.error("백업 오류")

# --- [사이드바 메뉴 시작] ---
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
        # [정원 님 요청] '외출/약속' 카테고리 추가
        c_main = st.selectbox("대분류", ["식비", "생활용품", "외출/약속", "월 구독료", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        method_choice = st.selectbox("결제 수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(MG+)", "현금", "계좌이체"])
        
        if st.button("시트 데이터 전송"):
            if a_input > 0:
                if send_to_sheet(sel_date, sel_hour, t_choice, c_main, content, a_input, method_choice):
                    # 가계부-재고 연동: 식비/생활용품 시 재고 목록 자동 추가
                    if t_choice == "지출" and c_main in ["식비", "생활용품"]:
                        p_date = (now + timedelta(days=infer_shelf_life(content))).strftime('%Y-%m-%d')
                        new_item = pd.DataFrame([{"품목": content, "수량": "1(자동)", "기한": p_date}])
                        st.session_state.food_df_state = pd.concat([st.session_state.food_df_state, new_item], ignore_index=True)
                    st.success("로그 기록 완료")
                    st.cache_data.clear(); st.rerun()

    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df = df_assets[df_assets["val"] > 0]
        l_df = df_assets[df_assets["val"] < 0]
        net_worth = a_df["val"].sum() + l_df["val"].sum()
        st.markdown(f"""<div class="net-box"><small>통합 순자산</small><br><span style="font-size:2.8em; font-weight:bold;">{net_worth:,.0f} 원</span></div>""", unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        with tc1: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_ASSET};'>자산 총계</small><br><h3 style='color:{COLOR_ASSET} !important;'>{a_df['val'].sum():,.0f} 원</h3></div>""", unsafe_allow_html=True)
        with tc2: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_DEBT};'>부채 총계</small><br><h3 style='color:{COLOR_DEBT} !important;'>{abs(l_df['val'].sum()):,.0f} 원</h3></div>""", unsafe_allow_html=True)
        st.divider()
        col1, col2 = st.columns(2)
        # [정원 님 요청] 인덱스 번호 삭제 (hide_index=True)
        with col1: 
            st.subheader("자산 내역")
            st.dataframe(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]], hide_index=True, use_container_width=True)
        with col2: 
            st.subheader("부채 내역")
            st.dataframe(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]], hide_index=True, use_container_width=True)

# --- [모듈 2: 식단 & 건강] ---
elif menu == "식단 & 건강":
    st.header("🥗 정밀 영양 분석 (목표: 2900 kcal)")
    with st.sidebar:
        st.subheader("식사 기록")
        with st.form("health_form"):
            f_in = {k: st.number_input(k, value=0.00, step=0.1) for k in RECOMMENDED.keys()}
            if st.form_submit_button("영양 데이터 추가"):
                for k in RECOMMENDED.keys(): st.session_state.daily_nutri[k] += f_in[k]
                st.rerun()
        if st.button("🏁 식단 리셋"):
            st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
            st.rerun()

    curr = st.session_state.daily_nutri
    hc1, hc2, hc3, hc4 = st.columns(4)
    with hc1: st.markdown(f"""<div class="net-box"><small>칼로리 잔여</small><br><h3>{max(0, 2900 - curr.get('칼로리', 0)):.0f} kcal</h3></div>""", unsafe_allow_html=True)
    with hc2: st.markdown(f"""<div class="net-box"><small>단백질 잔여</small><br><h3>{max(0, 170 - curr.get('단백질', 0)):.1f} g</h3></div>""", unsafe_allow_html=True)
    with hc3: st.markdown(f"""<div class="net-box"><small>식이섬유 잔여</small><br><h3>{max(0, 30 - curr.get('식이섬유', 0)):.1f} g</h3></div>""", unsafe_allow_html=True)
    with hc4: st.markdown(f"""<div class="net-box"><small>수분 잔여</small><br><h3>{max(0, 2000 - curr.get('수분(ml)', 0)):.0f} ml</h3></div>""", unsafe_allow_html=True)

    analysis_data = [{"영양소": k, "현재": f"{curr.get(k, 0):.2f}", "권장": f"{RECOMMENDED[k]:.2f}", "남은양": f"{max(0, RECOMMENDED[k]-curr.get(k, 0)):.2f}"} for k in RECOMMENDED.keys()]
    st.table(pd.DataFrame(analysis_data).set_index("영양소"))

# --- [모듈 3: 재고 & 교체관리] ---
elif menu == "재고 & 교체관리":
    st.header("🏠 스마트 물품 관리")
    today = datetime.utcnow() + timedelta(hours=9)
    st.subheader("🚨 수행 알림")
    if 'maintenance' in st.session_state:
        for item in st.session_state.maintenance:
            due = datetime.strptime(str(item["마지막"]), "%Y-%m-%d") + timedelta(days=int(item["주기"]))
            if (due - today).days <= 7:
                st.warning(f"**{item['항목']}**: {(due - today).days}일 남음 ({due.strftime('%Y-%m-%d')})")

    st.divider()
    st.subheader("🚀 지능형 품목 등록")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1: q_name = st.text_input("품목명", key="q_name")
    with c2: q_qty = st.text_input("수량", value="1", key="q_qty")
    with c3:
        p_date = (today + timedelta(days=infer_shelf_life(q_name))).strftime('%Y-%m-%d')
        if st.button("자동 추가"):
            new_item = {"품목": q_name, "수량": q_qty, "기한": p_date}
            if any(k in q_name for k in ["약", "정", "제", "눈물"]):
                st.session_state.med_df_state = pd.concat([st.session_state.med_df_state, pd.DataFrame([new_item])], ignore_index=True)
            else:
                st.session_state.food_df_state = pd.concat([st.session_state.food_df_state, pd.DataFrame([new_item])], ignore_index=True)
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["🍎 식재료", "💊 의약품", "⚙️ 일정"])
    with tab1:
        st.session_state.food_df_state = st.data_editor(st.session_state.food_df_state, num_rows="dynamic", use_container_width=True, key="f_ed")
    with tab2:
        st.session_state.med_df_state = st.data_editor(st.session_state.med_df_state, num_rows="dynamic", use_container_width=True, key="m_ed")
    with tab3:
        if 'mt_df' not in st.session_state: st.session_state.mt_df = pd.DataFrame(st.session_state.maintenance)
        st.session_state.mt_df = st.data_editor(st.session_state.mt_df, num_rows="dynamic", use_container_width=True, key="mt_ed")
        st.session_state.maintenance = st.session_state.mt_df.to_dict('records')
