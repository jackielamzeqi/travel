#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 history-tracks.html：重命名轨迹文件并生成双表汇总。"""
import html
import json
import re
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent

# 按当前文件名兜底（标题过于笼统时）
STEM_DISPLAY = {
    "2021-10-04": "2021-10-04 德钦高海拔自驾",
    "2022-04-03 阿坝藏族羌族自治州阿坝县": "2022-04-03 莲宝叶则扎嘎尔措",
    "2023年端午长穿毕": "2023端午 长穿毕",
    "2023年国庆麦径百公里反穿": "2023国庆 麦径百公里反穿",
    "2023-05-01 雨崩冰湖线": "2023-05-01 雨崩冰湖线",
    "2023-04-30 雨崩神瀑线": "2023-04-30 雨崩神瀑线",
    "2023-02-12 峨眉山（雷洞坪➡️金顶）": "2023-02-12 峨眉山雷洞坪至金顶",
    "2023-06-10 五台山大朝台逆穿": "2023-06-10 五台山大朝台逆穿",
    "2022-12-09 武功山穿越明月山": "2022-12-09 武功山穿越明月山",
    "2024-10-25 泰山夜爬": "2024-10-25 泰山夜爬",
    "2024-11-22 养子沟穿越老君山环线": "2024-11-22 养子沟穿越老君山环线",
}


def esc(s):
    return html.escape(str(s)) if s else ""


def safe_filename(name):
    s = re.sub(r'[\\/:*?"<>|]', "-", name.strip())
    s = re.sub(r"\s+", " ", s)
    return s[:120] + ".html"


def parse_meters(s):
    if not s or s in ("—", "-"):
        return 0
    m = re.search(r"([\d,]+)\s*m", s.replace(",", ""))
    return int(m.group(1)) if m else 0


def parse_km(s):
    if not s or s in ("—", "-"):
        return 0.0
    m = re.search(r"([\d.]+)\s*km", s)
    return float(m.group(1)) if m else 0.0


def extract_date_span(text):
    m = re.search(
        r'class="muted"[^>]*>(\d{4}-\d{2}-\d{2})\s+\d{1,2}:\d{2}\s*→\s*(\d{4}-\d{2}-\d{2})',
        text,
    )
    if m:
        return m.group(1), m.group(2)
    m = re.search(r'class="muted"[^>]*>(\d{4}-\d{2}-\d{2})', text)
    if m:
        return m.group(1), m.group(1)
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1), m.group(1)
    return "", ""


def calc_days(start, end):
    if not start:
        return 1
    if not end:
        end = start
    d0 = datetime.strptime(start, "%Y-%m-%d")
    d1 = datetime.strptime(end, "%Y-%m-%d")
    return max(1, (d1 - d0).days + 1)


def score_band(value, bands):
    """bands: [(threshold, points), ...] 从高到低"""
    for threshold, points in bands:
        if value >= threshold:
            return points
    return 0


def kilimanjaro_score(track):
    """0–100：相对 Machame 威士忌线 8 天徒步的可行性信号（非医学结论）。"""
    max_m = parse_meters(track["max_alt"])
    high_min = track["high_3000_min"]
    dist_km = track["dist_km"]
    days = track["days"]
    ascent_m = parse_meters(track["ascent"])
    descent_m = parse_meters(track["descent"])

    alt_pts = score_band(
        max_m,
        [(5000, 25), (4500, 22), (4000, 18), (3500, 12), (3000, 6), (2500, 3)],
    )
    high_pts = score_band(
        high_min,
        [(48 * 60, 20), (24 * 60, 16), (12 * 60, 12), (6 * 60, 8), (60, 4)],
    )
    dist_pts = score_band(
        dist_km,
        [(100, 15), (50, 13), (30, 11), (15, 8), (5, 5), (0, 2)],
    )
    days_pts = score_band(days, [(4, 15), (3, 12), (2, 8), (1, 4)])
    ascent_pts = score_band(
        ascent_m,
        [(3000, 15), (1500, 12), (800, 10), (400, 6), (0, 3)],
    )
    descent_pts = score_band(
        descent_m,
        [(2500, 10), (1500, 8), (800, 6), (400, 4), (0, 2)],
    )
    return min(100, alt_pts + high_pts + dist_pts + days_pts + ascent_pts + descent_pts)


