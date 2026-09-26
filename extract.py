"""Nightly copy of the published oaci.africa pages into this repo.
Reads only the public site. Writes pages/<slug>.md and images/<slug>/..."""
import hashlib, os, re, urllib.parse, urllib.request
from playwright.sync_api import sync_playwright

BASE = "https://www.oaci.africa"
PAGES = {
    "home": "/",
    "about": "/about",
    "platform": "/platform",
    "partner": "/partner",
    "one-health": "/solutions/one-health",
    "public-health": "/solutions/public-health",
    "human-health": "/solutions/public-health/human-health",
    "animal-health": "/solutions/public-health/animal-health",
    "food-safety": "/solutions/food-safety",
    "food-security": "/solutions/food-security",
    "environmental-health": "/solutions/environmental-health",
    "laboratory-networks": "/solutions/laboratory-networks",
    "emergency-response": "/solutions/emergency-response",
}

STRIP_JS = """() => {
  document.querySelectorAll('header, nav, footer, script, style, noscript, form')
    .forEach(e => e.remove());
}"""

def save_image(src, folder):
    name = os.path.basename(urllib.parse.urlparse(src).path) or "image"
    if not re.search(r"\.(webp|png|jpe?g|gif|svg)$", name, re.I):
        name += "-" + hashlib.md5(src.encode()).hexdigest()[:8] + ".img"
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        try:
            req = urllib.request.Request(src, headers={"User-Agent": "OACI-sync"})
            with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
                f.write(r.read())
        except Exception as e:
            print("  image skipped:", src, e)
            return None
    return path

def main():
    os.makedirs("pages", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for slug, path in PAGES.items():
            url = BASE + path
            print("Fetching", url)
            page.goto(url, wait_until="networkidle", timeout=120000)
            page.wait_for_timeout(3000)
            page.evaluate("async () => { for (let y=0; y<document.body.scrollHeight; y+=800) { window.scrollTo(0,y); await new Promise(r=>setTimeout(r,150)); } }")
            page.evaluate(STRIP_JS)
            text = page.evaluate("() => document.body.innerText")
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            imgs = page.evaluate("""() => Array.from(document.images)
                .filter(i => i.offsetParent !== null)
                .map(i => ({src: i.currentSrc || i.src, alt: i.alt || ''}))""")
            folder = os.path.join("images", slug)
            os.makedirs(folder, exist_ok=True)
            lines, seen = [], set()
            for im in imgs:
                src = im["src"]
                if not src or src.startswith("data:") or src in seen:
                    continue
                seen.add(src)
                saved = save_image(src, folder)
                if saved:
                    lines.append(f"- {saved} | {im['alt']}")
            with open(f"pages/{slug}.md", "w", encoding="utf-8") as f:
                f.write(f"# {slug}\n\nSource: {url}\n\n{text}\n\n## Images\n\n" + "\n".join(lines) + "\n")
        browser.close()

if __name__ == "__main__":
    main()
