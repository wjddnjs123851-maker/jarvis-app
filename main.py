import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"Log": "0", "Finance": "0", "Assets": "1068342666", "Health": "123456789"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 색상 팔레트 (화이트톤 기반)
COLOR_ASSET = "#4dabf7" # 파랑
COLOR_DEBT = "#ff922b"  # 주황
COLOR_BG_LIGHT = "#ffffff"
COLOR_TEXT_DARK = "#212529"

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

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}".rjust(15) + " 원"

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

# --- [3. 메인 레이아웃] ---
st.set_page_config(page_title="JARVIS v41.2", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG_LIGHT}; color: {COLOR_TEXT_DARK}; }}
    [data-testid="stMetricValue"] {{ text-align: right !important; color: {COLOR_TEXT_DARK}; }}
    [data-testid="stTable"] td {{ text-align: right !important; }}
    .net-wealth-card {{ background-color: #f8f9fa; padding: 25px; border-radius: 12px; border: 2px solid {COLOR_ASSET}; margin-bottom: 30px; }}
    .stSidebar {{ background-color: #f1f3f5 !important; }}
    h1, h2, h3 {{ color: {COLOR_TEXT_DARK} !important; }}
    </style>
""", unsafe_allow_html=True)

t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### {datetime.now().strftime('%Y-%m-%d')} | 평택(KST)")
with t_c2: st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold;'>SYSTEM STATUS: ONLINE (v41.2)</div>", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 투자 & 자산] ---
if menu == "투자 & 자산":
    st.header("투자 및 종합 자산 관리")
    
    with st.expander("신규 내역 기록", expanded=True):
        f_c1, f_c2, f_c3 = st.columns([1, 2, 1])
        with f_c1: t_choice = st.selectbox("구분", ["지출", "수입"])
        with f_c2: 
            cats = ["식비", "생활용품", "건강", "주거/통신", "교통", "보험", "결혼준비", "자산이동", "기타"] if t_choice == "지출" else ["급여", "금융소득", "자산이동", "기타"]
            c_choice = st.selectbox("카테고리", cats)
        with f_c3: a_input = st.number_input("금액(원)", min_value=0, step=1000)
        if st.button("내역 전송", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_choice, a_input, corpus="Finance"): st.rerun()

    df_assets = load_sheet_data(GID_MAP["Assets"])
    df_log = load_sheet_data(GID_MAP["Log"])
    
    if not df_assets.empty:
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
    
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

    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
    
    df_total = pd.concat([df_assets, pd.DataFrame(inv_rows)], ignore_index=True)
    if not df_total.empty: df_total.iloc[0, df_total.columns.get_loc("val")] += cash_diff
    if card_debt > 0: df_total = pd.concat([df_total, pd.DataFrame([{"항목": "카드값(미결제)", "val": -card_debt}])], ignore_index=True)

    a_df, l_df = df_total[df_total["val"] >= 0].copy(), df_total[df_total["val"] < 0].copy()
    net_worth = a_df["val"].sum() - abs(l_df["val"].sum())

    st.markdown(f"""<div class="net-wealth-card"><small>통합 순자산 (Net Worth)</small><br><span style="font-size:2.5em; color:{COLOR_ASSET}; font-weight:bold;">{format_krw(net_worth)}</span></div>""", unsafe_allow_html=True)

    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("자산 현황")
        st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        st.metric("자산 총계", format_krw(a_df["val"].sum()))
    with col_l:
        st.subheader("부채 현황")
        if not l_df.empty:
            st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
        else: st.write("현재 부채가 없습니다.")
        st.metric("부채 총계", format_krw(abs(l_df["val"].sum())), delta_color="inverse")
        # --- [5. 식단 & 건강 로직] ---
elif menu == "식단 & 건강":
    st.header("영양 분석 리포트")
    
    # 상단 요약 바 (디데이 제거)
    st.markdown(f"""
        <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid {COLOR_ASSET}; margin-bottom:20px;'>
            <span style='color:gray;'>관리 시작 체중</span> <b>125.0kg</b> | 
            <span style='color:gray;'>현재 시스템 상태</span> <b>집중 감량 모드</b>
        </div>
    """, unsafe_allow_html=True)

    c_in, c_sum = st.columns([6, 4])
    
    with c_in:
        st.subheader("데이터 기록")
        with st.form("health_form"):
            in_w = st.number_input("체중 측정 (kg)", 50.0, 150.0, 125.0, step=0.1)
            st.divider()
            cc1, cc2 = st.columns(2)
            with cc1:
                in_kcal = st.number_input("칼로리 (kcal)", 0, 5000, 0)
                in_carb = st.number_input("탄수화물 (g)", 0, 500, 0)
                in_sugar = st.number_input("당류 (g)", 0, 200, 0)
            with cc2:
                in_prot = st.number_input("단백질 (g)", 0, 300, 0)
                in_fat = st.number_input("지방 (g)", 0, 200, 0)
                in_na = st.number_input("나트륨 (mg)", 0, 5000, 0)
            
            if st.form_submit_button("시스템 저장", use_container_width=True):
                # 체중 기록
                if in_w != 125.0: send_to_sheet("건강", "체중", in_w, corpus="Health")
                # 식단 기록
                nutri_map = {"칼로리": in_kcal, "탄수화물": in_carb, "단백질": in_prot, "지방": in_fat, "당": in_sugar, "나트륨": in_na}
                for k, v in nutri_map.items():
                    if v > 0: send_to_sheet("식단", k, v, corpus="Health")
                st.success("데이터가 기록되었습니다."); st.rerun()

    with c_sum:
        st.subheader("오늘의 영양 요약")
        df_log = load_sheet_data(GID_MAP["Log"])
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        cur_nutri = {k: 0 for k in DAILY_GUIDE.keys()}
        if not df_log.empty:
            df_log['날짜'] = df_log['날짜'].astype(str)
            df_today = df_log[df_log['날짜'].str.contains(today_str)]
            for k in cur_nutri.keys():
                cur_nutri[k] = df_today[(df_today['구분'] == '식단') & (df_today['항목'] == k)]['수치'].apply(to_numeric).sum()

        # 칼로리 분석
        kcal_val = cur_nutri["칼로리"]
        kcal_limit = DAILY_GUIDE["칼로리"]["val"]
        st.write(f"칼로리: {kcal_val:,.0f} / {kcal_limit:,.0f} kcal")
        st.progress(min(kcal_val / kcal_limit, 1.0))
        
        st.divider()
        # 주요 영양소 프로그레스 바
        for name in ["단백질", "탄수화물", "지방", "나트륨"]:
            val = cur_nutri[name]
            guide = DAILY_GUIDE[name]
            st.caption(f"{name} ({val:,.0f}{guide['unit']} / {guide['val']}{guide['unit']})")
            st.progress(min(val / guide['val'], 1.0))

# --- [6. 재고 관리 로직] ---
elif menu == "재고 관리":
    st.header("재고 및 교체 주기 관리")
    
    inv_c1, inv_c2 = st.columns(2)
    
    with inv_c1:
        st.subheader("식자재 재고 현황")
        if 'inventory' not in st.session_state:
            st.session_state.inventory = pd.DataFrame([
                {"항목": "냉동 삼치", "수량": "4팩", "비고": "26-05-10까지"},
                {"항목": "냉동닭다리살", "수량": "3팩", "비고": "냉동보관"},
                {"항목": "단백질 쉐이크", "수량": "9개", "비고": "초코맛"}
            ])
        st.session_state.inventory = st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True)

    with inv_c2:
        st.subheader("소모품 교체 주기")
        supplies = pd.DataFrame([
            {"품목": "칫솔(정원)", "최근교체": "2026-02-01", "주기": 30},
            {"품목": "칫솔(서진)", "최근교체": "2026-02-15", "주기": 30},
            {"품목": "면도날", "최근교체": "2026-02-10", "주기": 14}
        ])
        supplies['최근교체'] = pd.to_datetime(supplies['최근교체'])
        supplies['다음교체'] = supplies.apply(lambda x: x['최근교체'] + pd.Timedelta(days=x['주기']), axis=1)
        
        display_sup = supplies.copy()
        display_sup['다음교체'] = display_sup['다음교체'].dt.strftime('%Y-%m-%d')
        st.table(display_sup[['품목', '다음교체']].set_index('품목'))

# --- [7. 시스템 유지보수] ---
st.divider()
if st.button("시스템 리프레시", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
