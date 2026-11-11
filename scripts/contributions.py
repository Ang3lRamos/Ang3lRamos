"""Dibuja el calendario de contribuciones del último año como un SVG animado.

Lee la página pública de contribuciones de GitHub (sin token) y escribe assets/contributions.svg.
Lo corre a diario .github/workflows/contributions.yml.

Uso: python scripts/contributions.py [usuario] [pagina.html]
(el segundo argumento lee una copia local de la página, para probar sin red)
"""
import datetime as dt
import html
import re
import sys
import urllib.request
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else "Ang3lRamos"
OUT = Path(__file__).resolve().parent.parent / "assets" / "contributions.svg"

PANEL, LINE, INK, MUTED, FAINT, BG = "#10141a", "#222a33", "#e4e7eb", "#8b95a3", "#5d6774", "#0a0d10"
LEVELS = ["#161b22", "#0b3d24", "#11683b", "#18a058", "#2fe08a"]  # de 0 a 4 contribuciones relativas
MONO = "JetBrains Mono, Cascadia Code, Consolas, ui-monospace, monospace"
REDUCE = "@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }"


def fetch_days(user: str, local: str | None = None) -> list[tuple[dt.date, int, int]]:
    """(fecha, contribuciones, nivel 0-4) por día, en orden."""
    if local:
        page = Path(local).read_text(encoding="utf-8")
    else:
        req = urllib.request.Request(f"https://github.com/users/{user}/contributions",
                                     headers={"User-Agent": "profile-contributions-svg"})
        page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    cells = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})" id="(contribution-day-component-\d+-\d+)" data-level="(\d)"', page)
    tips = dict(re.findall(r'<tool-tip[^>]*for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>', page))
    days = []
    for date, cid, level in cells:
        m = re.match(r"([\d,]+) contribution", html.unescape(tips.get(cid, "")))
        days.append((dt.date.fromisoformat(date), int(m.group(1).replace(",", "")) if m else 0, int(level)))
    if len(days) < 300:
        raise SystemExit(f"Solo se leyeron {len(days)} días: GitHub cambió el formato de la página.")
    return sorted(days)


def streaks(days):
    longest = current = run = 0
    for _, count, _ in days:
        run = run + 1 if count else 0
        longest = max(longest, run)
    # La racha actual no se corta si hoy todavía no hay contribuciones.
    for i, (_, count, _) in enumerate(reversed(days)):
        if count:
            current += 1
        elif i > 0:
            break
    return longest, current


