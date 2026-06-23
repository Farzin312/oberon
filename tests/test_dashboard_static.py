from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


def test_dashboard_uses_local_operational_shell() -> None:
    html = (DASHBOARD / "index.html").read_text()

    assert "fonts.googleapis.com" not in html
    assert "style=" not in html
    assert "Welcome to Oberon" not in html
    assert "Select or create a portfolio" in html


def test_dashboard_css_avoids_decorative_ai_tropes() -> None:
    css = (DASHBOARD / "style.css").read_text()

    banned = [
        "glassmorphism",
        "backdrop-filter",
        "btn-primary-gradient",
        "title-gradient",
        "@keyframes float",
    ]
    for token in banned:
        assert token not in css
