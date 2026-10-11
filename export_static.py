"""Render the UI with every city's forecast embedded into one self-contained file: docs/index.html.

Host it anywhere static (GitHub Pages from /docs, a Hugging Face Static Space). Re-run after train.py.
"""
from app import ROOT, app

out = ROOT / "docs" / "index.html"
out.parent.mkdir(exist_ok=True)
html = app.test_client().get("/").data
out.write_bytes(html)
print(f"wrote {out} ({len(html) / 1024:.0f} KB)")
