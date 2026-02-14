import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532", "Health": "123456789"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 데이터 보존
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

# --- [2. 유틸리티 함수] ---
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

# --- [3. 메인 화면 구성] ---
st.set_page_config(page_title="JARVIS v37.0", layout="wide")

st.markdown("""
    <style>
    .stTable td { text-align: right !important; }
    [data-testid="stHorizontalBlock"] { gap: 2rem; }
    .stDataEditor { border: 1px solid #f0f2f6; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    /* 회색바 제거 */
    .input-card { background-color: transparent; padding: 0px; border: none; }
    /* 자산 총계 스타일 */
    .total-row { font-weight: bold; background-color: #f1f3f5; }
    </style>
""", unsafe_allow_html=True)

# 한국 시간 및 날씨
try:
    kst_now = datetime.now() + pd.Timedelta(hours=9)
    date_str = kst_now.strftime('%Y-%m-%d %H:%M')
    # 평택 날씨
    w_url = "https://api.open-meteo.com/v1/forecast?latitude=36.99&longitude=127.11&current_weather=true&timezone=auto"
    w_res = requests.get(w_url, timeout=1).json()
    temp = w_res['current_weather']['temperature']
    w_code = w_res['current_weather']['weathercode']
    icon = "☀️" if w_code <= 3 else "☁️" if w_code <= 48 else "🌧️" if w_code <= 80 else "❄️"
    weather_str = f"{icon} {temp}°C"
except:
    date_str = datetime.now().strftime('%Y-%m-%d')
    weather_str = "기상 정보 로딩 실패"

t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### 📅 {date_str} (KST) | {weather_str} (평택)")
with t_c2: st.markdown("<div style='text-align:right;'><b>SYSTEM STATUS: ONLINE (v37.0)</b></div>", unsafe_allow_html=True)

# --- [사이드바] ---
with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    
    st.divider()
    
    # [자산 탭] 입력창 사이드바 배치
    if menu == "투자 & 자산":
        st.subheader("💰 자산 변동 기록")
        with st.form("asset_input_sidebar"):
            t_choice = st.selectbox("구분", ["지출", "수입"])
            if t_choice == "지출":
                cats = ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "자산이동", "기타지출"]
            else:
                cats = ["급여", "금융소득", "자산이동", "기타"]
            c_choice = st.selectbox("카테고리", cats)
            a_input = st.number_input("금액(원)", min_value=0, step=1000)
            
            if st.form_submit_button("기록 저장", use_container_width=True):
                if a_input > 0:
                    if send_to_sheet(t_choice, c_choice, a_input, corpus="Finance"):
                        st.success("기록 완료"); st.rerun()

