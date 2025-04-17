import requests
import datetime
from bs4 import BeautifulSoup
from pytz import timezone
import openai

# ▼ 한국 시간
kst = timezone("Asia/Seoul")
now = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M")

# ▼ 키워드 리스트
keywords = [
    "해외선물", "나스닥", "금 선물", "파월", "CPI", "PPI", "FOMC",
    "미국 고용", "실업률", "트럼프", "연준", "금리", "GDP", "엔비디아", "ISM", "소비자신뢰지수"
]

# ▼ 사용할 뉴스 API 또는 RSS (MarketWatch RSS)
rss_url = "https://www.marketwatch.com/rss/topstories"

# ▼ RSS 가져오기
response = requests.get(rss_url)
soup = BeautifulSoup(response.content, features="xml")
items = soup.findAll("item")

# ▼ 필터링 및 요약
news_data = []

for item in items:
    title = item.title.text
    link = item.link.text
    pub_date = item.pubDate.text

    # 키워드 포함 여부
    if any(k in title for k in keywords):
        summary_prompt = f"뉴스 제목: {title}\n요약: 이 뉴스 내용을 한국어로 해석해주고, 해외선물과 관련된 것인지 판단해서 요약을 한두 문장으로 해줘."
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "뉴스 요약 어시스턴트"},
                    {"role": "user", "content": summary_prompt}
                ]
            )
            summary = completion['choices'][0]['message']['content'].strip()
        except Exception as e:
            summary = "요약 불가"

        # 날짜 형식 변환
        try:
            pub_dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            pub_dt_kst = pub_dt.astimezone(kst).strftime("%Y-%m-%d %H:%M")
        except:
            pub_dt_kst = "알 수 없음"

        news_data.append({
            "title": title,
            "summary": summary,
            "time": pub_dt_kst,
            "link": link
        })

# ▼ HTML 구성
html = f"""<!DOCTYPE html>
<html>
<head><meta charset=\"utf-8\"><title>GOMA 실시간 뉴스</title></head>
<body style=\"font-family:sans-serif; padding:20px;\">
<h1>실시간 해외선물 뉴스</h1>
<p>최종 업데이트: {now} (KST)</p>
<ul>
"""

if news_data:
    for news in news_data:
        html += f"""<li>
        <strong>{news['title']}</strong><br>
        요약: {news['summary']}<br>
        발표 시간: {news['time']}<br>
        <a href=\"{news['link']}\" target=\"_blank\">[원문 보기]</a><br><br>
        </li>
        """
else:
    html += "<li>현재 시간 기준으로 새롭게 수집된 뉴스가 없습니다.</li>"

html += """
</ul>
</body>
</html>
"""

# ▼ 저장
with open("goma_news_live_updated.html", "w", encoding="utf-8") as f:
    f.write(html)

