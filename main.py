import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, date

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0",
    "Assets": "1068342666",
    "Finance": "0",
    "Health": "0"
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 색상 팔레트: 적녹색약 배려 (파랑/주황)
COLOR_GOOD = "#4dabf7" # 자산/수입
COLOR_BAD = "#ff922b"  # 부채/지출
COLOR_TEXT = "#fafafa"

DAILY_GUIDE = {
    "칼로리": {"val": 2900.0, "unit": "kcal"}, "지방": {"val": 90.0, "unit": "g"},
    "콜레스테롤": {"val": 300.0, "unit": "mg"}, "나트륨": {"val": 2300.0, "unit": "mg"},
    "탄수화물": {"val": 360.0, "unit": "g"}, "식이섬유": {"val": 30.0, "unit": "g"},
    "당": {"val": 50.0, "unit": "g"}, "단백질": {"val": 160.0, "unit": "g"}
}

FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46}, "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88}, "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400}, "ETH": {"평단": 4243000, "수량": 0.03417393}
    }
}

def format_krw(val): return f"{int(val):,}" + "원"
def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0
def send_to_sheet(d_type, item, value, date_val, corpus="Log"):
    d_str = date_val.strftime('%Y-%m-%d')
    payload = {"time": d_str, "corpus": corpus, "type": d_type, "item": item, "value": value}
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False
@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [2. UI 레이아웃 설정] ---
st.set_page_config(page_title="JARVIS v40.2", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e1117; color: {COLOR_TEXT}; }}
    [data-testid="stSidebar"] {{ background-color: #262730; }}
    [data-testid="stDataFrame"] table td:nth-child(2) {{ text-align: right !important; }}
    button[kind="secondaryFormSubmit"] {{ background-color: {COLOR_GOOD} !important; color: white !important; border: none !important; }}
    div[data-testid="stFormSubmitButton"] > button {{ background-color: {COLOR_GOOD} !important; color: white !important; border: none !important; }}
    .stNumberInput input, .stTextInput input, .stDateInput input {{ background-color: #e9ecef !important; color: black !important; font-weight: bold; }}
    .stSelectbox div[data-baseweb="select"] > div {{ background-color: #e9ecef !important; color: black !important; }}
    h1, h2, h3, p {{ color: {COLOR_TEXT} !important; }}
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    if menu == "투자 & 자산":
        st.subheader("💰 내역 입력")
        with st.form("input_form"):
            d_in = st.date_input("날짜", datetime.now())
            t_choice = st.selectbox("구분", ["지출", "수입"])
            cats = ["식비", "생활/마트", "주거/통신", "건강/의료", "교통/차량", "금융/보험", "경조사/선물", "취미/여가", "기타"] if t_choice == "지출" else ["급여", "금융소득", "자산이동", "기타수입"]
            c_choice = st.selectbox("카테고리", cats)
            item_in = st.text_input("상세 내용", "")
            a_input = st.number_input("금액(원)", min_value=0, step=1000)
            if st.form_submit_button("기록 저장", use_container_width=True):
                if a_input > 0:
                    f_item = f"{c_choice} - {item_in}" if item_in else c_choice
                    if send_to_sheet(t_choice, f_item, a_input, d_in, corpus="Finance"):
                        st.success("저장 완료"); st.rerun()

# --- [3. 메인 콘텐츠] ---
if menu == "투자 & 자산":
    st.header("💎 종합 자산 현황 (Net Worth)")
    try:
        df_assets = load_sheet_data(GID_MAP["Assets"])
        df_log = load_sheet_data(GID_MAP["Log"])
        
        # Assets 데이터 정제
        if not df_assets.empty:
            df_assets = df_assets.iloc[:, :2]
            df_assets.columns = ["항목", "금액"]
            df_assets["val"] = df_assets["금액"].apply(to_numeric)
        else: df_assets = pd.DataFrame(columns=["항목", "val"])

        # Log 데이터 분석
        monthly_trend = {}; new_card_debt = 0; df_clean = pd.DataFrame()
        if not df_log.empty:
            df_clean = df_log.iloc[:, [0, 1, 2, 4]].copy()
            df_clean.columns = ["날짜", "구분", "카테고리", "수치"]
            df_clean['날짜'] = pd.to_datetime(df_clean['날짜'].astype(str).str.replace('.', '-'), errors='coerce')
            for _, row in df_clean.iterrows():
                if pd.isna(row["날짜"]) or row["날짜"] < pd.Timestamp("2026-02-01"): continue
                val = to_numeric(row["수치"])
                date_ym = row["날짜"].strftime('%Y-%m')
                if row["구분"] == "지출": new_card_debt += val
                if date_ym not in monthly_trend: monthly_trend[date_ym] = {"수입": 0, "지출": 0}
                if row["구분"] == "수입": monthly_trend[date_ym]["수입"] += val
                else: monthly_trend[date_ym]["지출"] += val

        # 주식 데이터 병합
        inv_rows = []
        for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
            for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
        
        df_total = pd.concat([df_assets, pd.DataFrame(inv_rows)], ignore_index=True)
        if new_card_debt > 0:
            df_total = pd.concat([df_total, pd.DataFrame([{"항목": "💳 신규 카드사용액", "val": -new_card_debt}])], ignore_index=True)

        a_df = df_total[df_total["val"] >= 0].copy()
        l_df = df_total[df_total["val"] < 0].copy()
        net_worth = a_df["val"].sum() - abs(l_df["val"].sum())

        c_a, c_l, c_n = st.columns([1, 1, 0.8])
        with c_a:
            st.subheader("🔹 자산")
            st.metric("총 자산", format_krw(a_df["val"].sum()))
            st.dataframe(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]], use_container_width=True, hide_index=True)
        with c_l:
            st.subheader("🔸 부채")
            st.metric("총 부채", format_krw(l_df["val"].sum()))
            st.dataframe(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]], use_container_width=True, hide_index=True)
        with c_n:
            st.markdown(f"<div style='background-color:#1c1e26; padding:15px; border-radius:10px; text-align:center; border:1px solid {COLOR_GOOD};'>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin:0; color:gray;'>순자산</h3><h1 style='margin:0; color:{COLOR_GOOD};'>{format_krw(net_worth)}</h1></div>", unsafe_allow_html=True)

        st.divider()
        st.header("📊 월별 지출 분석 (Flow)")
        if monthly_trend:
            trend_df = pd.DataFrame.from_dict(monthly_trend, orient='index').sort_index()
            sel_month = st.selectbox("분석 월 선택", sorted(trend_df.index, reverse=True))
            inc, exp = monthly_trend[sel_month]["수입"], monthly_trend[sel_month]["지출"]
            m1, m2, m3 = st.columns(3)
            m1.metric("총 수입", format_krw(inc)); m2.metric("총 지출", format_krw(exp), delta_color="inverse"); m3.metric("월 수지", format_krw(inc-exp))
    except Exception as e: st.error(f"⚠️ 시스템 오류: {e}")

elif menu == "식단 & 건강":
    st.header("🥗 실시간 영양 분석 리포트")
    st.info(f"💍 결혼식까지 D-{(date(2026, 5, 30) - date.today()).days} | {st.session_state.get('user', '정원')}님 125kg 기준 감량 모드")
    col_in, col_sum = st.columns([6, 4])
    with col_in:
        with st.form("diet_form"):
            in_w = st.number_input("현재 체중 (kg)", 0.0, 200.0, 125.0, step=0.1)
            c1, c2 = st.columns(2)
            with c1:
                st.number_input("칼로리 (kcal)", 0.0); st.number_input("탄수화물 (g)", 0.0)
                st.number_input("당류 (g)", 0.0); st.number_input("나트륨 (mg)", 0.0)
            with c2:
                st.number_input("단백질 (g)", 0.0); st.number_input("지방 (g)", 0.0)
                st.number_input("식이섬유 (g)", 0.0); st.number_input("콜레스테롤 (mg)", 0.0)
            if st.form_submit_button("✅ 저장"): st.success("식단 저장 완료")

elif menu == "재고 관리":
    st.header("📦 식자재 및 생활용품 관리")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🛒 식재료 현황")
        inv = pd.DataFrame([
            {"항목": "냉동 삼치", "수량": "4팩", "유통기한": "2026-05-10"},
            {"항목": "냉동닭다리살", "수량": "3팩", "유통기한": "2026-06-01"},
            {"항목": "단백질 쉐이크", "수량": "9개", "유통기한": "2026-12-30"},
            {"항목": "카무트/쌀 혼합", "수량": "2kg", "유통기한": "2026-10-20"},
            {"항목": "파스타면", "수량": "대량", "유통기한": "-"},
            {"항목": "소면", "수량": "1봉", "유통기한": "-"},
            {"항목": "쿠스쿠스", "수량": "500g", "유통기한": "2027-01-01"},
            {"항목": "우동사리", "수량": "3봉", "유통기한": "-"},
            {"항목": "라면", "수량": "6봉", "유통기한": "-"},
            {"항목": "토마토 페이스트", "수량": "10캔", "유통기한": "2027-05-15"},
            {"항목": "김치 4종", "수량": "보유", "유통기한": "-"},
            {"항목": "당근", "수량": "보유", "유통기한": "-"},
            {"항목": "감자", "수량": "보유", "유통기한": "-"}
        ])
        st.data_editor(inv, use_container_width=True, hide_index=True)
    with c2:
        st.subheader("⏰ 생활용품 교체")
        # 호칭 수정: 정원(보스), 서진(약혼녀) 반영
        sup = pd.DataFrame([
            {"품목": "칫솔(정원)", "최근교체일": "2026-01-15", "주기": 30},
            {"품목": "칫솔(서진)", "최근교체일": "2026-02-15", "주기": 30},
            {"품목": "면도날", "최근교체일": "2026-02-01", "주기": 14},
            {"품목": "수세미", "최근교체일": "2026-02-15", "주ig": 30},
            {"품목": "정수기필터", "최근교체일": "2025-12-10", "주기": 120}
        ])
        st.data_editor(sup, use_container_width=True, hide_index=True)