def render(days) -> str:
    cell, gap = 12, 3
    step = cell + gap
    x0, y0 = 56, 74
    start = days[0][0] - dt.timedelta(days=(days[0][0].weekday() + 1) % 7)  # semanas empiezan en domingo
    weeks = (days[-1][0] - start).days // 7 + 1
    w = x0 + weeks * step + 24
    h = 250
    total = sum(c for _, c, _ in days)
    longest, current = streaks(days)
    best_day, best = max(((d, c) for d, c, _ in days), key=lambda t: t[1])
    active = sum(1 for _, c, _ in days if c)

    cells, months, last_month = [], [], None
    for d, count, level in days:
        col, row = (d - start).days // 7, (d.weekday() + 1) % 7
        x, y = x0 + col * step, y0 + row * step
        cells.append(f'<rect class="d w{col}" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[level]}"/>')
        if d.day <= 7 and d.month != last_month and row == 0:
            months.append(f'<text x="{x}" y="{y0-8}" font-size="10" fill="{MUTED}">{d.strftime("%b")}</text>')
            last_month = d.month
    weekdays = "".join(f'<text x="{x0-10}" y="{y0 + r*step + 10}" text-anchor="end" font-size="9" fill="{FAINT}">{n}</text>'
                       for r, n in [(1, "Mon"), (3, "Wed"), (5, "Fri")])

    # Onda de luz: cada semana se ilumina por turnos, de izquierda a derecha.
    cycle = 9.0
    wave = "".join(f".w{c} {{ animation-delay: {c * 0.09:.2f}s; }}" for c in range(weeks))
    glow_x = x0 - 6
    style = f"""
text {{ font-family: {MONO}; }}
.d {{ animation: glow {cycle}s ease-in-out infinite; }}
{wave}
@keyframes glow {{ 0%, 6%, 100% {{ filter: none; transform: none; }} 2% {{ filter: brightness(1.9) drop-shadow(0 0 3px #2fe08a); }} }}
.beam {{ animation: beam {cycle}s linear infinite; }}
@keyframes beam {{ from {{ transform: translateX(0); }} {weeks*0.09/cycle*100:.1f}%, 100% {{ transform: translateX({weeks*step}px); opacity: 0; }} }}
.walk {{ animation: walk {cycle}s linear infinite; }}
@keyframes walk {{ from {{ transform: translateX({x0}px); }} {weeks*0.09/cycle*100:.1f}% {{ transform: translateX({x0 + weeks*step}px); opacity: 1; }} {weeks*0.09/cycle*100+2:.1f}%, 100% {{ transform: translateX({x0 + weeks*step}px); opacity: 0; }} }}
.legs-a {{ animation: la .44s steps(1) infinite; }} @keyframes la {{ 50% {{ opacity: 0; }} }}
.legs-b {{ opacity: 0; animation: lb .44s steps(1) infinite; }} @keyframes lb {{ 50% {{ opacity: 1; }} }}
{REDUCE}
"""
    # Clawd caminando sobre la onda.
    px = 3
    body_rows = ["0111111110", "0121111210", "1111111111", "0111111110"]
    colors = {"1": "#D97757", "2": "#1a1a1a"}

    def pixels(rows, top):
        return "".join(f'<rect x="{(c-5)*px}" y="{top + r*px}" width="{px}" height="{px}" fill="{colors[ch]}"/>'
                       for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != "0")

    clawd_top = y0 + 7 * step + 6
    clawd = (f'<g class="walk">{pixels(body_rows, clawd_top)}'
             f'<g class="legs-a">{pixels(["0101001010"], clawd_top + 4*px)}</g>'
             f'<g class="legs-b">{pixels(["1010000101"], clawd_top + 4*px)}</g></g>')

    # Leyenda arriba a la derecha: menos ■■■■■ más.
    lx = w - 24 - 22 - 5 * 15
    legend = (f'<text x="{lx-6}" y="54" text-anchor="end" font-size="9" fill="{FAINT}">menos</text>'
              + "".join(f'<rect x="{lx + i*15}" y="44" width="{cell}" height="{cell}" rx="2.5" fill="{c}"/>' for i, c in enumerate(LEVELS))
              + f'<text x="{lx + 5*15 + 2}" y="54" font-size="9" fill="{FAINT}">más</text>')
    stats = [("contribuciones", f"{total:,}"), ("días activos", f"{active}"), ("racha más larga", f"{longest} d"),
             ("racha actual", f"{current} d"), ("mejor día", f"{best} · {best_day.strftime('%d %b')}")]
    stat_svg = "".join(f'<text x="{x0 + i*140}" y="{h-36}" font-size="10" fill="{MUTED}">{k}</text>'
                       f'<text x="{x0 + i*140}" y="{h-20}" font-size="13" font-weight="700" fill="{INK}">{v}</text>'
                       for i, (k, v) in enumerate(stats))
    updated = dt.date.today().isoformat()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Contribuciones de {USER} en el último año: {total} contribuciones">
<style>{style}</style>
<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="{PANEL}" stroke="{LINE}"/>
<circle cx="18" cy="17" r="4" fill="#f0525f"/><circle cx="31" cy="17" r="4" fill="#e0a526"/><circle cx="44" cy="17" r="4" fill="#1fbf75"/>
<text x="{w/2}" y="21" text-anchor="middle" font-size="11" fill="{MUTED}">git log --graph --since=1.year · {USER}</text>
<line x1="0" y1="32" x2="{w}" y2="32" stroke="{LINE}"/>
{''.join(months)}{weekdays}
<rect class="beam" x="{glow_x}" y="{y0-4}" width="18" height="{7*step+6}" rx="4" fill="#2fe08a" opacity=".08"/>
{''.join(cells)}
{clawd}
{stat_svg}
{legend}
<text x="{w-24}" y="{h-14}" text-anchor="end" font-size="9" fill="{FAINT}">actualizado {updated}</text>
</svg>'''


def main() -> None:
    days = fetch_days(USER, sys.argv[2] if len(sys.argv) > 2 else None)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(days), encoding="utf-8")
    print(f"{OUT.name}: {len(days)} días, {sum(c for _, c, _ in days)} contribuciones")


if __name__ == "__main__":
    main()
