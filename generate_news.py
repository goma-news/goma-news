import requests
import datetime
from bs4 import BeautifulSoup
from pytz import timezone
import openai

# ▼ 한국 시간 기준
kst = timezone("Asia/Seoul")
now = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M")

# ▼ 키워드 리스트 (영문 기반)
keywords = [
    "nasdaq", "gold", "fed", "powell", "fomc", "cpi", "ppi", "gdp",
    "us jobs", "unemployment", "trump", "interest rate", "nvidia",
    "ism", "consumer confidence", "xauusd", "nq"
]

# ▼ 수집할 RSS 피드 주소 (통합)
rss_feeds = [
    "https://www.marketwatch.com/rss/topstories",
    "https://www.forexlive.com/feed/"
]

news_data = []

for rss_url in rss_feeds:
    try:
        response = requests.get(rss_url)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.findAll("item")
    except Exception as e:
        continue

    for item in items:
        title = item.title.text.strip()
        link = item.link.text.strip()
        pub_date = item.pubDate.text if item.pubDate else "Unknown"
        description = item.description.text.strip() if item.description else ""

        # 키워드 포함 여부 (영문 소문자 비교)
        title_lower = title.lower()
        if not any(k in title_lower for k in keywords):
            continue

        # 발표 시간 처리
        try:
            pub_dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            pub_dt_kst = pub_dt.astimezone(kst).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pub_dt_kst = "알 수 없음"

        # GPT 요약
        prompt = (
            f"뉴스 제목: {title}\n"
            f"내용 요약: {description}\n"
            f"위 뉴스가 해외선물과 관련 있다면, 핵심 내용을 한국어로 간단하게 한 문장으로 요약해줘. "
            f"관련이 없으면 '요약 불가'라고 답해줘."
        )

        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 금융 뉴스 요약 전문가입니다."},
                    {"role": "user", "content": prompt}
                ]
            )
            summary = completion.choices[0].message.content.strip()
        except Exception:
            summary = "요약 불가"

        news_data.append({
            "title": title,
            "summary": summary,
            "time": pub_dt_kst,
            "link": link
        })

# ▼ HTML 생성
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

# ▼ 파일 저장
with open("goma_news_live_updated.html", "w", encoding="utf-8") as f:
    f.write(html)
