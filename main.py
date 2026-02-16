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
# 정원 님이 새로 배포하신 API URL
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"

COLOR_BG = "#ffffff"
COLOR_TEXT = "#000000"
COLOR_ASSET = "#4dabf7" 
COLOR_DEBT = "#ff922b"  

# [정원 님 요청] 권장 칼로리 2900kcal 및 영양소 재설정
# [정원 님 요청] 수분(ml) 항목 추가 및 권장량 설정
# [정원 님 요청] 수분(ml) 포함 권장량 재설정
RECOMMENDED = {
    "칼로리": 2900, "지방": 70, "콜레스테롤": 300, "나트륨": 2300, 
    "탄수화물": 350, "식이섬유": 30, "당": 50, "단백질": 170, "수분(ml)": 2000
}

# 세션 상태 초기화 (항상 최신 RECOMMENDED 키값을 반영하도록 수정)
if 'daily_nutri' not in st.session_state or set(st.session_state.daily_nutri.keys()) != set(RECOMMENDED.keys()):
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
st.set_page_config(page_title="JARVIS v63.2", layout="wide")
st.markdown(f"""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * {{ font-family: 'Pretendard', sans-serif !important; }}
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    h1, h2, h3, p, span, label, div {{ color: {COLOR_TEXT} !important; }}
    
    .stButton>button {{
        background-color: #ffffff !important; color: #000000 !important;
        border: 1px solid #dee2e6 !important; border-radius: 8px; font-weight: bold; width: 100%; height: 3.5em;
    }}
    .stButton>button:hover {{ border-color: #000000 !important; background-color: #f8f9fa !important; }}
    
    input, select, div[data-baseweb="select"] {{
        outline: none !important; box-shadow: none !important; border: 1px solid #dee2e6 !important;
    }}

    .net-box {{ background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; text-align: right; }}
    td {{ text-align: right !important; color: {COLOR_TEXT} !important; }}
    th {{ color: #495057 !important; text-align: center !important; }}
    </style>
""", unsafe_allow_html=True)

# --- [3. 유틸리티 함수] ---
def format_krw(val): 
    return f"{{:,.0f}}".format(val).rjust(15) + " 원"

def to_numeric(val):
    if pd.isna(val) or val == "": return 0
    s = re.sub(r'[^0-9.-]', '', str(val))
    try: return float(s) if '.' in s else int(s)
    except: return 0

def load_sheet_data(gid):
    ts = datetime.now().timestamp()
    url = f"https://docs.google.com/spreadsheets/d/{{SPREADSHEET_ID}}/export?format=csv&gid={{gid}}&t={{ts}}".format(SPREADSHEET_ID=SPREADSHEET_ID, gid=gid, ts=ts)
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()
def send_to_sheet(d_date, d_hour, d_type, cat_main, content, value, method, corpus="Log"):
    full_time = f"{{d_date}} {{d_hour:02d}}시".format(d_date=d_date, d_hour=d_hour)
    payload = {
        "time": full_time, "corpus": corpus, "type": d_type, 
        "cat_main": cat_main, "cat_sub": "-", 
        "item": content, "value": value, "method": method, "user": "정원"
    }
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# [실시간 시간 반영] 매 로드마다 한국 시간 갱신
now = datetime.utcnow() + timedelta(hours=9)
st.markdown(f"### {{}} | JARVIS Prime".format(now.strftime('%Y-%m-%d %H:%M:%S')))

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
        c_main = st.selectbox("대분류", ["식비", "생활용품", "월 구독료", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        method_choice = st.selectbox("결제 수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(MG+)", "현금", "계좌이체"])
        
        if st.button("시트 데이터 전송"):
            if a_input > 0:
                if send_to_sheet(sel_date, sel_hour, t_choice, c_main, content, a_input, method_choice):
                    st.success("로그 기록 완료 (자산 동기화)")
                    st.cache_data.clear(); st.rerun()

    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]; df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df = df_assets[df_assets["val"] > 0]; l_df = df_assets[df_assets["val"] < 0]
        sum_asset = a_df["val"].sum(); sum_debt = l_df["val"].sum(); net_worth = sum_asset + sum_debt
        st.markdown(f"""<div class="net-box"><small>통합 순자산</small><br><span style="font-size:2.8em; font-weight:bold;">{{:,.0f}} 원</span></div>""".format(net_worth), unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        with tc1: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_ASSET};'>자산 총계</small><br><h3 style='color:{COLOR_ASSET} !important;'>{{:,.0f}} 원</h3></div>""".format(sum_asset), unsafe_allow_html=True)
        with tc2: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_DEBT};'>부채 총계</small><br><h3 style='color:{COLOR_DEBT} !important;'>{{:,.0f}} 원</h3></div>""".format(abs(sum_debt)), unsafe_allow_html=True)
        st.divider(); col1, col2 = st.columns(2)
        with col1: st.subheader("자산 내역"); st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with col2: st.subheader("부채 내역"); st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

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
        
        # [정원 님 요청] 완료 및 리셋 버튼
        if st.button("🏁 오늘의 식단 마감 및 리셋"):
            for k, v in st.session_state.daily_nutri.items():
                send_to_sheet(now.date(), now.hour, "식단", "건강", k, v, "자동기록", corpus="Health")
            st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
            st.success("데이터 초기화 완료!"); st.rerun()

    curr = st.session_state.daily_nutri
    # [정원 님 요청] 남은 양 계산 포함 데이터 구성
    curr = st.session_state.daily_nutri
    # 남은 양 계산 포함 데이터 구성 (KeyError 방지 로직 적용)
    analysis_data = []
    for k in RECOMMENDED.keys():
        # curr에 키가 없을 경우 0.0으로 기본값 설정
        current_val = curr.get(k, 0.0)
        rem = max(0, RECOMMENDED[k] - current_val)
        analysis_data.append({
            "영양소": k, 
            "현재 섭취": f"{current_val:.2f}", 
            "권장량": f"{RECOMMENDED[k]:.2f}", 
            "남은 양": f"{rem:.2f}"
        })
    health_df = pd.DataFrame(analysis_data)
    health_df.index = health_df.index + 1 # 순번 1번부터
    
    # 핵심 지표 상단 노출 (칼로리, 단백질, 식이섬유, 수분 강조)
    hc1, hc2, hc3, hc4 = st.columns(4)
    with hc1: st.markdown(f"""<div class="net-box"><small>칼로리 잔여</small><br><h3>{max(0, 2900 - curr['칼로리']):.0f} kcal</h3></div>""", unsafe_allow_html=True)
    with hc2: st.markdown(f"""<div class="net-box"><small>단백질 잔여</small><br><h3>{max(0, 170 - curr['단백질']):.1f} g</h3></div>""", unsafe_allow_html=True)
    with hc3: st.markdown(f"""<div class="net-box"><small>식이섬유 잔여</small><br><h3>{max(0, 30 - curr['식이섬유']):.1f} g</h3></div>""", unsafe_allow_html=True)
    with hc4: st.markdown(f"""<div class="net-box"><small>수분 잔여</small><br><h3>{max(0, 2000 - curr['수분(ml)']):.0f} ml</h3></div>""", unsafe_allow_html=True)

    curr = st.session_state.daily_nutri
    # 남은 양 계산 포함 데이터 구성
    analysis_data = []
    for k in RECOMMENDED.keys():
        rem = max(0, RECOMMENDED[k] - curr[k])
        analysis_data.append({
            "영양소": k, 
            "현재 섭취": f"{curr[k]:.2f}", 
            "권장량": f"{RECOMMENDED[k]:.2f}", 
            "남은 양": f"{rem:.2f}"
        })
    
    health_df = pd.DataFrame(analysis_data)
    health_df.index = health_df.index + 1
    st.table(health_df)

