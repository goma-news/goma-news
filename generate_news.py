import os
import re
import requests
import datetime
from bs4 import BeautifulSoup
from pytz import timezone
import openai

# ── OpenAI API 키 설정 ──
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

# ── 한국 시간 기준 현재 시각 ──
kst = timezone("Asia/Seoul")
now = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M")

# ── 키워드 리스트 ──
keywords = [
    "nasdaq", "gold", "futures", "powell", "cpi", "ppi", "fomc",
    "employment", "unemployment", "trump", "fed", "rate", "gdp", "nvidia",
    "ism", "confidence", "nq", "xauusd"
]

# ── RSS 피드 주소 목록 ──
rss_feeds = [
    "https://www.marketwatch.com/rss/topstories",
    "https://www.forexlive.com/feed/"
]

news_data = []

for rss_url in rss_feeds:
    try:
        response = requests.get(rss_url)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
    except:
        continue

    for item in items:
        title = item.title.text.strip()
        link = item.link.text.strip()
        pub_date = item.pubDate.text if item.pubDate else ""

        # Forexlive 본문 처리
        desc_tag = item.find("description")
        content_tag = item.find("content:encoded")
        if content_tag and content_tag.text.strip():
            desc = content_tag.text.strip()
        elif desc_tag and desc_tag.text.strip():
            desc = desc_tag.text.strip()
        else:
            desc = ""

        # 키워드 필터링
        if not any(k in title.lower() for k in keywords):
            continue

        # 발행시간 변환
        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            pub_time = dt.astimezone(kst).strftime("%Y-%m-%d %H:%M")
        except:
            pub_time = "알 수 없음"

        # GPT 호출 프롬프트
        body_prompt = desc if desc else "본문 없음"
        prompt = (
            f"뉴스 제목: {title}\n"
            f"본문 요약: {body_prompt}\n\n"
            "1) 위 제목과 본문을 한국어로 자연스럽게 번역하고,\n"
            "2) 해외선물 관련이면 핵심 요약, 아니면 ‘핵심 없음’이라고 응답하세요."
        )
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "금융 뉴스 번역·요약 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            text = response.choices[0].message.content.strip()
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            translated = re.sub(r"^\d+\)\s*", "", lines[0])
            summary = lines[1] if len(lines) > 1 else "핵심 없음"
        except:
            translated = title
            summary = "요약 불가"

        news_data.append({"title": translated, "summary": summary, "time": pub_time, "link": link})

# ── HTML 생성 및 저장 ──
html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\">
  <title>GOMA 실시간 해외선물 뉴스</title>
  <style>
    html, body { height:100%; margin:0; padding:0; overflow:hidden; }
    header { position:fixed; top:0; left:0; right:0; background:#fff; padding:20px; box-shadow:0 2px 4px rgba(0,0,0,0.1); z-index:10; }
    .news-container { position:absolute; top:100px; bottom:0; left:0; right:0; padding:20px; overflow-y:auto; }
    ul { list-style: none; padding:0; }
    li { margin-bottom:20px; }
  </style>
</head>
<body>
  <header>
    <h1>실시간 해외선물 뉴스</h1>
    <p>최종 업데이트: {now} (KST)</p>
  </header>
  <div class=\"news-container\">
    <ul>
"""

if news_data:
    for n in news_data:
        html += f"""      <li>
        <strong>{n['title']}</strong><br>
        요약: {n['summary']}<br>
        발표 시간: {n['time']}<br>
        <a href=\"{n['link']}\" target=\"_blank\">[원문 보기]</a>
      </li>
"""
else:
    html += "      <li>현재 시간 기준으로 새롭게 수집된 뉴스가 없습니다.</li>\n"

html += """
    </ul>
  </div>
</body>
</html>
"""
with open("goma_news_live_updated.html", "w", encoding="utf-8") as f:
    f.write(html)
