import os
import requests
import datetime
from bs4 import BeautifulSoup
from pytz import timezone
import openai

# ── 1) OpenAI API 키 설정 ──
# GitHub Actions에서 secrets.OPENAI_API_KEY 를 env로 넘겨줍니다.
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

# ── 2) 시간대 & 현재 시각 ──
kst = timezone("Asia/Seoul")
now = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M")

# ── 3) 키워드 & RSS 목록 ──
keywords = [
    "nasdaq", "gold", "futures", "powell", "cpi", "ppi", "fomc",
    "employment", "jobless", "trump", "fed", "rate", "gdp", "nvidia",
    "ism", "confidence", "nq", "xauusd"
]
rss_feeds = [
    "https://www.marketwatch.com/rss/topstories",
    "https://www.forexlive.com/feed/"
]

news_data = []

for rss_url in rss_feeds:
    try:
        resp = requests.get(rss_url)
        soup = BeautifulSoup(resp.content, features="xml")
        items = soup.find_all("item")
    except Exception:
        continue

    for item in items:
        title    = item.title.text.strip()
        link     = item.link.text.strip()
        pub_date = item.pubDate.text if item.pubDate else ""
        desc     = item.description.text.strip() if item.description else ""

        # ── 키워드 필터링 (소문자 비교) ──
        if not any(k in title.lower() for k in keywords):
            continue

        # ── 시간 변환 ──
        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            pub_time = dt.astimezone(kst).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pub_time = "알 수 없음"

        # ── GPT 프롬프트 ──
        prompt = (
            f"뉴스 제목: {title}\n"
            f"본문 요약: {desc}\n\n"
            "위의 제목과 요약을 한국어로 자연스럽게 번역해 주시고,\n"
            "이 뉴스가 해외선물(Futures) 관련이면 핵심만 한 문장으로 요약해 주세요.\n"
            "관련이 아니면 “핵심 없음”이라고만 답해 주세요."
        )

        try:
            res = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 금융 뉴스 번역·요약 전문가입니다."},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            answer = res.choices[0].message.content.strip()

            # 응답을 줄 단위로 분리하여 번역/요약 추출
            lines = [ln for ln in [l.strip() for l in answer.split("\n")] if ln]
            translated = lines[0]
            summary    = lines[1] if len(lines) > 1 else "핵심 없음"
        except Exception:
            translated = title
            summary    = "요약 불가"

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
  <meta charset="utf-8">
  <title>GOMA 실시간 해외선물 뉴스</title>
</head>
<body style="font-family:sans-serif; padding:20px;">
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
    html += """    <li>현재 시간 기준으로 새롭게 수집된 뉴스가 없습니다.</li>
"""

html += """
  </ul>
</body>
</html>
"""

# ── 파일 저장 ──
with open("goma_news_live_updated.html", "w", encoding="utf-8") as f:
    f.write(html)