# --- [모듈 3: 재고 & 교체관리] ---
# --- [모듈 3: 재고 & 교체관리] ---
elif menu == "재고 & 교체관리":
    st.header("🏠 생활 시스템 및 물품 관리 (Direct Editor)")
    today = datetime.utcnow() + timedelta(hours=9)
    
    # [1. 교체 주기 및 정기 일정 관리]
    st.subheader("⚙️ 교체 및 정기 일정")
    st.caption("표의 셀을 더블클릭하여 내용을 수정하거나, 하단의 [+] 버튼으로 행을 추가하세요.")
    
    # 데이터프레임 초기화
    if 'maintenance_df' not in st.session_state:
        st.session_state.maintenance_df = pd.DataFrame(st.session_state.maintenance)

    # 엑셀식 에디터 적용
    edited_m_df = st.data_editor(
        st.session_state.maintenance_df,
        num_rows="dynamic", # 행 추가/삭제 가능
        use_container_width=True,
        key="m_editor"
    )
    
    # 변경사항 저장 버튼
    if st.button("💾 일정 변경사항 저장"):
        st.session_state.maintenance = edited_m_df.to_dict('records')
        st.session_state.maintenance_df = edited_m_df
        st.success("일정 수정사항이 반영되었습니다."); st.rerun()

    st.divider()

    # [2. 식재료 & 의약품 유통기한 관리]
    st.subheader("📦 식재료 & 의약품 유통기한 (상함 방지)")
    st.info("기한/상태 열을 더블클릭해서 수정하세요. 행 번호를 선택하고 Del키를 누르면 삭제됩니다.")

    if 'inv_df_state' not in st.session_state:
        # 기존 데이터를 데이터프레임으로 변환
        if 'custom_inventory' not in st.session_state:
            st.session_state.custom_inventory = [
                {"구분": "식재료", "품목": "라면", "기한/상태": "5봉지 (26-08-01)"},
                {"구분": "식재료", "품목": "닭다리살", "기한/상태": "500g (냉동)"},
                {"구분": "의약품", "품목": "타이레놀", "기한/상태": "8정 (27-12-31)"}
            ]
        st.session_state.inv_df_state = pd.DataFrame(st.session_state.custom_inventory)

    # 엑셀식 에디터 적용
    edited_inv_df = st.data_editor(
        st.session_state.inv_df_state,
        num_rows="dynamic", # 행 추가/삭제 가능
        use_container_width=True,
        column_config={
            "구분": st.column_config.SelectboxColumn("구분", options=["식재료", "의약품", "기타"], required=True),
        },
        key="inv_editor"
    )

    if st.button("💾 재고 변경사항 저장"):
        st.session_state.custom_inventory = edited_inv_df.to_dict('records')
        st.session_state.inv_df_state = edited_inv_df
        st.success("재고 리스트가 업데이트되었습니다."); st.rerun()

    # [3. 통합 알림 섹션]
    st.subheader("🚨 수행 필요 알림")
    for index, row in edited_m_df.iterrows():
        try:
            due = datetime.strptime(str(row["마지막"]), "%Y-%m-%d") + timedelta(days=int(row["주기"]))
            rem = (due - today).days
            if rem <= 7:
                st.warning(f"**{row['항목']}**: {rem}일 남음 ({due.strftime('%Y-%m-%d')})")
        except:
            continue
