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

# ── 한국 시간 기준 현재 시각 및 24시간 전 컷오프 ──
kst = timezone("Asia/Seoul")
now = datetime.datetime.now(kst)
cutoff = now - datetime.timedelta(hours=24)
now_str = now.strftime("%Y-%m-%d %H:%M")

# ── 관심 키워드 리스트 ──
keywords = [
    "nasdaq", "gold", "futures", "powell", "cpi", "ppi", "fomc",
    "employment", "unemployment", "trump", "fed", "rate", "gdp", "nvidia",
    "ism", "confidence", "nq", "xauusd"
]

# ── RSS 피드 주소 목록 ──
rss_feeds = [
    ("marketwatch", "https://www.marketwatch.com/rss/topstories"),
    ("forexlive",  "https://www.forexlive.com/feed/"),
    ("dailyfx",    "https://www.dailyfx.com/feeds/all")
]

news_data = []

# ── 뉴스 수집 및 제목 번역 ──
for source, rss_url in rss_feeds:
    try:
        resp = requests.get(rss_url)
        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")
    except Exception:
        continue

    for item in items:
        title = item.title.text.strip()
        link  = item.link.text.strip()
        pub_date = item.pubDate.text if item.pubDate else ""

        # 발행 시간 파싱 → 24시간 초과면 스킵
        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            dt_kst = dt.astimezone(kst)
            if dt_kst < cutoff:
                continue
            pub_time = dt_kst.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pub_time = "알 수 없음"

        # 키워드 필터링
        if not any(k in title.lower() for k in keywords):
            continue

        # 제목만 번역
        prompt = (
            f"뉴스 제목: {title}\n\n"
            "위 제목을 한국어로 자연스럽게 번역해 주세요."
        )
        try:
            ai_resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",  "content": "당신은 금융 뉴스 번역 전문가입니다."},
                    {"role": "user",    "content": prompt}
                ],
                temperature=0.0,
                max_tokens=50
            )
            result = ai_resp.choices[0].message.content.strip()
            translated = re.sub(r"^\d+\)\s*", "", result)
        except Exception:
            translated = title

        news_data.append({
            "title": translated,
            "time":  pub_time,
            "link":  link
        })

# ── HTML 생성 및 저장 ──
html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\"/>
  <title>GOMA 실시간 해외선물 뉴스</title>
  <style>
    html, body {{ margin:0; padding:0; overflow:auto; font-family:sans-serif; }}
    header {{ background:#fff; padding:20px; box-shadow:0 2px 4px rgba(0,0,0,0.1); }}
    .news-container {{ padding:20px; }}
    ul {{ list-style:disc inside; margin:0; padding:0; }}
    li {{ margin-bottom:20px; }}
    strong {{ display:block; margin-bottom:5px; }}
    a {{ color:#4a90e2; text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
  </style>
</head>
<body>
  <header>
    <h1>실시간 해외선물 뉴스</h1>
    <p>최종 업데이트: {now_str} (KST)</p>
    <p style=\"font-size:0.9em; color:#555;\">최신뉴스: F5를 눌러 새로고침 (1시간마다 자동 업데이트)</p>
  </header>
  <div class=\"news-container\">  
    <ul>
"""
for n in news_data:
    html += f"""      <li>
        <strong>{n['title']}</strong><br>
        발표 시간: {n['time']}<br>
        <a href=\"{n['link']}\" target=\"_blank\">[원문 보기]</a>
      </li>
"""
html += """
    </ul>
  </div>
</body>
</html>
"""

with open("goma_news_live_updated.html", "w", encoding="utf-8") as f:
    f.write(html)
