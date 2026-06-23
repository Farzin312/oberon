from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


def test_dashboard_uses_local_operational_shell() -> None:
    html = (DASHBOARD / "index.html").read_text()
    js = (DASHBOARD / "app.js").read_text()

    assert "fonts.googleapis.com" not in html
    assert "style=" not in html
    assert "Welcome to Oberon" not in html
    assert "Select or create a portfolio" in html
    assert 'value="vegetation_disturbance"' in html
    assert 'id="port-task"' in html
    assert '<select id="port-task"' not in html
    assert "After creation, add an AOI" in html
    assert "burn_severity" not in html
    assert "Burn Severity" not in js


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


def test_dashboard_mobile_dialogs_are_viewport_bounded() -> None:
    css = (DASHBOARD / "style.css").read_text()

    assert "top: 50dvh;" in css
    assert "left: 50dvw;" in css
    assert "max-height: calc(100dvh - 32px);" in css
    assert "overflow-y: auto;" in css
