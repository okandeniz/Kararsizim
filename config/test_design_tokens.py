"""Tasarım token'ları: sabit renk yasağı ve WCAG AA kontrast kontrolü (plan Bölüm 6, Faz 6).

CSS'teki renkler yalnızca :root içinde tanımlanır; başka her yerde token kullanılır. Kontrast
oranları token değerlerinden hesaplanır, böylece bir renk değişince AA bozulursa test düşer.
"""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parent.parent / "static"
CSS = (STATIC / "css" / "app.css").read_text(encoding="utf-8")
JS = (STATIC / "js" / "app.js").read_text(encoding="utf-8")
CSS_WITHOUT_COMMENTS = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)

root_match = re.search(r":root\s*\{(.*?)\n\}", CSS_WITHOUT_COMMENTS, flags=re.S)
assert root_match, ":root bloğu bulunamadı"
ROOT = root_match.group(1)
OUTSIDE_ROOT = CSS_WITHOUT_COMMENTS[: root_match.start()] + CSS_WITHOUT_COMMENTS[root_match.end() :]
TOKENS = {name: value.strip() for name, value in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", ROOT)}


def resolve(name: str) -> str:
    """Token değerini döndürür; var(--baska) başvurularını çözer."""
    value = TOKENS[name]
    while value.startswith("var(--"):
        value = TOKENS[value[len("var(--") : -1]]
    return value


def luminance(hex_color: str) -> float:
    digits = hex_color.lstrip("#")
    channels = [int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


# ---------- Sabit renk yasağı ----------


def test_no_hardcoded_colors_outside_root():
    # (?<![\w-]) / (?![\w-]): "white-space" gibi özellik adları renk adı sayılmaz.
    offenders = re.findall(
        r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\(|(?<![\w-])(?:white|black)(?![\w-])",
        OUTSIDE_ROOT,
    )
    assert not offenders, f"Renkler :root token'larından gelmeli, sabit renk bulundu: {offenders}"


def test_required_tokens_exist():
    for name in (
        "gradient-strong",
        "on-primary",
        "track",
        "c1-on",
        "c2-on",
        "c3-on",
        "c4-on",
        "c5-on",
    ):
        assert name in TOKENS


def test_every_class_added_by_js_has_css():
    classes = set(re.findall(r'classList\.(?:add|toggle)\("([\w-]+)"', JS))

    assert classes, "JS'te sınıf ekleyen kod bulunamadı (test eskimiş olabilir)"
    for css_class in classes:
        assert f".{css_class}" in CSS, f"app.js '{css_class}' ekliyor ama CSS'te tanımı yok"


# ---------- Kontrast (WCAG AA) ----------

TEXT_ON_SURFACES = [
    (fg, bg)
    for fg in ("text", "muted")
    for bg in (
        "surface",
        "bg",
        "primary-tint",
        "c1-tint",
        "c2-tint",
        "c3-tint",
        "c4-tint",
        "c5-tint",
    )
] + [
    ("primary", "surface"),
    ("primary", "bg"),
    ("primary", "primary-tint"),
    ("danger", "surface"),
    ("on-primary", "primary"),
    ("on-primary", "primary-hover"),
    ("c1-on", "c1"),
    ("c2-on", "c2"),
    ("c3-on", "c3"),
    ("c4-on", "c4"),
    ("c5-on", "c5"),
]


@pytest.mark.parametrize(("foreground", "background"), TEXT_ON_SURFACES)
def test_text_contrast_meets_aa(foreground, background):
    ratio = contrast(resolve(foreground), resolve(background))
    assert ratio >= 4.5, f"--{foreground} / --{background}: {ratio:.2f}:1 (en az 4.5 gerekir)"


def test_primary_button_text_meets_aa_on_every_gradient_stop():
    stops = re.findall(r"#[0-9a-fA-F]{6}", TOKENS["gradient-strong"])

    assert len(stops) == 3
    for stop in stops:
        ratio = contrast(resolve("on-primary"), stop)
        assert ratio >= 4.5, f"Beyaz metin / {stop}: {ratio:.2f}:1"


def test_light_brand_gradient_is_only_used_as_a_text_fill():
    # Açık --gradient (logo, dekoratif sayı) yalnızca metin dolgusu olabilir. Üzerinde beyaz metin
    # olan yüzeyler (butonlar) koyulaştırılmış --gradient-strong kullanmalı.
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", OUTSIDE_ROOT):
        if re.search(r"background:\s*var\(--gradient\)\s*;", body):
            assert "background-clip: text" in body, (
                f"{selector.strip()}: açık gradyan metin taşıyan bir yüzeyde kullanılmamalı"
            )
    assert re.search(r"background:\s*var\(--gradient-strong\)", OUTSIDE_ROOT)