def parse_duration_minutes(s):
    if not s or s in ("—", "-"):
        return 0
    s = s.replace(" ", "")
    h = re.search(r"(\d+)小时", s)
    m = re.search(r"(\d+)分", s)
    return (int(h.group(1)) if h else 0) * 60 + (int(m.group(1)) if m else 0)


def fmt_duration(minutes):
    if minutes <= 0:
        return "—"
    h, m = divmod(int(round(minutes)), 60)
    if h and m:
        return f"{h}小时{m:02d}分"
    if h:
        return f"{h}小时"
    return f"{m}分"


def extract_alt_table(text):
    rows = {}
    block = re.search(r"<h2>高海拔暴露[^<]*</h2><table>(.*?)</table>", text, re.DOTALL)
    if not block:
        return rows
    for row in re.finditer(
        r"<tr><td>([^<]+)</td><td>([^<]*)</td><td>([^<]*)</td></tr>", block.group(1)
    ):
        band, _dist, dur = row.groups()
        rows[band.strip()] = dur.strip()
    return rows


def extract_route_points(text):
    m = re.search(r"const routePoints\s*=\s*(\[\[.*?\]\])\s*;", text, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(1).replace("'", '"'))
    except json.JSONDecodeError:
        return []


def estimate_alt_duration(text, total_min, threshold=3000):
    pts = extract_route_points(text)
    if len(pts) < 2 or total_min <= 0:
        return 0
    total_dist = 0.0
    segs = []
    for i in range(1, len(pts)):
        lat1, lon1, a1 = pts[i - 1]
        lat2, lon2, a2 = pts[i]
        dlat = (lat2 - lat1) * 111_000
        dlon = (lon2 - lon1) * 111_000 * max(0.3, abs(__import__("math").cos(__import__("math").radians(lat1))))
        dist = (dlat**2 + dlon**2) ** 0.5
        segs.append((dist, min(a1, a2), (a1 + a2) / 2))
        total_dist += dist
    if total_dist <= 0:
        return 0
    high_min = 0.0
    for dist, alt_min, alt_avg in segs:
        seg_min = total_min * dist / total_dist
        if alt_min >= threshold or alt_avg >= threshold:
            high_min += seg_min
    return high_min


def extract_record_date(text):
    m = re.search(r'class="muted"[^>]*>(\d{4}-\d{2}-\d{2})', text)
    return m.group(1) if m else ""


def normalize_display_name(h1, text, path: Path):
    if path.stem in STEM_DISPLAY:
        return STEM_DISPLAY[path.stem]
    name = h1.replace("🚗", "").replace("🥾", "").strip()
    name = re.sub(r"@JK\b", "", name).strip()
    name = re.sub(r"\s*@\w+\s*$", "", name).strip()
    # 去掉标题中的时刻：2022-04-02 10:54 … / 2021-10-04 16:41:05
    name = re.sub(
        r"(\d{4}-\d{2}-\d{2})\s+(?:\d{1,2}[:：]\d{2}(?::\d{2})?|\d{1,2}-\d{1,2}-\d{1,2})\s*",
        r"\1 ",
        name,
    ).strip()
    m = re.match(r"^(\d{2})年", name)
    if m:
        yy = int(m.group(1))
        full = 2000 + yy if yy < 50 else 1900 + yy
        name = f"{full}年" + name[3:]
    name = re.sub(r"^(\d{4})年", r"\1", name)
    if not re.search(r"\d{4}", name):
        rec = extract_record_date(text)
        if rec:
            name = f"{rec} {name}"
    return re.sub(r"\s+", " ", name).strip()


def classify_kind(text, metrics, h1):
    badge_m = re.search(r'class="badge"[^>]*>([^<]+)', text)
    badge = badge_m.group(1) if badge_m else ""
    type_metric = metrics.get("类型", "")
    if "历史高海拔轨迹样本" in badge or type_metric == "驾车" or "自驾" in h1:
        return "drive"
    if "历史徒步轨迹样本" in badge or type_metric == "徒步":
        return "walk"
    return "drive" if "自驾" in h1 or "驾车" in h1 else "walk"


