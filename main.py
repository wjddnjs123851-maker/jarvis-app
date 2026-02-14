import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# [고정 데이터] 자산/부채 (순금 16g 포함)
FIXED_DATA = {
    "stocks": {
        "SK하이닉스": {"수량": 6, "현재가": 880000}, "삼성전자": {"수량": 46, "현재가": 181200},
        "삼성중공업": {"수량": 88, "현재가": 27700}, "동성화인텍": {"수량": 21, "현재가": 27750}
    },
    "crypto": {
        "비트코인(BTC)": {"수량": 0.00181400, "현재가": 102625689}, "이더리움(ETH)": {"수량": 0.03417393, "현재가": 3068977}
    },
    "gold": {"품목": "순금", "수량": 16, "현재가": 115000}
}

# [고정 지표] 영양소 8종 (지방, 콜레스테롤, 나트륨, 탄수화물, 식이섬유, 당, 단백질, 칼로리)
DAILY_GUIDE = {"지방": 65, "콜레스테롤": 300, "나트륨": 2000, "탄수화물": 300, "식이섬유": 30, "당": 50, "단백질": 150, "칼로리": 2000}

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}"
def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0
def send_to_sheet(d_type, item, value):
    now = datetime.now()
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정] ---
st.set_page_config(page_title="JARVIS v34.8", layout="wide")
st.markdown("""<style>.stTable td { text-align: right !important; }.net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 20px; border-top: 3px solid #1E90FF; padding-top: 10px; }.total-box { text-align: right; font-size: 1.2em; font-weight: bold; padding: 10px; border-top: 2px solid #eee; }.input-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["식단 & 건강", "투자 & 자산", "재고 관리"])
    st.divider()
    if menu == "식단 & 건강":
        st.subheader("데이터 입력")
        in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0, step=0.01, format="%.2f")
        in_fat = st.number_input("1. 지방 (g)", 0.0, format="%.2f")
        in_chol = st.number_input("2. 콜레스테롤 (mg)", 0.0, format="%.2f")
        in_na = st.number_input("3. 나트륨 (mg)", 0.0, format="%.2f")
        in_carb = st.number_input("4. 탄수화물 (g)", 0.0, format="%.2f")
        in_fiber = st.number_input("5. 식이섬유 (g)", 0.0, format="%.2f")
        in_sugar = st.number_input("6. 당 (g)", 0.0, format="%.2f")
        in_prot = st.number_input("7. 단백질 (g)", 0.0, format="%.2f")
        in_kcal = st.number_input("8. 칼로리 (kcal)", 0.0, format="%.2f")
        if st.button("식단 입력 완료 및 리셋", use_container_width=True):
            inputs = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot, "칼로리": in_kcal}
            for k, v in inputs.items():
                if v > 0: send_to_sheet("식단", k, v)
            send_to_sheet("건강", "체중", in_w); st.rerun()

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "식단 & 건강":
    st.subheader("실시간 영양 분석 리포트 (8종 전 지표)")
    cur_d = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot, "칼로리": in_kcal}
    cols = st.columns(4)
    for idx, (k, v) in enumerate(cur_d.items()):
        with cols[idx % 4]:
            r = min(v / DAILY_GUIDE[k], 1.0) if v > 0 else 0
            st.metric(k, f"{v:.2f} / {DAILY_GUIDE[k]}", f"{int(r*100)}%")
            st.progress(r)

elif menu == "투자 & 자산":
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.subheader("📝 오늘의 재무 활동 기록")
    i_c1, i_c2, i_c3, i_c4 = st.columns([1, 2, 2, 1])
    with i_c1: t_type = st.selectbox("구분", ["지출", "수입"])
    with i_c2: cats = ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"] if t_type == "지출" else ["급여", "금융소득", "기타"]; cat = st.selectbox("카테고리", cats)
    with i_c3: amt = st.number_input("금액(원)", min_value=0, step=1000)
    with i_c4: 
        st.write(""); st.write("")
        if st.button("기록하기", use_container_width=True):
            if amt > 0 and send_to_sheet(t_type, cat, amt): st.success("기록 완료")
    st.markdown('</div>', unsafe_allow_html=True)
    # 자산/부채 테이블 로직 유지... (v34.7과 동일)

elif menu == "재고 관리":
    st.subheader("📦 보강된 식량창고 데이터 (구매일/유통기한 포함)")
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"분류": "단백질", "항목": "닭가슴살", "수량": "12팩", "상태": "냉동", "구매일": "2026-02-10", "유통기한": "2026-05-10"},
            {"분류": "단백질", "항목": "계란", "수량": "6알", "상태": "냉장", "구매일": "2026-02-14", "유통기한": "2026-03-14"}
        ])
    inv_df = st.session_state.inventory.copy(); inv_df.index = range(1, len(inv_df) + 1)
    st.session_state.inventory = st.data_editor(inv_df, num_rows="dynamic", use_container_width=True)

    st.divider(); st.subheader("⏰ 생활/가사 교체주기 (예정일 자동계산)")
    if 'supplies' not in st.session_state:
        st.session_state.supplies = pd.DataFrame([{"항목": "칫솔", "최근교체일": "2026-02-01", "주기(일)": 30}, {"항목": "면도날", "최근교체일": "2026-02-10", "주기(일)": 14}, {"항목": "이불빨래", "최근교체일": "2026-02-01", "주기(일)": 14}])
    
    def calc_next(r):
        nxt = datetime.strptime(r['최근교체일'], '%Y-%m-%d') + timedelta(days=int(r['주기(일)']))
        return nxt.strftime('%Y-%m-%d'), (nxt - datetime.now()).days
    
    supp_v = st.session_state.supplies.copy()
    supp_v[['교체예정일', '잔여일']] = supp_v.apply(lambda r: pd.Series(calc_next(r)), axis=1)
    supp_v.index = range(1, len(supp_v) + 1); st.table(supp_v)
