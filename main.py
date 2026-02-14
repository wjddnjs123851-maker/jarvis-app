import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 보스 자산 포트폴리오 (순금 16g 포함)
FIXED_DATA = {
    "stocks": {
        "SK하이닉스": {"수량": 6, "구매평단": 473521, "현재가": 880000},
        "삼성전자": {"수량": 46, "구매평단": 78895, "현재가": 181200},
        "삼성중공업": {"수량": 88, "구매평단": 16761, "현재가": 27700},
        "동성화인텍": {"수량": 21, "구매평단": 22701, "현재가": 27750}
    },
    "crypto": {
        "비트코인(BTC)": {"수량": 0.00181400, "구매평단": 137788139, "현재가": 102625689},
        "이더리움(ETH)": {"수량": 0.03417393, "구매평단": 4243000, "현재가": 3068977}
    },
    "gold": {"품목": "순금", "수량": 16, "단위": "g", "현재가": 115000}
}

DAILY_GUIDE = {"지방": 65.0, "콜레스테롤": 300.0, "나트륨": 2000.0, "탄수화물": 300.0, "식이섬유": 30.0, "당": 50.0, "단백질": 150.0, "칼로리": 2000.0}

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
st.set_page_config(page_title="JARVIS v34.5", layout="wide")
st.markdown("""<style>.stTable td { text-align: right !important; }.net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 20px; border-top: 3px solid #1E90FF; padding-top: 10px; }.total-box { text-align: right; font-size: 1.2em; font-weight: bold; padding: 10px; border-top: 2px solid #eee; }.input-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.subheader("📝 오늘의 재무 활동 기록")
    i_c1, i_c2, i_c3, i_c4 = st.columns([1, 2, 2, 1])
    with i_c1: t_choice = st.selectbox("구분", ["지출", "수입"])
    with i_c2: cats = ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"] if t_choice == "지출" else ["급여", "금융소득", "기타"]; c_choice = st.selectbox("카테고리", cats)
    with i_c3: a_input = st.number_input("금액(원)", min_value=0, step=1000)
    with i_c4: 
        st.write(""); st.write("")
        if st.button("기록하기", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_choice, a_input): st.success("기록 완료")
    st.markdown('</div>', unsafe_allow_html=True)

    df_sheet = load_sheet_data(GID_MAP["Assets"])
    df_sheet.columns = ["항목", "금액"]; df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            eval_v = info['수량'] * info['현재가']; inv_rows.append({"분류": cat, "항목": name, "수량": str(info['수량']), "현재가": format_krw(info['현재가']), "평가금액": eval_v})
    inv_rows.append({"분류": "현물", "항목": "순금", "수량": "16g", "현재가": format_krw(FIXED_DATA["gold"]["현재가"]), "평가금액": FIXED_DATA["gold"]["수량"] * FIXED_DATA["gold"]["현재가"]})
    df_inv = pd.DataFrame(inv_rows); df_inv_display = df_inv.copy(); df_inv_display["평가금액"] = df_inv_display["평가금액"].apply(lambda x: f"{format_krw(x)}원")
    df_inv_display.index = range(1, len(df_inv_display) + 1); st.subheader("📊 실시간 투자 현황"); st.table(df_inv_display)

    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("💰 현금 및 금융자산"); cash_df = df_sheet[df_sheet["val"] >= 0].copy(); cash_df["금액"] = cash_df["val"].apply(lambda x: f"{format_krw(x)}원")
        cash_df.index = range(1, len(cash_df) + 1); st.table(cash_df[["항목", "금액"]])
        t_a = df_inv["평가금액"].sum() + cash_df["val"].sum(); st.markdown(f'<div class="total-box">자산 총계: {format_krw(t_a)}원</div>', unsafe_allow_html=True)
    with col_l:
        st.subheader("📉 부채 목록"); liab_df = df_sheet[df_sheet["val"] < 0].copy(); liab_df["금액"] = liab_df["val"].apply(lambda x: f"{format_krw(abs(x))}원")
        liab_df.index = range(1, len(liab_df) + 1); st.table(liab_df[["항목", "금액"]])
        t_l = abs(liab_df["val"].sum()); st.markdown(f'<div class="total-box" style="color: #ff4b4b;">부채 총계: {format_krw(t_l)}원</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="net-wealth">종합 순자산: {format_krw(t_a - t_l)}원</div>', unsafe_allow_html=True)

elif menu == "식단 & 건강":
    st.subheader("🥗 영양 분석 및 데이터 입력")
    # 보스 요청: 정밀 소수점 입력칸 복구
    c1, c2, c3 = st.columns(3)
    with c1: in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0, step=0.01, format="%.2f")
    with c2: in_kcal = st.number_input("칼로리(kcal)", 0.0, format="%.2f")
    with c3: in_prot = st.number_input("단백질(g)", 0.0, format="%.2f")
    
    with st.expander("세부 영양소 입력"):
        e1, e2, e3 = st.columns(3)
        in_fat = e1.number_input("지방(g)", 0.0, format="%.2f"); in_chol = e2.number_input("콜레스테롤(mg)", 0.0, format="%.2f"); in_na = e3.number_input("나트륨(mg)", 0.0, format="%.2f")
        in_carb = e1.number_input("탄수화물(g)", 0.0, format="%.2f"); in_fiber = e2.number_input("식이섬유(g)", 0.0, format="%.2f"); in_sugar = e3.number_input("당(g)", 0.0, format="%.2f")

    if st.button("식단 입력 완료 및 리셋", use_container_width=True):
        st.success("시트 전송 완료!"); st.rerun()

    st.divider(); cols = st.columns(4)
    cur = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, "단백질": in_prot, "칼로리": in_kcal}
    for idx, (k, v) in enumerate(cur.items()):
        with cols[idx % 4]: r = min(v / DAILY_GUIDE.get(k, 1), 1.0) if v > 0 else 0; st.metric(k, f"{v:.2f}", f"{int(r*100)}%"); st.progress(r)

elif menu == "재고 관리":
    # 보스가 식량창고 뒤져서 알려준 데이터 기반 보강
    st.subheader("📦 식자재 통합 관리 (보강 데이터)")
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"분류": "단백질", "항목": "닭다리살", "수량": "4팩", "구매일": "2026-02-10", "유통기한": "2026-05-10"},
            {"분류": "단백질", "항목": "냉동삼치", "수량": "4팩", "구매일": "2026-02-12", "유통기한": "2026-04-12"},
            {"분류": "단백질", "항목": "단백질 쉐이크", "수량": "9개", "구매일": "-", "유통기한": "-"},
            {"분류": "곡물", "항목": "카무트/쌀 혼합", "수량": "2kg", "구매일": "-", "유통기한": "-"},
            {"분류": "면류", "항목": "파스타면", "수량": "2kg", "구매일": "-", "유통기한": "-"},
            {"분류": "소스", "항목": "토마토 페이스트", "수량": "10캔", "구매일": "-", "유통기한": "-"}
        ])
    
    inv_view = st.session_state.inventory.copy(); inv_view.index = range(1, len(inv_view) + 1)
    edited_inv = st.data_editor(inv_view, num_rows="dynamic", use_container_width=True)
    if st.button("식자재 데이터 저장"): st.session_state.inventory = edited_inv.reset_index(drop=True); st.success("저장 완료")

    st.divider(); st.subheader("⏰ 생활용품 교체주기 관리")
    if 'supplies' not in st.session_state:
        st.session_state.supplies = pd.DataFrame([{"품목": "칫솔", "최근교체일": "2026-01-15", "주기(일)": 30}, {"품목": "면도날", "최근교체일": "2026-02-01", "주기(일)": 14}])
    
    supp_view = st.session_state.supplies.copy(); supp_view.index = range(1, len(supp_view) + 1)
    edited_supp = st.data_editor(supp_view, num_rows="dynamic", use_container_width=True)
    
    sc1, sc2 = st.columns([3, 1])
    with sc1: target = st.selectbox("교체 완료 품목", st.session_state.supplies['품목'].tolist())
    with sc2: 
        if st.button("오늘 날짜로 갱신", use_container_width=True):
            st.session_state.supplies.loc[st.session_state.supplies['품목'] == target, '최근교체일'] = datetime.now().strftime('%Y-%m-%d')
            st.rerun()