def parse_track(path: Path):
    text = path.read_text(encoding="utf-8")
    h1_m = re.search(r"<h1>([^<]+)</h1>", text)
    raw_h1 = (h1_m.group(1) if h1_m else path.stem).strip()

    metrics = {}
    for val, label in re.findall(
        r'<div class="metric"><b>([^<]*)</b><span>([^<]*)</span></div>', text
    ):
        metrics[label.strip()] = val.strip()

    h1 = normalize_display_name(raw_h1, text, path)
    kind = classify_kind(text, metrics, raw_h1 + h1)

    dist = metrics.get("官方路程") or metrics.get("路程") or "—"
    duration = metrics.get("总时长") or metrics.get("记录跨度") or "—"
    ascent = metrics.get("累计爬升", "—")
    descent = metrics.get("累计下降", "—")
    max_alt = metrics.get("最高海拔", "—")
    avg_alt = metrics.get("平均海拔", "—")

    alt_rows = extract_alt_table(text)
    high_dur = alt_rows.get("≥3000 m") or alt_rows.get("≥3000m")
    if not high_dur:
        for k, v in metrics.items():
            if "≥3000" in k:
                high_dur = v
                break
    if not high_dur:
        total_min = parse_duration_minutes(duration)
        est = estimate_alt_duration(text, total_min, 3000)
        if est > 0:
            high_dur = fmt_duration(est)
        elif kind == "drive" and parse_duration_minutes(metrics.get("运动时长", "")) > 0:
            max_m = re.search(r"(\d+)", max_alt.replace(",", ""))
            if max_m and int(max_m.group(1)) >= 3000:
                avg_m = re.search(r"(\d+)", avg_alt.replace(",", ""))
                if avg_m and int(avg_m.group(1)) >= 3000:
                    high_dur = metrics.get("运动时长", "—")

    badge_m = re.search(r'class="badge"[^>]*>([^<]+)', text)
    tags = badge_m.group(1) if badge_m else ""
    tags = re.sub(r"历史(?:自驾|徒步|高海拔)轨迹样本\s*·?\s*", "", tags)
    tags = re.sub(r"^\d+\s*·\s*", "", tags).strip()

    start_date, end_date = extract_date_span(text)
    if not start_date and h1:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", h1)
        if m:
            start_date = m.group(1)
            end_date = end_date or start_date
    days = calc_days(start_date, end_date)
    duration_min = parse_duration_minutes(duration)
    high_3000_min = parse_duration_minutes(high_dur or "")
    dist_km = parse_km(dist)
    score = kilimanjaro_score(
        {
            "max_alt": max_alt,
            "high_3000_min": high_3000_min,
            "dist_km": dist_km,
            "days": days,
            "ascent": ascent,
            "descent": descent,
        }
    ) if kind == "walk" else 0

    return {
        "path": path,
        "h1": h1,
        "kind": kind,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "dist": dist,
        "dist_km": dist_km,
        "duration": duration,
        "duration_min": duration_min,
        "ascent": ascent,
        "ascent_m": parse_meters(ascent),
        "descent": descent,
        "descent_m": parse_meters(descent),
        "max_alt": max_alt,
        "max_m": parse_meters(max_alt),
        "avg_alt": avg_alt,
        "avg_m": parse_meters(avg_alt),
        "high_3000": high_dur or "—",
        "high_3000_min": high_3000_min,
        "score": score,
        "tags": tags,
    }


def sort_key(track):
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})?", track["h1"])
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), (m.group(3) or "01").zfill(2)
        return (y, mo, d, track["h1"])
    m = re.search(r"(\d{2,4})年", track["h1"])
    if m:
        return (m.group(1), "99", "99", track["h1"])
    return ("0000", "99", "99", track["h1"])


def rename_tracks(tracks):
    used = set()
    for t in tracks:
        base_name = safe_filename(t["h1"])[:-5]
        name = base_name
        n = 2
        while name + ".html" in used:
            name = f"{base_name}-{n}"
            n += 1
        used.add(name + ".html")
        new_path = BASE / f"{name}.html"
        old = t["path"]
        if old != new_path:
            if new_path.exists() and new_path.resolve() != old.resolve():
                raise SystemExit(f"冲突: {new_path}")
            old.rename(new_path)
        t["file"] = new_path.name
    return tracks


def row_drive(t):
    return (
        f"<tr><td><a href=\"{esc(t['file'])}\">🚗 {esc(t['h1'])}</a>"
        f"<span>{esc(t['tags'])}</span></td>"
        f"<td>{esc(t['dist'])}</td><td>{esc(t['duration'])}</td>"
        f"<td>{esc(t['high_3000'])}</td>"
        f"<td>{esc(t['max_alt'])}</td><td>{esc(t['avg_alt'])}</td></tr>"
    )