# --- [탭 1] 투자 & 자산 ---
if menu == "투자 & 자산":
    st.header("💰 투자 및 종합 자산 관리")
    
    try:
        df_assets = load_sheet_data(GID_MAP["Assets"])
        df_log = load_sheet_data(GID_MAP["Log"])
        
        # 데이터 전처리
        if not df_assets.empty:
            df_assets.columns = ["항목", "금액"]
            df_assets["val"] = df_assets["금액"].apply(to_numeric)
        
        # 로그 분석 (현금흐름 및 월별 추세)
        cash_diff, card_debt = 0, 0
        monthly_trend = {} 

        if not df_log.empty:
            df_log.columns = ["날짜", "구분", "항목", "수치"]
            for _, row in df_log.iterrows():
                val = to_numeric(row["수치"])
                date_ym = str(row["날짜"])[:7] # YYYY-MM
                
                # 현재 자산 가감
                if row["구분"] == "지출":
                    if row["항목"] == "자산이동": cash_diff -= val
                    else: card_debt += val
                elif row["구분"] == "수입":
                    if row["항목"] != "자산이동": cash_diff += val
                
                # 월별 추세 집계
                if date_ym not in monthly_trend: monthly_trend[date_ym] = {"수입": 0, "지출": 0}
                if row["구분"] == "수입" and row["항목"] != "자산이동": 
                    monthly_trend[date_ym]["수입"] += val
                elif row["구분"] == "지출" and row["항목"] != "자산이동":
                    monthly_trend[date_ym]["지출"] += val

        # 주식/코인 합산
        inv_rows = []
        for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
            for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
        
        df_total = pd.concat([df_assets, pd.DataFrame(inv_rows)], ignore_index=True)

        # 현금 업데이트
        if not df_total.empty:
            cash_idx = df_total[df_total['항목'].str.contains('현금', na=False)].index
            target_idx = cash_idx[0] if not cash_idx.empty else 0
            df_total.at[target_idx, "val"] += cash_diff

        # 카드 부채 추가
        if card_debt > 0: df_total = pd.concat([df_total, pd.DataFrame([{"항목": "카드값(미결제)", "val": -card_debt}])], ignore_index=True)

        # 자산/부채 분리
        a_df = df_total[df_total["val"] >= 0].copy()
        l_df = df_total[df_total["val"] < 0].copy()
        net_worth = a_df["val"].sum() - abs(l_df["val"].sum())

        # [그래프] 월별 흐름
        st.subheader("📉 월별 자산 흐름")
        if monthly_trend:
            trend_df = pd.DataFrame.from_dict(monthly_trend, orient='index').sort_index()
            st.line_chart(trend_df, color=["#4CAF50", "#FF4B4B"])
        else: st.info("데이터가 부족합니다.")
        
        st.divider()

        # [표] 자산 및 부채 (Total 오류 수정 완료)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("자산 (Assets)")
            if not a_df.empty:
                # 표시용 데이터프레임 생성 (컬럼 개수 오류 방지)
                disp_a = a_df[["항목", "val"]].copy()
                disp_a.loc["Total"] = ["합계", disp_a["val"].sum()] # 마지막 줄 추가
                disp_a["금액"] = disp_a["val"].apply(format_krw)
                st.dataframe(disp_a[["항목", "금액"]], use_container_width=True, hide_index=True)

        with c2:
            st.subheader("부채 (Liabilities)")
            if not l_df.empty:
                disp_l = l_df[["항목", "val"]].copy()
                disp_l.loc["Total"] = ["합계", disp_l["val"].sum()]
                disp_l["금액"] = disp_l["val"].apply(lambda x: format_krw(abs(x)))
                st.dataframe(disp_l[["항목", "금액"]], use_container_width=True, hide_index=True)
            else: st.success("부채가 없습니다.")

        st.markdown(f"<h2 style='text-align: right; color: #1E90FF;'>💎 순자산: {format_krw(net_worth)}</h2>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"⚠️ 에러 발생: {e}")

# --- [탭 2] 식단 & 건강 ---
elif menu == "식단 & 건강":
    st.header("🥗 실시간 영양 분석 리포트")
    try: d_day = (datetime(2026, 5, 30) - datetime.now()).days
    except: d_day = 0
    st.info(f"💍 결혼식까지 D-{d_day} | 현재 체중 125.00kg 기준 감량 모드")

    # 레이아웃 수정: 입력(왼쪽) / 요약(오른쪽)
    col_input, col_summary = st.columns([6, 4])

    with col_input:
        st.subheader("📝 영양 성분 상세 기록")
        with st.form("full_input"):
            in_w = st.number_input("오늘 체중 (kg / 변동 없으면 유지)", 0.0, 200.0, 125.0, step=0.1)
            st.markdown("---")
            c_in1, c_in2 = st.columns(2)
            with c_in1:
                in_kcal = st.number_input("칼로리 (kcal)", 0.0, step=10.0)
                in_carb = st.number_input("탄수화물 (g)", 0.0, step=1.0)
                in_sugar = st.number_input("당류 (g)", 0.0, step=1.0)
                in_na = st.number_input("나트륨 (mg)", 0.0, step=10.0)
            with c_in2:
                in_prot = st.number_input("단백질 (g)", 0.0, step=1.0)
                in_fat = st.number_input("지방 (g)", 0.0, step=1.0)
                in_fiber = st.number_input("식이섬유 (g)", 0.0, step=1.0)
                in_chol = st.number_input("콜레스테롤 (mg)", 0.0, step=10.0)

            st.write("")
            if st.form_submit_button("✅ 저장", use_container_width=True):
                if in_w > 0 and in_w != 125.0: send_to_sheet("건강", "체중", in_w, corpus="Health")
                nutri_map = {"칼로리": in_kcal, "탄수화물": in_carb, "단백질": in_prot, "지방": in_fat, "당": in_sugar, "식이섬유": in_fiber, "나트륨": in_na, "콜레스테롤": in_chol}
                saved_count = 0
                for key, val in nutri_map.items():
                    if val > 0:
                        send_to_sheet("식단", key, val, corpus="Health")
                        saved_count += 1
                if saved_count > 0: st.success(f"{saved_count}건 저장 완료"); st.rerun()

    with col_summary:
        st.subheader("📊 오늘의 요약")
        # 데이터 집계
        cur_nutri = {k: 0 for k in DAILY_GUIDE.keys()}
        today_str = datetime.now().strftime('%Y-%m-%d')
        current_kcal = 0
        try:
            df_log = load_sheet_data(GID_MAP["Log"])
            if not df_log.empty:
                df_today = df_log[df_log['날짜'].astype(str).str.contains(today_str, na=False)]
                for nut in cur_nutri.keys():
                    n_df = df_today[(df_today['구분'] == '식단') & (df_today['항목'] == nut)]
                    cur_nutri[nut] = n_df['수치'].apply(to_numeric).sum()
                current_kcal = cur_nutri["칼로리"]
        except: pass

        rem_kcal = DAILY_GUIDE["칼로리"]["val"] - current_kcal
        st.metric("남은 칼로리", f"{rem_kcal:.0f} kcal", delta=f"-{current_kcal:.0f} 섭취")
        st.progress(min(current_kcal / DAILY_GUIDE["칼로리"]["val"], 1.0))
        
        st.divider()
        for name in ["탄수화물", "단백질", "지방", "나트륨"]:
            val = cur_nutri[name]
            guide = DAILY_GUIDE[name]
            st.caption(f"{name} ({val:.0f}/{guide['val']}{guide['unit']})")
            st.progress(min(val / guide['val'], 1.0))
        
        st.divider()
        try:
            if not df_log.empty:
                w_df = df_log[(df_log["구분"] == "건강") & (df_log["항목"] == "체중")].copy()
                if not w_df.empty:
                    w_df["날짜"] = pd.to_datetime(w_df["날짜"])
                    w_df["수치"] = w_df["수치"].apply(to_numeric)
                    st.line_chart(w_df.set_index("날짜")[["수치"]].sort_index(), color="#FF4B4B", height=150)
        except: pass

# --- [탭 3] 재고 관리 ---
elif menu == "재고 관리":
    st.header("📦 식자재 및 생활용품 관리")
    col_left, col_right = st.columns([1, 1])
    
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
        
        # 수정사항 즉시 저장
        st.session_state.inventory = st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True, key="inv_editor")

    with col_right:
        st.subheader("⏰ 생활용품 교체")
        if 'supplies' not in st.session_state:
            st.session_state.supplies = pd.DataFrame([
                {"품목": "칫솔(보스)", "최근교체일": "2026-01-15", "주기": 30}, 
                {"품목": "칫솔(약혼녀)", "최근교체일": "2026-02-15", "주기": 30},
                {"품목": "면도날", "최근교체일": "2026-02-01", "주기": 14},
                {"품목": "수세미", "최근교체일": "2026-02-15", "주기": 30},
                {"품목": "정수기필터", "최근교체일": "2025-12-10", "주기": 120}
            ])
        
        st.session_state.supplies = st.data_editor(st.session_state.supplies, num_rows="dynamic", use_container_width=True, key="sup_editor")

        # 날짜 계산 (KeyError 및 포맷 에러 방지)
        try:
            calc_df = st.session_state.supplies.copy()
            # 컬럼명 통일 (주기 vs 주기(일))
            if '주기(일)' in calc_df.columns: calc_df.rename(columns={'주기(일)': '주기'}, inplace=True)
            if '주기' not in calc_df.columns: calc_df['주기'] = 30
            
            calc_df['최근교체일'] = pd.to_datetime(calc_df['최근교체일'], errors='coerce')
            calc_df['교체예정일'] = calc_df.apply(lambda x: x['최근교체일'] + pd.Timedelta(days=int(x['주기'])) if pd.notnull(x['최근교체일']) else pd.NaT, axis=1)
            
            st.caption("📅 교체 예정일 (자동 계산)")
            display_df = calc_df[['품목', '교체예정일']].copy()
            display_df['교체예정일'] = display_df['교체예정일'].dt.strftime('%Y-%m-%d').fillna("-")
            st.dataframe(display_df.set_index('품목'), use_container_width=True)
        except: pass
