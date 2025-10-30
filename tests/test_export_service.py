from services.export_service import render_text_export, render_csv_export


def test_render_text_export_basic():
    gen = {
        "platform": "ozon",
        "product_name": "Mouse",
        "features": "2.4G, silent",
        "title": "Wireless Mouse",
        "short_description": "Compact wireless mouse",
        "bullets": ["Silent click", "12 months battery"],
    }
    out = render_text_export(gen)
    assert "Title: Wireless Mouse" in out
    assert "Bullets:" in out
    assert out.endswith("\n")


def test_render_csv_export_basic():
    gen = {
        "platform": "ozon",
        "product_name": "Mouse",
        "features": "2.4G, silent",
        "title": "Wireless Mouse",
        "short_description": "Compact wireless mouse",
        "bullets": ["Silent click", "12 months battery"],
    }
    csv_text = render_csv_export(gen)
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    assert len(lines) == 2  # header + one row
    assert "platform,product_name,features,title,short_description,bullets_joined" in lines[0]

