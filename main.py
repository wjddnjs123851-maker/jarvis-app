import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정 및 데이터 보존] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {
    "Log": "1716739583", 
    "Finance": "1790876407", 
    "Assets": "1666800532",
    "Health": "0",  # 예시 GID, 실제 시트 ID로 변경 가능
    "Stock": "123456" # 예시 GID
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# [중요] 보스 자산 데이터 (수정/삭제 절대 금지)
FIXED_DATA = {
    "stocks": {
        "SK하이닉스": {"수량": 6, "현재가": 880000},
        "삼성전자": {"수량": 46, "현재가": 181200},
        "삼성중공업": {"수량": 88, "현재가": 27700},
        "동성화인텍": {"수량": 21, "현재가": 27750}
    },
    "crypto": {
        "비트코인(BTC)": {"수량": 0.00181400, "현재가": 102625689},
        "이더리움(ETH)": {"수량": 0.03417393, "현재가": 3068977}
    },
    "gold": {"품목": "순금", "수량": 16, "단위": "g", "현재가": 115000}
}

# --- [2. 유틸리티 함수] ---
def format_krw(val): 
    return f"{int(val):,}"

def to_numeric(val):
    try:
        return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except:
        return 0

def send_to_sheet(d_type, item, value, note=""):
    now = datetime.now()
    payload = {
        "time": now.strftime('%Y-%m-%d %H:%M:%S'), 
        "type": d_type, 
        "item": item, 
        "value": value,
        "note": note
    }
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except:
        return False

def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all').reset_index(drop=True)
    except:
        return pd.DataFrame()

# --- [3. 메인 UI 설정] ---
st.set_page_config(page_title="JARVIS v34.9", layout="wide")

# CSS 스타일링
st.markdown("""
<style>
    .stTable td { text-align: right !important; }
    .net-wealth { font-size: 2.2em; font-weight: bold; color: #1E90FF; border-top: 3px solid #1E90FF; padding: 15px 0; }
    .total-box { text-align: right; font-size: 1.1em; font-weight: bold; padding: 10px; border-top: 1px solid #ddd; }
    .input-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 25px; }
    h3 { margin-bottom: 20px; color: #333; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ JARVIS Control")
    st.info(f"접속 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    menu = st.radio("메인 모듈 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    if st.button("데이터 강제 동기화"):
        st.cache_data.clear()
        st.rerun()

# --- [4. 탭별 로직 실행] ---

# 1번 탭: 투자 & 자산
if menu == "투자 & 자산":
    st.header("💰 자산 관리 시스템")
    
    # 지출/수입 입력 섹션
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.subheader("📝 일일 재무 기록")
    i_c1, i_c2, i_c3, i_c4 = st.columns([1, 2, 2, 1])
    with i_c1: 
        t_choice = st.selectbox("구분", ["지출", "수입"])
    with i_c2: 
        cats = ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타"] if t_choice == "지출" else ["급여", "금융소득", "중고판매", "기타"]
        c_choice = st.selectbox("항목명", cats)
    with i_c3: 
        a_input = st.number_input("금액(원)", min_value=0, step=1000, format="%d")
    with i_c4: 
        st.write("")
        if st.button("데이터 전송", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_choice, a_input):
                st.success("시트 반영 완료")
            else:
                st.error("전송 실패")
    st.markdown('</div>', unsafe_allow_html=True)

    # 투자 데이터 계산
    inv_rows = []
    for cat, items in {"국내주식": FIXED_DATA["stocks"], "가상자산": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            val = info['수량'] * info['현재가']
            inv_rows.append({"분류": cat, "종목명": name, "보유량": str(info['수량']), "현재가": format_krw(info['현재가']), "평가금액": val})
    
    gold_val = FIXED_DATA["gold"]["수량"] * FIXED_DATA["gold"]["현재가"]
    inv_rows.append({"분류": "실물자산", "종목명": "순금", "보유량": "16g", "현재가": format_krw(FIXED_DATA["gold"]["현재가"]), "평가금액": gold_val})
    
    df_inv = pd.DataFrame(inv_rows)
    df_inv_disp = df_inv.copy()
    df_inv_disp["평가금액"] = df_inv_disp["평가금액"].apply(lambda x: f"{format_krw(x)}원")
    df_inv_disp.index = range(1, len(df_inv_disp) + 1)
    
    st.subheader("📈 투자 포트폴리오")
    st.table(df_inv_disp)

    # 시트 데이터 로드 (현금/부채)
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    if not df_sheet.empty:
        df_sheet.columns = ["항목", "금액"]
        df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
        
        c_left, c_right = st.columns(2)
        with c_left:
            st.subheader("🏦 현금성 자산")
            cash_df = df_sheet[df_sheet["val"] >= 0].copy()
            cash_df["금액표기"] = cash_df["val"].apply(lambda x: f"{format_krw(x)}원")
            cash_df.index = range(1, len(cash_df) + 1)
            st.table(cash_df[["항목", "금액표기"]])
            
            total_assets = df_inv["평가금액"].sum() + cash_df["val"].sum()
            st.markdown(f'<div class="total-box">자산 총계: {format_krw(total_assets)}원</div>', unsafe_allow_html=True)

        with c_right:
            st.subheader("💳 부채 현황")
            liab_df = df_sheet[df_sheet["val"] < 0].copy()
            liab_df["금액표기"] = liab_df["val"].apply(lambda x: f"{format_krw(abs(x))}원")
            liab_df.index = range(1, len(liab_df) + 1)
            st.table(liab_df[["항목", "금액표기"]])
            
            total_liab = abs(liab_df["val"].sum())
            st.markdown(f'<div class="total-box" style="color: #ff4b4b;">부채 총계: {format_krw(total_liab)}원</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="net-
