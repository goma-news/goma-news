import os
import re
import requests
import datetime
from bs4 import BeautifulSoup
from pytz import timezone
import openai

# ── OpenAI API 키 설정 ──
# GitHub Actions에서 secrets.OPENAI_API_KEY 를 환경변수로 전달해야 합니다
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
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all("item")
    except Exception:
        continue

    for item in items:
        title = item.title.text.strip()
        link = item.link.text.strip()
        pub_date = item.pubDate.text if item.pubDate else ""
        desc = item.description.text.strip() if item.description else ""

        # 키워드 필터링 (소문자 비교)
        if not any(k in title.lower() for k in keywords):
            continue

        # 발행시간 GMT → KST 변환
        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            pub_time = dt.astimezone(kst).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pub_time = "알 수 없음"

        # GPT-4 호출 프롬프트
        prompt = (
            f"뉴스 제목: {title}\n"
            f"본문 요약: {desc}\n\n"
            "1) 위 제목과 요약을 한국어로 자연스럽게 번역해 주세요.\n"
            "2) 이 뉴스가 해외선물(Futures) 관련이면 핵심만 한 문장으로 요약하고,\n"
            "   관련이 아니면 ‘핵심 없음’이라고 답해 주세요."
        )

        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 금융 뉴스 번역·요약 전문가입니다."},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            answer = completion.choices[0].message.content.strip()

            # 응답에서 번역/요약 추출
            lines = [ln for ln in [l.strip() for l in answer.split("\n")] if ln]
            translated = lines[0]
            summary = lines[1] if len(lines) > 1 else "핵심 없음"
        except Exception as e:
            translated = title
            summary = "요약 불가"

        news_data.append({
            "title":   translated,
            "summary": summary,
            "time":    pub_time,
            "link":    link
        })

# ── HTML 생성 ──
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
    for n in news_data:
        html += f"""    <li>
      <strong>{n['title']}</strong><br>
      요약: {n['summary']}<br>
      발표 시간: {n['time']}<br>
      <a href=\"{n['link']}\" target=\"_blank\">[원문 보기]</a><br><br>
    </li>
"""
else:
    html += "    <li>현재 시간 기준으로 새롭게 수집된 뉴스가 없습니다.</li>\n"

html += """
  </ul>
</body>
</html>
"""

# ── 파일 저장 ──
with open("goma_news_live_updated.html", "w", encoding="utf-8") as f:
    f.write(html)

