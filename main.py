import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {
    "Log": "0", "Assets": "1068342666", "Report": "308599580", "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

COLOR_ASSET = "#4dabf7"  
COLOR_DEBT = "#ff922b"   

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}".rjust(15) + " 원"
def to_numeric(val):
    try: 
        if pd.isna(val): return 0
        return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def send_to_sheet(d_type, cat_main, cat_sub, content, value, corpus="Log"):
    payload = {
        "time": datetime.now().strftime('%Y-%m-%d'),
        "corpus": corpus, "type": d_type, "cat_main": cat_main, 
        "cat_sub": cat_sub, "item": content, "value": value, 
        "method": "자비스", "user": "정원"
    }
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 레이아웃] ---
st.set_page_config(page_title="JARVIS v42.5", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; color: #212529; }}
    [data-testid="stMetricValue"] {{ text-align: right !important; }}
    [data-testid="stTable"] td {{ text-align: right !important; }}
    .net-box {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid {COLOR_ASSET}; margin-bottom: 25px; }}
    </style>
""", unsafe_allow_html=True)

t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Pyeongtaek")
with t_c2: st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold;'>JARVIS: ONLINE</div>", unsafe_allow_html=True)

# --- [4. 사이드바: 통합 제어 센터] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    
    if menu == "투자 & 자산":
        st.subheader("지출/수입 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        c_sub = st.text_input("소분류")
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        if st.button("전송", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input):
                st.success("데이터 전송 완료"); st.rerun()

# --- [5. 메인 화면: 투자 & 자산 대시보드 (100% 시트 연동)] ---
if menu == "투자 & 자산":
    st.header("종합 자산 관리 (시트 실시간 연동)")
    df_assets = load_sheet_data(GID_MAP["Assets"]) # Assets 탭 데이터
    df_log = load_sheet_data(GID_MAP["Log"])       # Log 탭 데이터
    
    cash_diff, card_debt = 0, 0
    if not df_log.empty:
        for _, row in df_log.iterrows():
            val = to_numeric(row.iloc[5]) 
            if row.iloc[1] == "지출":
                if row.iloc[2] == "자산이동": cash_diff -= val
                else: card_debt += val
            elif row.iloc[1] == "수입":
                if row.iloc[2] != "자산이동": cash_diff += val

    if not df_assets.empty:
        # 시트 컬럼: A(항목), B(금액)
        df_assets = df_assets.iloc[:, :2] 
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
    
        # 가용현금 항목에 이번 달 입출금 변동분 반영
        cash_idx = df_assets[df_assets['항목'] == '가용현금'].index
        if not cash_idx.empty: df_assets.at[cash_idx[0], 'val'] += cash_diff
    
    # 카드 미결제액(부채) 추가
    if card_debt > 0:
        df_assets = pd.concat([df_assets, pd.DataFrame([{"항목": "카드 미결제액", "val": -card_debt}])], ignore_index=True)

    a_df, l_df = df_assets[df_assets["val"] >= 0].copy(), df_assets[df_assets["val"] < 0].copy()
    net_worth = a_df["val"].sum() - abs(l_df["val"].sum())

    st.markdown(f"""<div class="net-box"><small>시트 연동 통합 순자산</small><br><span style="font-size:2.5em; color:{COLOR_ASSET}; font-weight:bold;">{format_krw(net_worth)}</span></div>""", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("보유 자산 내역")
        st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
    with c2:
        st.subheader("부채 관리")
        if not l_df.empty: st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
        st.metric("이번 달 지출 누계", format_krw(card_debt))
        # --- [6. 사이드바: 건강 및 재고 입력 섹션] ---
with st.sidebar:
    if menu == "식단 & 건강":
        st.subheader("영양 기록 (FatSecret 순서)")
        with st.form("health_input"):
            in_w = st.number_input("현재 체중 (kg)", 50.0, 150.0, 125.0, step=0.1)
            st.divider()
            in_kcal = st.number_input("칼로리 (kcal)", 0, 5000, 0)
            in_fat = st.number_input("지방 (g)", 0, 200, 0)
            in_chole = st.number_input("콜레스테롤 (mg)", 0, 1000, 0)
            in_na = st.number_input("나트륨 (mg)", 0, 5000, 0)
            in_carb = st.number_input("탄수화물 (g)", 0, 500, 0)
            in_fiber = st.number_input("식이섬유 (g)", 0, 100, 0)
            in_sugar = st.number_input("당 (g)", 0, 200, 0)
            in_prot = st.number_input("단백질 (g)", 0, 300, 0)
            
            if st.form_submit_button("기록 저장", use_container_width=True):
                send_to_sheet("건강", "기록", "체중", "정원", in_w, corpus="Health")
                nutris = {"칼로리": in_kcal, "지방": in_fat, "콜레스테롤": in_chole, "나트륨": in_na, "탄수화물": in_carb, "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot}
                for k, v in nutris.items():
                    if v > 0: send_to_sheet("식단", "영양소", k, "정원", v, corpus="Health")
                st.success("완료"); st.rerun()

    elif menu == "재고 관리":
        st.subheader("재고 추가")
        with st.form("inv_form"):
            inv_item = st.text_input("품목명")
            inv_qty = st.text_input("수량")
            inv_note = st.text_input("비고")
            if st.form_submit_button("추가"):
                new_item = pd.DataFrame([{"구분": "추가", "항목": inv_item, "수량": inv_qty, "비고": inv_note}])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_item], ignore_index=True)
                st.rerun()

# --- [7. 메인 화면: 식단 & 건강 대시보드] ---
if menu == "식단 & 건강":
    st.header("영양 섭취 분석")
    df_log = load_sheet_data(GID_MAP["Log"])
    today_str = datetime.now().strftime('%Y-%m-%d')
    NUTRI_ORDER = ["칼로리", "지방", "콜레스테롤", "나트륨", "탄수화물", "식이섬유", "당", "단백질"]
    
    cur_nutri = {k: 0 for k in NUTRI_ORDER}
    if not df_log.empty:
        df_today = df_log[df_log.iloc[:, 0].astype(str).str.contains(today_str)]
        for k in NUTRI_ORDER:
            cur_nutri[k] = df_today[(df_today.iloc[:, 1] == '식단') & (df_today.iloc[:, 3] == k)].iloc[:, 5].apply(to_numeric).sum()

    col_stat, col_vis = st.columns([5, 5])
    with col_stat:
        st.subheader("일일 섭취량")
        stat_data = [{"영양소": k, "현재량": f"{cur_nutri[k]:,.1f}"} for k in NUTRI_ORDER]
        st.table(pd.DataFrame(stat_data).set_index("영양소"))
    with col_vis:
        st.subheader("주요 영양소")
        for name in ["칼로리", "단백질", "탄수화물", "지방"]:
            val, target = cur_nutri[name], (2900 if name == "칼로리" else 160)
            st.caption(f"{name} ({val:,.1f} / {target:,.1f})")
            st.progress(min(val / target, 1.0) if target > 0 else 0)

# --- [8. 메인 화면: 재고 관리 (전체 데이터)] ---
elif menu == "재고 관리":
    st.header("재고 관리 시스템")
    if 'inventory' not in st.session_state:
        all_inventory = [
            {"구분": "상온", "항목": "올리브유/알룰로스/스테비아/사과식초", "수량": "보유", "비고": "-"},
            {"구분": "상온", "항목": "진간장/국간장/맛술/굴소스/저당케찹", "수량": "보유", "비고": "-"},
            {"구분": "상온", "항목": "하이라이스 가루/황설탕/고춧가루/후추", "수량": "보유", "비고": "-"},
            {"구분": "상온", "항목": "소금/통깨/김", "수량": "보유", "비고": "-"},
            {"구분": "곡물", "항목": "카무트/현미/쌀", "수량": "보유", "비고": "-"},
            {"구분": "냉장/냉동", "항목": "냉동 삼치/냉동 닭다리살", "수량": "4팩/3팩", "비고": "-"},
            {"구분": "냉장/냉동", "항목": "토마토 페이스트", "수량": "10캔", "비고": "2027-05-15"},
            {"구분": "냉장/냉동", "항목": "단백질 쉐이크", "수량": "9개", "비고": "-"},
            {"구분": "냉장/냉동", "항목": "계란/대파/양파/마늘/청양고추", "수량": "보유", "비고": "냉장"},
            {"구분": "냉장/냉동", "항목": "닭가슴살 스테이크", "수량": "보유", "비고": "냉동"}
        ]
        st.session_state.inventory = pd.DataFrame(all_inventory)
    st.session_state.inventory = st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True)

st.divider()
if st.button("새로고침", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
