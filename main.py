/** * 전문가용 통합 데이터 추출 함수
 */
function GET_ULTIMATE_DATA(code, type) {
  if (!code) return 0;
  var cleanCode = code.toString().match(/\d{6}/);
  if (!cleanCode) return 0;
  
  var url = "https://finance.naver.com/item/main.naver?code=" + cleanCode[0];
  try {
    var response = UrlFetchApp.fetch(url);
    var html = response.getContentText("EUC-KR");
    
    if (type === "PBR") return (html.match(/_pbr">([\d\.]+)<\/em>/) || [0,1])[1];
    if (type === "DIV") return (html.match(/_dvr">([\d\.]+)<\/em>/) || [0,0])[1];
    if (type === "ROE") return (html.match(/ROE.*?<td>([\d\.,]+)<\/td>/) || [0,10])[1].replace(/,/g,"");
    if (type === "DEBT") return (html.match(/부채비율.*?<td>([\d\.,]+)<\/td>/) || [0,100])[1].replace(/,/g,"");
    return 0;
  } catch (e) { return 0; }
}

/** * 전문가용 통합 스코어링 함수
 */
function CALCULATE_TOTAL_SCORE(pbr, div, roe, debt, usd, rate, category) {
  var score = (1/pbr) * 30 + (div * 5) + (roe * 2) - (debt / 50);
  if (category === "Export" && usd > 1400) score *= 1.2;
  if (category === "Finance" && rate > 4.0) score *= 1.3;
  if (category === "Growth" && rate > 4.0) score *= 0.7;
  return parseFloat(score).toFixed(2);
}