def row_walk(t):
    start = t["start_date"] or "—"
    score_cls = "score-high" if t["score"] >= 70 else "score-mid" if t["score"] >= 45 else "score-low"
    return (
        f"<tr data-start=\"{esc(t['start_date'])}\" data-name=\"{esc(t['h1'])}\" "
        f"data-days=\"{t['days']}\" data-dist=\"{t['dist_km']}\" data-duration=\"{t['duration_min']}\" "
        f"data-ascent=\"{t['ascent_m']}\" data-descent=\"{t['descent_m']}\" "
        f"data-high=\"{t['high_3000_min']}\" data-max=\"{t['max_m']}\" data-avg=\"{t['avg_m']}\" "
        f"data-score=\"{t['score']}\">"
        f"<td>{esc(start)}</td>"
        f"<td><a href=\"{esc(t['file'])}\">🥾 {esc(t['h1'])}</a>"
        f"<span>{esc(t['tags'])}</span></td>"
        f"<td>{t['days']}</td>"
        f"<td>{esc(t['dist'])}</td><td>{esc(t['duration'])}</td>"
        f"<td>{esc(t['ascent'])}</td><td>{esc(t['descent'])}</td>"
        f"<td>{esc(t['high_3000'])}</td>"
        f"<td>{esc(t['max_alt'])}</td><td>{esc(t['avg_alt'])}</td>"
        f"<td><b class=\"{score_cls}\">{t['score']}</b></td></tr>"
    )


WALK_SORT_JS = """
(function(){
  const table=document.getElementById('walk-table');
  if(!table)return;
  const tbody=table.querySelector('tbody');
  const headers=table.querySelectorAll('th[data-sort]');
  let col='score',dir=-1;
  function val(row,key){return row.dataset[key]||'';}
  function cmp(a,b,key){
    if(key==='start'||key==='name'){
      return val(a,key).localeCompare(val(b,key),'zh-CN');
    }
    return (parseFloat(val(a,key))||0)-(parseFloat(val(b,key))||0);
  }
  function render(){
    const rows=[...tbody.querySelectorAll('tr')];
    rows.sort((a,b)=>dir*cmp(a,b,col));
    rows.forEach(r=>tbody.appendChild(r));
    headers.forEach(th=>{
      const on=th.dataset.sort===col;
      th.classList.toggle('sorted',on);
      th.setAttribute('aria-sort',on?(dir<0?'descending':'ascending'):'none');
    });
  }
  headers.forEach(th=>{
    th.addEventListener('click',()=>{
      const k=th.dataset.sort;
      if(col===k)dir*=-1;else{col=k;dir=-1;}
      render();
    });
  });
  render();
})();
"""


