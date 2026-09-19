"""
The installable site: the designer wrapped with a manifest, icons and an
offline cache, and nothing else changed.
"""
import json
import struct

import pytest

from chalktalk import designer
from chalktalk.designer import site


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    # Small stand-in icons keep the test quick; the real ones are drawn below.
    icons = {name: site.draw_icon(16, spec[1], spec[2]) for name, spec in site.ICONS.items()}
    return tmp_path_factory.mktemp("site") / "out", icons


def _png_size(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_the_site_has_everything_an_installable_app_needs(built):
    out, icons = built
    site.build_site(str(out), icons=icons)
    names = {p.name for p in out.iterdir()}
    assert names == {"index.html", "manifest.webmanifest", "sw.js", *site.ICONS}

    manifest = json.loads((out / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["display"] == "standalone" and manifest["start_url"] == "./"
    assert {i["purpose"] for i in manifest["icons"]} == {"any", "maskable"}
    for icon in manifest["icons"]:
        assert (out / icon["src"]).exists()

    index = (out / "index.html").read_text(encoding="utf-8")
    assert '<link rel="manifest" href="manifest.webmanifest">' in index
    assert 'navigator.serviceWorker.register("sw.js")' in index
    assert "apple-touch-icon.png" in index


def test_the_offline_cache_lists_every_file_it_serves(built):
    out, icons = built
    site.build_site(str(out), icons=icons)
    sw = (out / "sw.js").read_text(encoding="utf-8")
    files = json.loads(sw[sw.index("const FILES = ") + len("const FILES = "):sw.index(";", sw.index("const FILES"))])
    assert files[0] == "./"
    for name in files[1:]:
        assert (out / name).exists(), name
    assert "sw.js" not in files


def test_a_new_build_gets_a_new_cache(tmp_path, built):
    _, icons = built
    a = site.build_site(str(tmp_path / "a"), icons=icons)
    b = site.build_site(str(tmp_path / "b"), icons=icons, theme="paper")
    version = lambda p: open(p + "/sw.js", encoding="utf-8").read().split('"chalktalk-')[1][:12]
    assert version(a) != version(b)
    assert version(a) == version(site.build_site(str(tmp_path / "c"), icons=icons))


def test_the_designer_inside_is_the_designer(built):
    """The site only wraps the file: the app between the tags is byte-for-byte the same."""
    html = site.site_index()
    plain = designer.build()
    script = plain[plain.index("<script>"):plain.rindex("</script>")]
    assert script in html
    assert plain.count("</script>") == 1          # the template itself is unchanged


def test_icons_are_real_pngs_of_the_right_size():
    for size, full, content in [(48, False, 0.8), (40, True, 0.62)]:
        data = site.draw_icon(size, full, content)
        assert _png_size(data) == (size, size)


def test_the_cli_builds_the_site(tmp_path, monkeypatch):
    from chalktalk import cli
    monkeypatch.setattr(site, "draw_icon", lambda size, full, content: site._png(1, 1, [b"\0\0\0\0"]))
    assert cli.main(["site", "--out", str(tmp_path / "site")]) == 0
    assert (tmp_path / "site" / "index.html").exists()
