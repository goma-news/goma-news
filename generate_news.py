import requests
import datetime
from bs4 import BeautifulSoup
from pytz import timezone
import openai
import os

# 🔍 여기 추가!
print("🔑 OPENAI API KEY (확인용):", os.getenv("OPENAI_API_KEY"))

openai.api_key = os.getenv("OPENAI_API_KEY")



# ▼ OpenAI API 키 불러오기
openai.api_key = os.getenv("OPENAI_API_KEY")

# ▼ 한국 시간 기준 현재 시각
kst = timezone("Asia/Seoul")
now = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M")

# ▼ 키워드 리스트 (영문 기준)
keywords = [
    "futures", "Nasdaq", "Gold", "Powell", "CPI", "PPI", "FOMC",
    "jobs", "unemployment", "Trump", "Fed", "rate", "GDP", "Nvidia",
    "ISM", "confidence", "NQ", "XAUUSD"
]

# ▼ RSS 피드 주소 목록
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
    except Exception:
        continue

    for item in items:
        title = item.title.text.strip()
        link = item.link.text.strip()
        pub_date = item.pubDate.text if item.pubDate else "Unknown"
        description = item.description.text.strip() if item.description else ""

        if not any(k.lower() in title.lower() for k in keywords):
            continue

        try:
            pub_dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            pub_dt_kst = pub_dt.astimezone(kst).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pub_dt_kst = "알 수 없음"

        prompt = (
            f"뉴스 제목: {title}\n"
            f"본문 요약: {description}\n\n"
            "1) 위 제목과 본문을 한국어로 자연스럽게 번역해줘.\n"
            "2) 이 뉴스가 해외선물과 관련된 내용이면, 핵심만 한 문장으로 요약해주고, 관련이 없다면 '핵심 없음'이라고 답해줘."
        )

        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 금융 뉴스 번역·요약 전문가입니다."},
                    {"role": "user", "content": prompt}
                ]
            )
            content = completion.choices[0].message.content.strip()

            print("GPT 응답 원문 ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓")
            print(content)
            print("↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑")

            translated = title
            summary = "요약 불가"

            match_trans = re.search(r"번역[:\]\s*(.+)", content)
            match_sum = re.search(r"요약[:\]\s*(.+)", content)

            if match_trans:
                translated = match_trans.group(1).strip()
            if match_sum:
                summary = match_sum.group(1).strip()

        except Exception as e:
            print(f"GPT 오류: {e}")
            translated = title
            summary = "요약 불가"

        news_data.append({
            "title": translated,
            "summary": summary,
            "time": pub_dt_kst,
            "link": link
        })

html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\">
  <title>GOMA 실시간 해외선물 뉴스</title>
</head>
<body style=\"font-family:sans-serif; padding:20px;\">
  <h1>실시간 해외선물 뉴스</h1>
  <p>최종 업데이트: {now} (KST)</p>
  <ul>
"""

if news_data:
    for news in news_data:
        html += f"""    <li>
      <strong>{news['title']}</strong><br>
      요약: {news['summary']}<br>
      발표 시간: {news['time']}<br>
      <a href=\"{news['link']}\" target=\"_blank\">[원문 보기]</a><br><br>
    </li>
"""
else:
    html += "    <li>현재 시간 기준으로 새롭게 수집된 뉴스가 없습니다.</li>\n"

html += """  </ul>
</body>
</html>
"""

with open("goma_news_live_updated.html", "w", encoding="utf-8") as f:
    f.write(html)