def build_index(drives, walks):
    hike_km = 0.0
    for t in walks:
        m = re.search(r"([\d.]+)\s*km", t["dist"])
        if m:
            hike_km += float(m.group(1))
    max_alt = 0
    for t in drives + walks:
        m = re.search(r"(\d+)", t["max_alt"].replace(",", ""))
        if m:
            max_alt = max(max_alt, int(m.group(1)))

    drive_rows = "\n".join(row_drive(t) for t in drives)
    walks = sorted(walks, key=lambda t: t["score"], reverse=True)
    walk_rows = "\n".join(row_walk(t) for t in walks)

    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>历史户外经验汇总｜乞力马扎罗评估</title><style>:root{{--bg:#101418;--panel:#171f27;--ink:#e9eef5;--muted:#9aa9b8;--line:#334150;--accent:#34d399;--drive:#38bdf8;--warn:#f59e0b}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.55;-webkit-text-size-adjust:100%}}.wrap{{max-width:1120px;margin:0 auto;padding:28px 18px 56px;padding-left:max(18px,env(safe-area-inset-left));padding-right:max(18px,env(safe-area-inset-right))}}h1{{font-size:28px;margin:0 0 8px;line-height:1.2}}h2{{font-size:17px;margin:0 0 12px}}h2.drive{{color:#bfe7ff}}h2.walk{{color:#c5f7df}}.hero,.card{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px;margin-bottom:14px}}.hero{{background:linear-gradient(150deg,#173124,#101418 72%)}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}}.metric{{background:#101820;border:1px solid var(--line);border-radius:8px;padding:12px}}.metric b{{display:block;font-size:22px;line-height:1.2}}.metric span{{font-size:12px;color:var(--muted)}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{border-bottom:1px solid var(--line);padding:11px 8px;text-align:left;vertical-align:top}}th{{color:#cbd5e1}}th.sortable{{cursor:pointer;user-select:none;white-space:nowrap}}th.sortable:hover{{color:#e9eef5}}th.sortable.sorted::after{{content:" ↓";color:var(--accent);font-size:12px}}th.sortable.sorted[aria-sort="ascending"]::after{{content:" ↑"}}td span{{display:block;color:var(--muted);font-size:12px;margin-top:2px}}a{{color:#86efac;text-decoration:none}}a:hover{{text-decoration:underline}}.note{{border-left:3px solid var(--warn);padding:10px 12px;background:rgba(245,158,11,.09);color:#f7d795;border-radius:0 8px 8px 0}}.muted{{color:var(--muted)}}.score-high{{color:#86efac}}.score-mid{{color:#fcd34d}}.score-low{{color:#9aa9b8}}@media(max-width:780px){{.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}table{{font-size:13px}}th,td{{padding:9px 6px}}}} </style></head><body><main class="wrap"><section class="hero"><h1>历史户外经验汇总</h1><p class="muted" style="margin:0">用于评估乞力马扎罗 Machame 威士忌线 8 天徒步的历史轨迹样本库。文件命名：时间 + 路线名称。</p><div class="metrics"><div class="metric"><b>{len(walks)} 条</b><span>🥾 徒步样本</span></div><div class="metric"><b>{hike_km:.1f} km</b><span>累计官方徒步距离</span></div><div class="metric"><b>{len(drives)} 条</b><span>🚗 自驾高海拔样本</span></div><div class="metric"><b>{max_alt} m</b><span>历史最高海拔</span></div></div></section><div class="card"><h2>初步能力信号</h2><p class="note">藏东秘境环线补充了高海拔停留暴露：时间轴 ≥4500m 约 12小时02分，≥5000m 约 1小时10分；低速/停留估算 ≥5000m 约 32 分钟。下表【高海拔停留】统一统计 ≥3000m 估算停留时长。</p></div><div class="card"><h2 class="drive">🚗 自驾轨迹（{len(drives)}）</h2><table><tr><th>轨迹</th><th>路程</th><th>时长</th><th>高海拔停留<br><span class="muted">≥3000m</span></th><th>最高</th><th>平均</th></tr>{drive_rows}</table></div><div class="card"><h2 class="walk">🥾 徒步轨迹（{len(walks)}）</h2><p class="muted" style="margin:0 0 12px;font-size:13px">时间取轨迹开始日期（YYYY-MM-DD）。天数按起止日历日计算（含首尾）。综合评分 100 表示历史信号与威士忌线挑战高度匹配，0 表示几乎无参考价值；点击表头可排序，默认按评分从高到低。</p><table id="walk-table"><thead><tr><th class="sortable" data-sort="start">时间</th><th class="sortable" data-sort="name">轨迹</th><th class="sortable" data-sort="days">天数</th><th class="sortable" data-sort="dist">路程</th><th class="sortable" data-sort="duration">时长</th><th class="sortable" data-sort="ascent">爬升</th><th class="sortable" data-sort="descent">下降</th><th class="sortable" data-sort="high">高海拔停留<br><span class="muted">≥3000m</span></th><th class="sortable" data-sort="max">最高</th><th class="sortable" data-sort="avg">平均</th><th class="sortable sorted" data-sort="score" aria-sort="descending">综合评分</th></tr></thead><tbody>{walk_rows}</tbody></table></div><div class="card"><h2>高海拔关注点</h2><p>历史样本最高 {max_alt} m、徒步累计约 {hike_km:.1f} km。评估乞力马扎罗时，建议同时看【高海拔停留】与连续多日徒步负荷、睡眠海拔变化及 4000m 以上反应记录。</p></div></main><script>{WALK_SORT_JS}</script></body></html>"""


def main():
    paths = [p for p in BASE.glob("*.html") if p.name != "history-tracks.html"]
    tracks = [parse_track(p) for p in paths]
    rename_tracks(tracks)
    drives = sorted([t for t in tracks if t["kind"] == "drive"], key=sort_key, reverse=True)
    walks = sorted([t for t in tracks if t["kind"] == "walk"], key=sort_key, reverse=True)
    (BASE / "history-tracks.html").write_text(build_index(drives, walks), encoding="utf-8")
    print(f"OK: {len(drives)} 自驾 + {len(walks)} 徒步")
    for t in sorted([t for t in tracks if t["kind"] == "walk"], key=lambda x: -x["score"]):
        print(f"  {t['start_date']}  {t['h1']}  {t['days']}天  评分{t['score']}")


if __name__ == "__main__":
    main()
