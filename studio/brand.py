"""Brands: plain files in ~/.shorts-studio/brands/<name>/ (theme.json, fonts/, logo, optional texture).

  python -m studio.brand list
  python -m studio.brand show <name>
  python -m studio.brand init <name> [--from <name>]          copy a brand to start a new one
  python -m studio.brand font <name> display|text <file.ttf>  add a font (variable fonts become static instances)
  python -m studio.brand use <name> [<video folder>]          write shorts-studio.json in a video folder

A video folder's shorts-studio.json names its brand; every render reads the brand from there.
"""
import json, os, shutil, subprocess, sys

HOME = os.path.expanduser(os.environ.get("SHORTS_STUDIO_HOME", "~/.shorts-studio"))
BRANDS = os.path.join(HOME, "brands")
PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = os.path.join(PKG, "brands", "default")


def brand_dir(name):
    return os.path.join(BRANDS, name)


def ensure_default():
    """Copy the shipped neutral brand into the user's brands folder on first use."""
    d = brand_dir("default")
    if not os.path.exists(os.path.join(d, "theme.json")):
        os.makedirs(BRANDS, exist_ok=True)
        shutil.copytree(DEFAULT_SRC, d, dirs_exist_ok=True)
    return d


def project_brand_name(folder="."):
    p = os.path.join(folder, "shorts-studio.json")
    if os.path.exists(p):
        return json.load(open(p)).get("brand", "default")
    return "default"


def load(name=None, folder="."):
    """The brand as a dict, with every file path made absolute. Falls back to the default brand."""
    ensure_default()
    name = name or project_brand_name(folder)
    d = brand_dir(name)
    if not os.path.exists(os.path.join(d, "theme.json")):
        raise SystemExit(f"brand '{name}' not found in {BRANDS}. Run /brand to create it, or use 'default'.")
    b = json.load(open(os.path.join(d, "theme.json")))
    b["dir"] = d
    for k in ("logo", "texture", "texture2"):
        if b.get(k): b[k] = os.path.join(d, b[k])
    for k, f in (b.get("fonts") or {}).items():
        f["file"] = os.path.join(d, f["file"])
    return b


def kit_brand(b):
    """The brand as the kit page wants it: file:// URLs."""
    u = lambda p: "file://" + p if p else None
    return {"colors": b["colors"], "hud": b.get("hud", ""), "logo": u(b.get("logo")), "texture": u(b.get("texture")),
            "texture2": u(b.get("texture2")),
            "fonts": {k: {"family": v["family"], "file": u(v["file"])} for k, v in b["fonts"].items()}}


def ass_colour(hexcol, alpha=0):
    h = hexcol.lstrip("#")
    r, g, bl = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{bl}{g}{r}".upper()


def static_font(src, dst, weight):
    """A static instance of a variable font at one weight (libass and PIL want static files)."""
    py = sys.executable
    r = subprocess.run([py, "-m", "fontTools.varLib.instancer", src, f"wght={weight}", "--update-name-table", "-o", dst],
                       capture_output=True, text=True)
    if r.returncode:                      # not a variable font: use it as it is
        shutil.copy(src, dst)
    return dst


def family_name(path):
    from fontTools.ttLib import TTFont
    f = TTFont(path)
    names = {n.nameID: n.toUnicode() for n in f["name"].names if n.platformID in (1, 3)}
    return names.get(16) or names.get(1)


def add_font(name, role, src):
    d = brand_dir(name); os.makedirs(os.path.join(d, "fonts"), exist_ok=True)
    weight = 700 if role == "display" else 400
    base = os.path.splitext(os.path.basename(src))[0].replace("[", "").replace("]", "").replace(",", "")
    dst = os.path.join(d, "fonts", f"{base}-{weight}.ttf")
    static_font(src, dst, weight)
    t = json.load(open(os.path.join(d, "theme.json")))
    t.setdefault("fonts", {})[role] = {"family": family_name(dst), "file": os.path.relpath(dst, d)}
    json.dump(t, open(os.path.join(d, "theme.json"), "w"), indent=2)
    return t["fonts"][role]


def main(a):
    ensure_default()
    if not a or a[0] == "list":
        for n in sorted(os.listdir(BRANDS)):
            if os.path.exists(os.path.join(BRANDS, n, "theme.json")): print(n)
    elif a[0] == "show":
        print(json.dumps(load(a[1]), indent=2))
    elif a[0] == "init":
        src = brand_dir(a[a.index("--from") + 1]) if "--from" in a else brand_dir("default")
        dst = brand_dir(a[1])
        if os.path.exists(dst): raise SystemExit(f"{dst} already exists")
        shutil.copytree(src, dst)
        t = json.load(open(os.path.join(dst, "theme.json"))); t["name"] = a[1]
        json.dump(t, open(os.path.join(dst, "theme.json"), "w"), indent=2)
        print(dst)
    elif a[0] == "font":
        print(add_font(a[1], a[2], a[3]))
    elif a[0] == "use":
        folder = a[2] if len(a) > 2 else "."
        load(a[1])
        p = os.path.join(folder, "shorts-studio.json")
        s = json.load(open(p)) if os.path.exists(p) else {}
        s["brand"] = a[1]
        json.dump(s, open(p, "w"), indent=2)
        print(p)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
