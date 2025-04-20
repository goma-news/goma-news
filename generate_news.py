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
    "https://www.marketwatch.com/rss/topstories",
    "https://www.forexlive.com/feed/"
]

news_data = []

# ── 뉴스 수집 및 요약 ──
for rss_url in rss_feeds:
    try:
        resp = requests.get(rss_url)
        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")
    except Exception:
        continue

    for item in items:
        title = item.title.text.strip()
        link = item.link.text.strip()
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

        # 본문 내용 추출 (content:encoded 우선)
        content_tag = item.find("content:encoded")
        desc_tag = item.find("description")
        if content_tag and content_tag.text.strip():
            desc = content_tag.text.strip()
        elif desc_tag and desc_tag.text.strip():
            desc = desc_tag.text.strip()
        else:
            desc = "이 뉴스의 본문 내용이 RSS에 제공되지 않았습니다."

        # 키워드 필터링
        if not any(k in title.lower() for k in keywords):
            continue

        # GPT-4 호출 프롬프트 구성 (레이블 수정)
        prompt = (
            f"뉴스 제목: {title}\n"
            f"본문: {desc}\n\n"
            "1) 위 제목과 본문을 한국어로 자연스럽게 번역해 주세요.\n"
            "2) 해외선물 관련이면 핵심만 한 문장으로 요약하고, 아니면 '핵심 없음'이라고 답해주세요."
        )

        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 금융 뉴스 번역·요약 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=120  # 출력 토큰 상한을 120으로 조정
            )
            result = resp.choices[0].message.content.strip()
            lines = [ln.strip() for ln in result.split("\n") if ln.strip()]

            # 번역 & 요약 분리, 접두사 제거
            translated = re.sub(r"^\d+\)\s*", "", lines[0]) if lines else title
            raw_summary = lines[1] if len(lines) > 1 else ""
            # '본문 요약:', '본문:', '요약:' 접두사 일괄 제거
            summary = re.sub(r'^(?:본문\s*요약:|본문:|요약:)\s*', '', raw_summary).strip() or "요약 불가"

        except Exception:
            translated = title
            summary = "요약 불가"

        news_data.append({
            "title": translated,
            "summary": summary,
            "time": pub_time,
            "link": link
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
        요약: {n['summary']}<br>
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
