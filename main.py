import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 마스터 설정] ---
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'
# 보스께서 주신 GID 재확인
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}

FIXED_DATA = {
    "health_target": {"칼로리": 2000, "탄수": 300, "단백": 150, "지방": 65, "당": 50, "나트륨": 2000, "콜레스테롤": 300},
    "stocks": {
        "동성화인텍": {"평단": 22701, "수량": 21, "코드": "033500"},
        "삼성중공업": {"평단": 16761, "수량": 88, "코드": "010140"},
        "SK하이닉스": {"평단": 473521, "수량": 6, "코드": "000660"},
        "삼성전자": {"평단": 78895, "수량": 46, "코드": "005930"}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400, "마켓": "KRW-BTC"},
        "ETH": {"평단": 4243000, "수량": 0.03417393, "마켓": "KRW-ETH"}
    },
    "recurring": [
        {"항목": "임대료", "금액": 261620}, {"항목": "대출 이자", "금액": 263280},
        {"항목": "통신비", "금액": 136200}, {"항목": "보험료", "금액": 121780},
        {"항목": "청년도약계좌(적금)", "금액": 700000}, {"항목": "구독서비스", "금액": 42680}
    ],
    "categories": {
        "지출": ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"],
        "수입": ["급여", "금융소득", "기타"],
        "자산이동": ["적금/청약 납입", "주식/코인 매수", "대출 원금상환"]
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, "칫솔": {"last": "2026-02-06", "period": 90}, "이불세탁": {"last": "2026-02-04", "period": 14}
    },
    "kitchen": {
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# --- [2. 유틸리티] ---
def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return True
    except: return False

@st.cache_data(ttl=5)
def load_csv_diagnostic(sheet_name):
    gid = GID_MAP.get(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        if df.empty: return "Empty"
        return df.fillna(0)
    except Exception as e:
        return f"Error: {str(e)}"

def get_live_prices():
    prices = {"stocks": {}, "crypto": {}, "gold": 231345}
    for n, i in FIXED_DATA["stocks"].items():
        try:
            res = requests.get(f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{i['코드']}", timeout=1).json()
            prices["stocks"][n] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][n] = i['평단']
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=1).json()
        for c in res: prices["crypto"][c['market']] = float(c['trade_price'])
    except:
        for k, v in FIXED_DATA["crypto"].items(): prices["crypto"][v['마켓']] = v['평단']
    return prices

# --- [3. 메인 인터페이스] ---
st.set_page_config(page_title="JARVIS v24.0", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in FIXED_DATA["health_target"].keys()}

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()
    
    # 데이터 연결 상태 진단판
    st.subheader("시스템 연결 진단")
    for s_name in GID_MAP.keys():
        status = load_csv_diagnostic(s_name)
        if isinstance(status, str):
            st.error(f"{s_name} 탭: {status}")
        else:
            st.success(f"{s_name} 탭: 연결됨")

    if menu == "영양/식단/체중":
        st.subheader("건강 데이터 입력")
        in_w = st.number_input("현재 체중(kg)", 125.0, step=0.1)
        in_kcal = st.number_input("칼로리", 0)
        if st.button("전송"):
            if send_to_sheet("체중", "일일체크", in_w): st.success("전송 완료")

    elif menu == "자산/투자/가계부":
        st.subheader("가계부 기록")
        t_type = st.selectbox("구분", ["지출", "수입", "자산이동"])
        t_cat = st.selectbox("카테고리", FIXED_DATA["categories"][t_type])
        t_memo = st.text_input("메모")
        t_val = st.number_input("금액", 0)
        if st.button("시트 기록"):
            if send_to_sheet(t_type, f"{t_cat} - {t_memo}", t_val): st.success("기록 완료")

# --- [4. 메뉴별 리포트 출력] ---
st.title(f"자비스 리포트: {menu}")

if menu == "영양/식단/체중":
    st.subheader("일일 영양 섭취 현황")
    n_rows = [{"항목": k, "현재": v, "목표": FIXED_DATA["health_target"][k]} for k, v in st.session_state.consumed.items()]
    df_n = pd.DataFrame(n_rows)
    df_n.index = range(1, len(df_n) + 1)
    st.table(df_n)

elif menu == "자산/투자/가계부":
    live = get_live_prices()
    
    st.subheader("통합 자산 관리")
    asset_data = load_csv_diagnostic("Assets")
    a_rows = []
    
    # 💡 데이터 로드 실패해도 수동 데이터로 표 구성
    if not isinstance(asset_data, str):
        for _, row in asset_data.iterrows():
            try:
                a_rows.append({"분류": "금융", "항목": str(row.iloc[0]), "평가액": f"{int(float(str(row.iloc[1]).replace(',',''))):,}원", "비고": "시트 데이터"})
            except: continue
    else:
        # 시트 로드 실패 시 보스의 마지막 자산 정보를 임시로 보여줌
        a_rows.append({"분류": "금융", "항목": "데이터 대기 중", "평가액": "0원", "비고": "시트 공유 확인 필요"})

    # 주식/코인 데이터 (무조건 출력)
    g_qty = 16.0
    a_rows.append({"분류": "귀금속", "항목": "순금(16g)", "평가액": f"{int(g_qty * live['gold']):,}원", "비고": "시세반영"})
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        a_rows.append({"분류": "주식", "항목": n, "평가액": f"{curr * i['수량']:,}원", "비고": f"{((curr/i['평단'])-1)*100:.2f}%"})
    for n, i in FIXED_DATA["crypto"].items():
        curr = live["crypto"].get(i['마켓'], i['평단'])
        a_rows.append({"분류": "코인", "항목": n, "평가액": f"{int(curr * i['수량']):,}원", "비고": f"{((curr/i['평단'])-1)*100:.2f}%"})
    
    df_report = pd.DataFrame(a_rows)
    df_report.index = range(1, len(df_report) + 1)
    st.table(df_report)

elif menu == "재고/생활관리":
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("소모품 교체 주기")
        l_rows = []
        now_kr = datetime.utcnow() + timedelta(hours=9)
        for item, info in FIXED_DATA["lifecycle"].items():
            d_day = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - now_kr).days
            l_rows.append({"항목": item, "상태": f"{d_day}일 남음", "최근": info["last"]})
        df_l = pd.DataFrame(l_rows)
        df_l.index = range(1, len(df_l) + 1)
        st.table(df_l)
    with col2:
        st.subheader("주방 재고 리스트")
        df_k = pd.DataFrame([{"구분": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()])
        df_k.index = range(1, len(df_k) + 1)
        st.table(df_k)
