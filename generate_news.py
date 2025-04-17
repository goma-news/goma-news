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
    "미국 고용", "실어발사도", "트럼프", "연준", "금리", "GDP", "엔비디아", "ISM", "소비자신리지수"
]

# ▼ 사용할 뉴스 API 또는 RSS (MarketWatch RSS)
rss_url = "https://www.marketwatch.com/rss/topstories"

# ▼ RSS 가져오기
response = requests.get(rss_url)
soup = BeautifulSoup(response.content, features="xml")
items = soup.findAll("item")

# ▼ 필터링 및 요조
news_data = []

for item in items:
    title = item.title.text
    link = item.link.text
    pub_date = item.pubDate.text

    # 키워드 포함 여부
    if any(k in title for k in keywords):
        # GPT 요조 원체
        summary_prompt = f"\ub274\uc2a4 \uc81c\ubaa9: {title}\n\uc694\uc870: \uc774 \ub274\uc2a4 \ub0b4\uc6a9\uc744 \ud55c\uad6d\uc5b4\ub85c \ud574\uc11d\ud574\uc8fc\uace0, \ud574외\uc120\ubb3c\uacfc \uad00\ub828\ub41c \uac83\uc778\uc9c0\ub97c \ud310단\ud574\uc11c \uc694\uc870\ub97c \ud55c\ub450 \ubb38장\uc73c\ub85c \uc694\uc870\ud574\uc918."
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "\ub274\uc2a4 \uc694\uc870 \uc5b4\uc2dc\uc2a4\ud2b8"},
                    {"role": "user", "content": summary_prompt}
                ]
            )
            summary = completion['choices'][0]['message']['content'].strip()
        except Exception as e:
            summary = "\uc694\uc870 \ubd88\uac00"

        # 날짜 형식 변환
        try:
            pub_dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            pub_dt_kst = pub_dt.astimezone(kst).strftime("%Y-%m-%d %H:%M")
        except:
            pub_dt_kst = "\uc54c \uc218 \uc5c6\uc74c"

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
<p>참조 최종 업데이트: {now} (KST)</p>
<ul>
"""

if news_data:
    for news in news_data:
        html += f"""<li>
        <strong>{news['title']}</strong><br>
        요조: {news['summary']}<br>
        보내지내 시간: {news['time']}<br>
        <a href=\"{news['link']}\" target=\"_blank\">[\uc6d0문 \ubcf4기]</a><br><br>
        </li>
        """
else:
    html += "<li>\uc774보내 \uc2dc간별\ub85c \ubcf4고\ub0b4\ub294 \ub274스가 \uc5c6습니다.</li>"

html += """
</ul>
</body>
</html>
"""

# ▼ 저장
with open("goma_news_live_updated.html", "w", encoding="utf-8") as f:
    f.write(html)
