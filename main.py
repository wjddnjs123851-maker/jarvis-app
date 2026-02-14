import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532", "Health": "123456789"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 일일 권장 가이드 (데이터 보존)
DAILY_GUIDE = {
    "칼로리": {"val": 2900.0, "unit": "kcal"}, "지방": {"val": 90.0, "unit": "g"},
    "콜레스테롤": {"val": 300.0, "unit": "mg"}, "나트륨": {"val": 2300.0, "unit": "mg"},
    "탄수화물": {"val": 360.0, "unit": "g"}, "식이섬유": {"val": 30.0, "unit": "g"},
    "당": {"val": 50.0, "unit": "g"}, "단백질": {"val": 160.0, "unit": "g"}
}

# 투자 자산 데이터 (데이터 보존)
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
def format_krw(val): return f"{int(val):,}" + "원"
def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def send_to_sheet(d_type, item, value, corpus="Log"):
    payload = {"time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "corpus": corpus, "type": d_type, "item": item, "value": value}
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정 및 상단 바] ---
st.set_page_config(page_title="JARVIS v35.8", layout="wide")
t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### {datetime.now().strftime('%Y-%m-%d')} | 8°C 맑음")
with t_c2: st.markdown("<div style='text-align:right;'>SYSTEM STATUS: ONLINE</div>", unsafe_allow_html=True)

