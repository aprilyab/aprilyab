"""Render public GitHub contribution activity as local, dependency-free SVGs."""

import argparse
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
        self.labels = {}
        self.tooltip = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "data-date" in attrs:
            self.days[attrs["data-date"]] = (int(attrs["data-level"]), attrs["id"])
        if tag == "tool-tip":
            self.tooltip = attrs.get("for")

    def handle_data(self, data):
        if self.tooltip:
            self.labels[self.tooltip] = self.labels.get(self.tooltip, "") + data

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.tooltip = None


def render(source, output):
    calendar = Calendar()
    calendar.feed(source)
    if len(calendar.days) < 350:
        raise ValueError("GitHub did not return a complete contribution calendar")
    days = sorted(calendar.days)
    first = date.fromisoformat(days[0])
    first -= timedelta(days=(first.weekday() + 1) % 7)
    colors = ["#192637", "#145b60", "#16888b", "#24b7b4", "#62e4dc"]
    graph = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="380" viewBox="0 0 1000 380" role="img" aria-labelledby="title desc">',
             '<title id="title">aprilyab — 3D contribution activity</title>',
             f'<desc id="desc">Public GitHub contribution calendar from {days[0]} to {days[-1]}. Taller columns represent higher activity.</desc>',
             '<rect width="1000" height="380" rx="16" fill="#0d1117"/>',
             '<g font-family="Arial, Helvetica, sans-serif"><text x="32" y="42" fill="#f0f6fc" font-size="20" font-weight="700">A year of building</text>',
             f'<text x="32" y="67" fill="#8b949e" font-size="12">@aprilyab · {days[0]} — {days[-1]}</text></g>']
    total = streak = longest = 0
    counts = {}
    for day in days:
        level, key = calendar.days[day]
        label = calendar.labels.get(key, "").strip()
        match = re.match(r"([\d,]+) contribution", label)
        if not match and not label.startswith("No contributions"):
            raise ValueError(f"Unrecognized contribution count for {day}: {label}")
        count = int(match[1].replace(",", "")) if match else 0
        counts[day] = count
        total += count
        streak = streak + 1 if count else 0
        longest = max(longest, streak)
        offset = (date.fromisoformat(day) - first).days
        week, weekday = divmod(offset, 7)
        x, y = 55 + week * 15 + weekday * 14, 228 - week * 1.65 + weekday * 8
        h = 3 + level * 15
        points = [(x, y), (x + 13, y - 3), (x + 25, y + 4), (x + 12, y + 7)]
        a, b, c, d = points
        def poly(vertices, color):
            return '<polygon points="' + ' '.join(f'{px:.1f},{py:.1f}' for px, py in vertices) + f'" fill="{color}" stroke="#0d1117" stroke-width="0.6"/>'
        graph.append(f'<g><title>{escape(day + ": " + label)}</title>')
        graph.append(poly([d, c, (c[0], c[1]-h), (d[0], d[1]-h)], "#113a45" if level else "#111c29"))
        graph.append(poly([b, c, (c[0], c[1]-h), (b[0], b[1]-h)], "#17616a" if level else "#152030"))
        graph.append(poly([(px, py-h) for px, py in points], colors[level]))
        graph.append('</g>')
    graph.append('<text x="32" y="346" fill="#8b949e" font-family="Arial, Helvetica, sans-serif" font-size="12">Each column is one day · Height and color show contribution activity</text>')
    for i, color in enumerate(colors):
        graph.append(f'<rect x="{843+i*20}" y="335" width="14" height="14" rx="3" fill="{color}"/>')
    graph.append('</svg>')
    output.mkdir(parents=True, exist_ok=True)
    (output / "contributions-3d.svg").write_text('\n'.join(graph) + '\n')
    current = 0
    # Today's unfinished day does not break the streak until tomorrow.
    active_days = days[:-1] if counts[days[-1]] == 0 else days
    for day in reversed(active_days):
        if not counts[day]:
            break
        current += 1
    card = ['<svg xmlns="http://www.w3.org/2000/svg" width="467" height="195" viewBox="0 0 467 195" role="img" aria-labelledby="title">',
            '<title id="title">Contribution statistics for aprilyab</title>',
            '<rect x="0.5" y="0.5" width="466" height="194" rx="5" fill="#0d1117" stroke="#30363d"/>',
            '<g font-family="Arial, Helvetica, sans-serif" text-anchor="middle">',
            '<text x="233" y="33" fill="#61dafb" font-size="17" font-weight="700">Contribution activity</text>']
    for x, value, label in [(80, f"{total:,}", "Past year"), (233, str(current), "Current streak"), (386, str(longest), "Longest streak")]:
        card.append(f'<text x="{x}" y="95" fill="#f0f6fc" font-size="30" font-weight="700">{value}</text><text x="{x}" y="122" fill="#8b949e" font-size="12">{label}</text>')
    card.append(f'<text x="233" y="168" fill="#8b949e" font-size="11">Streaks in days · Updated {days[-1]}</text></g></svg>')
    (output / "contribution-stats.svg").write_text('\n'.join(card) + '\n')
    print(f"Rendered {len(days)} days, {total:,} contributions, longest streak {longest} days")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Use a downloaded public GitHub calendar")
    args = parser.parse_args()
    if args.input:
        source = args.input.read_text()
    else:
        request = Request("https://github.com/users/aprilyab/contributions", headers={"User-Agent": "aprilyab-profile"})
        with urlopen(request, timeout=45) as response:
            source = response.read().decode()
    render(source, Path(__file__).resolve().parents[1] / "assets")
