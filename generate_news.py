from datetime import datetime

html = f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>GOMA NEWS</title></head>
<body>
<h1>실시간 해외선물 뉴스</h1>
<p>업데이트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<ul>
  <li>예시 뉴스: 미국 CPI 발표 예정</li>
  <li>예시 뉴스: 파월 발언 대기 중</li>
</ul>
</body>
</html>
"""

with open("goma_news_live_updated.html", "w", encoding="utf-8") as f:
    f.write(html)
