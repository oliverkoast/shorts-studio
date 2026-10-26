"""Check chosen b-roll against the script before it goes in a Short.

  studio broll-sheet clips.json script.md [out.jpg]

clips.json: [{"id", "line", "src", "t", "d", "what", "credit", "license", "kind": "footage"|"collage"|"graphic"}]
script.md:  numbered lines ("1. In 1966, ...").

Writes a contact sheet with THREE frames per clip (start, middle, end), because a clip that starts on the wrong
shot looks right at its midpoint, labelled with the script line, source and license. With tesseract installed it
also reads the on-screen text in every frame and flags years or labels that contradict the script line.
Prints a report; exit code 1 if anything is flagged. Read the sheet yourself as well: the check cannot tell a
modern plane from a 1984 one."""
import json, os, re, subprocess, sys, tempfile, textwrap, shutil

YEAR = re.compile(r"\b(1[89]\d\d|20\d\d)\b")


def frame(src, t, out, w=320, h=180):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(t, 0):.3f}", "-i", src, "-frames:v", "1",
                    "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x16181D", out],
                   check=True)


def ocr(src, t):
    if not shutil.which("tesseract"): return None
    f = os.path.abspath(f".ocr-{os.getpid()}.png")            # next to the work, where tesseract can read it
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(t, 0):.3f}", "-i", src, "-frames:v", "1",
                    "-vf", "scale=iw*2:-1,format=gray", f], check=True)
    r = subprocess.run(["tesseract", f, "-", "--psm", "11"], capture_output=True, text=True)
    os.remove(f)
    return " ".join(r.stdout.split())


def main(a):
    from PIL import Image, ImageDraw, ImageFont
    clips = json.load(open(a[0]))
    lines = {int(l.split(".")[0]): l.split(". ", 1)[1].strip() for l in open(a[1]) if re.match(r"^\d+\.", l)}
    out = a[2] if len(a) > 2 else "broll contact sheet.jpg"
    from . import brand
    b = brand.load()
    F = ImageFont.truetype(b["fonts"]["display"]["file"], 20); R = ImageFont.truetype(b["fonts"]["text"]["file"], 16)
    fw, fh, pad, cap = 320, 180, 18, 120
    cw = 3 * fw + 2 * 4
    cols = 3
    rows = (len(clips) + cols - 1) // cols
    W = cols * (cw + pad) + pad; H = rows * (fh + cap + pad) + pad
    sheet = Image.new("RGB", (W, H), (22, 24, 29)); d = ImageDraw.Draw(sheet)
    flags = []
    tmp = tempfile.mkdtemp()
    for k, c in enumerate(clips):
        x0, y0 = pad + (k % cols) * (cw + pad), pad + (k // cols) * (fh + cap + pad)
        line = lines.get(c["line"], "")
        want = set(YEAR.findall(line))
        for j, frac in enumerate((0.05, 0.5, 0.95)):
            t = c["t"] + c["d"] * frac
            p = os.path.join(tmp, f"{k}_{j}.png")
            if c.get("src", "kit") == "kit" or not os.path.exists(c.get("src", "")):
                Image.new("RGB", (fw, fh), (36, 50, 74)).save(p)
            else:
                frame(c["src"], t, p, fw, fh)
                txt = ocr(c["src"], t)
                if txt:
                    seen = set(YEAR.findall(txt))
                    bad = seen - want if want else set()
                    if bad:
                        flags.append(f"clip {c['id']} (line {c['line']}): on-screen year {', '.join(sorted(bad))} at {t:.1f} s, "
                                     f"but the line says {', '.join(sorted(want))}")
            sheet.paste(Image.open(p), (x0 + j * (fw + 4), y0))
        if c.get("kind") == "collage":
            flags.append(f"clip {c['id']} (line {c['line']}): another creator's designed collage, not clean footage; "
                         "prefer a clean frame, or note it in sources.md")
        yy = y0 + fh + 8
        d.text((x0, yy), f"{c['id']}  line {c['line']}  ·  {c.get('kind', 'footage')}", font=F, fill=(242, 193, 78)); yy += 26
        for t_ in textwrap.wrap(line, 70)[:2]: d.text((x0, yy), t_, font=R, fill=(247, 247, 245)); yy += 20
        for t_ in textwrap.wrap(f"{c.get('what', '')}. {c.get('credit', '')}. {c.get('license', '')}", 76)[:3]:
            d.text((x0, yy), t_, font=R, fill=(160, 170, 185)); yy += 19
    sheet.save(out, quality=88)
    print("contact sheet:", out, "(start, middle and end frame of every clip)")
    if not shutil.which("tesseract"):
        print("note: tesseract is not installed, so on-screen text was not read; check dates and labels by eye")
    else:
        print("note: text reading catches printed text; hand-drawn or stylised dates often slip past it, so read every "
              "frame's dates and labels yourself")
    for f in flags: print("FLAG", f)
    print("ok" if not flags else f"{len(flags)} flag(s): fix them or explain them in sources.md")
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