st.markdown("""<style>.stTable td { text-align: right !important; }.total-display { text-align: right; font-size: 1.3em; font-weight: bold; padding: 15px; background: #f1f3f5; border-radius: 5px; margin-top: 5px; }.net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 25px; border-top: 3px solid #1E90FF; padding-top: 10px; }.input-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    # [식단 & 건강 입력창 유지]
    if menu == "식단 & 건강":
        st.subheader("영양소 입력")
        in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0, step=0.01, format="%.2f")
        in_kcal = st.number_input("칼로리 (kcal)", 0.0, format="%.2f")
        in_fat = st.number_input("지방 (g)", 0.0, format="%.2f")
        in_chol = st.number_input("콜레스테롤 (mg)", 0.0, format="%.2f")
        in_na = st.number_input("나트륨 (mg)", 0.0, format="%.2f")
        in_carb = st.number_input("탄수화물 (g)", 0.0, format="%.2f")
        in_fiber = st.number_input("식이섬유 (g)", 0.0, format="%.2f")
        in_sugar = st.number_input("당 (g)", 0.0, format="%.2f")
        in_prot = st.number_input("단백질 (g)", 0.0, format="%.2f")
        if st.button("데이터 전송 및 리셋"):
            nutri_map = {"칼로리": in_kcal, "지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot}
            for k, v in nutri_map.items(): 
                if v > 0: send_to_sheet("식단", k, v, corpus="Health")
            send_to_sheet("건강", "체중", in_w, corpus="Health")
            st.rerun()

# --- [4. 메인 화면 로직] ---
if menu == "투자 & 자산":
    st.header("투자 및 종합 자산 관리")
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    f_c1, f_c2, f_c3, f_c4 = st.columns([1, 2, 2, 1])
    with f_c1: t_choice = st.selectbox("구분", ["지출", "수입"])
    with f_c2:
        if t_choice == "지출":
            cats = ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "자산이동", "기타지출"]
        else:
            cats = ["급여", "금융소득", "자산이동", "기타"]
        c_choice = st.selectbox("카테고리", cats)
    with f_c3: a_input = st.number_input("금액(원)", min_value=0, step=1000)
    with f_c4: 
        st.write(""); st.write("")
        if st.button("기록"): 
            if a_input > 0 and send_to_sheet(t_choice, c_choice, a_input, corpus="Finance"): st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 자산 실시간 계산 로직 적용
    # 자산 데이터와 Log 데이터를 불러와서 실시간 계산
    df_assets = load_sheet_data(GID_MAP["Assets"])
    df_log = load_sheet_data(GID_MAP["Log"])
    
    if not df_assets.empty:
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
    
    # 실시간 변화량 변수
    cash_diff = 0    # 통장 잔고 변화
    card_debt = 0    # 카드값 부채 누적
    
    if not df_log.empty:
        df_log.columns = ["날짜", "구분", "항목", "수치"]
        for _, row in df_log.iterrows():
            val = to_numeric(row["수치"])
            if row["구분"] == "지출":
                if row["항목"] == "자산이동":
                    cash_diff -= val  # 자산이동(카드값변제 등) 시 현금 감소
                else:
                    card_debt += val  # 일반 지출 시 카드값 부채 증가
            elif row["구분"] == "수입":
                if row["항목"] != "자산이동":
                    cash_diff += val
    
    # 투자 자산 데이터 합치기
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
    
    # 전체 자산 통합
    df_total = pd.concat([df_assets, pd.DataFrame(inv_rows)], ignore_index=True)
    
    # 실시간 반영: 첫 번째 항목(현금/통장)에 변화량 더하기
    if not df_total.empty:
        df_total.iloc[0, df_total.columns.get_loc("val")] += cash_diff
    
    # 카드값 부채 항목 추가
    if card_debt > 0:
        df_total = pd.concat([df_total, pd.DataFrame([{"항목": "카드값(미결제)", "val": -card_debt}])], ignore_index=True)
    
    a_df, l_df = df_total[df_total["val"] >= 0].copy(), df_total[df_total["val"] < 0].copy()
    sum_a, sum_l = a_df["val"].sum(), abs(l_df["val"].sum())
    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("자산 내역"); a_df.index = range(1, len(a_df)+1)
        st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        st.markdown(f'<div class="total-display">자산총계: {format_krw(sum_a)}</div>', unsafe_allow_html=True)
    with col_l:
        st.subheader("부채 내역"); l_df.index = range(1, len(l_df)+1)
        st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
        st.markdown(f'<div class="total-display" style="color:#e03131;">부채총계: {format_krw(sum_l)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="net-wealth">종합 순자산: {format_krw(sum_a - sum_l)}</div>', unsafe_allow_html=True)

elif menu == "식단 & 건강":
    st.header("실시간 영양 분석 리포트")
    # (기존 식단 로직 전체 유지)
    st.warning(f"목표: 5월 30일 결혼식 전 체중 감량 (현재: 125.00kg)")
    cur_nutri = {"지방": 0, "콜레스테롤": 0, "나트륨": 0, "탄수화물": 0, "식이섬유": 0, "당": 0, "단백질": 0}
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("칼로리 요약")
        rem_kcal = DAILY_GUIDE["칼로리"]["val"]
        st.metric("남은 칼로리", f"{rem_kcal:.0f} kcal", delta="-0 섭취")
        st.progress(0.0)
    with c2:
        st.subheader("영양소 상세")
        for name, val in cur_nutri.items():
            guide = DAILY_GUIDE[name]; ratio = 0
            st.write(f"**{name}**: {val:.2f}{guide['unit']} / {guide['val']}{guide['unit']} (0%)")
            st.progress(0.0)

elif menu == "재고 관리":
    st.header("📦 식자재 및 생활용품 관리")
    
    # 화면을 6:4 비율로 쪼개기
    col_left, col_right = st.columns([6, 4])
    
    with col_left:
        st.subheader("🛒 식재료 현황")
        if 'inventory' not in st.session_state:
            st.session_state.inventory = pd.DataFrame([
                {"항목": "냉동 삼치", "수량": "4팩", "유통기한": "2026-05-10"}, {"항목": "냉동닭다리살", "수량": "3팩단위", "유통기한": "2026-06-01"},
                {"항목": "단백질 쉐이크", "수량": "9개", "유통기한": "2026-12-30"}, {"항목": "카무트/쌀 혼합", "수량": "2kg", "유통기한": "2026-10-20"},
                {"항목": "파스타면", "수량": "대량", "유통기한": "-"}, {"항목": "소면", "수량": "1봉", "유통기한": "-"},
                {"항목": "쿠스쿠스", "수량": "500g", "유통기한": "2027-01-01"}, {"항목": "우동사리", "수량": "3봉", "유통기한": "-"},
                {"항목": "라면", "수량": "6봉", "유통기한": "-"}, {"항목": "토마토 페이스트", "수량": "10캔", "유통기한": "2027-05-15"},
                {"항목": "나시고랭 소스", "수량": "1팩", "유통기한": "2026-11-20"}, {"항목": "치아씨드/아사이베리", "수량": "보유", "유통기한": "-"},
                {"항목": "김치 4종", "수량": "보유", "유통기한": "-"}, {"항목": "당근", "수량": "보유", "유통기한": "-"}, {"항목": "감자", "수량": "보유", "유통기한": "-"}
            ])
        inv_df = st.session_state.inventory.copy()
        inv_df.index = range(1, len(inv_df) + 1)
        st.data_editor(inv_df, num_rows="dynamic", use_container_width=True)

    with col_right:
        st.subheader("⏰ 생활용품 교체")
        if 'supplies' not in st.session_state:
            st.session_state.supplies = pd.DataFrame([
                {"품목": "칫솔", "최근교체일": "2026-02-15", "주기": 30}, 
                {"품목": "면도날", "최근교체일": "2026-02-01", "주기": 14},
                {"품목": "수세미", "최근교체일": "2026-02-15", "주기": 30},
                {"품목": "정수기필터", "최근교체일": "2025-12-10", "주기": 120}
            ])
        sup_df = st.session_state.supplies.copy()
        sup_df['최근교체일'] = pd.to_datetime(sup_df['최근교체일'])
        sup_df['교체예정일'] = sup_df.apply(lambda x: x['최근교체일'] + pd.Timedelta(days=x['주기']), axis=1)
        sup_df['최근교체일'] = sup_df['최근교체일'].dt.strftime('%Y-%m-%d')
        sup_df['교체예정일'] = sup_df['교체예정일'].dt.strftime('%Y-%m-%d')
        sup_df.index = range(1, len(sup_df) + 1)
        st.data_editor(sup_df, num_rows="dynamic", use_container_width=True)
