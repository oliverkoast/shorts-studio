"""Render one kit scene on its own, in the current brand, with a contact sheet.

  studio kit <scene.json> <out.mp4>          scene.json is the KIT dict: {"dur": 3, "scene": "counter", ...}
  studio kit gallery <out dir>               every scene once, as a brand preview

Contact sheets land in graphics-review/ next to the output."""
import json, os, sys
from . import lib

GALLERY = [
    dict(dur=3, scene="counter", ground="ink", value=18.1, decimals=1, suffix="M", label="the number, exact, with its unit", t0=0.2, t1=1.6),
    dict(dur=3, scene="keyword", ground="marine", lines=[["ONE IDEA", 0.2], ["PER CARD", 0.7]], sub="a short sub-line"),
    dict(dur=3, scene="versus", ground="marine", title="BEFORE AND AFTER", a=dict(value="10 SECONDS", label="with the tool", t=0.2, w=0.05),
         b=dict(value="30 MINUTES", label="by hand", t=0.9, w=1.0)),
    dict(dur=3, scene="diagram", ground="ink", title="HOW IT WORKS", nodes=[dict(id="a", label="INPUT", x=540, y=620, t=0.2),
         dict(id="b", label="THE MODEL", x=540, y=950, t=0.8, accent=True), dict(id="c", label="OUTPUT", x=540, y=1280, t=1.4)],
         edges=[{"from": "a", "to": "b", "t": 0.6}, {"from": "b", "to": "c", "t": 1.2}]),
    dict(dur=3, scene="height", ground="ink", ground_y=1250, top_y=640, items=[dict(label="REFERENCE", h=93, kind="statue", w=12, t=0.05),
         dict(label="RIVAL", h=110.6, w=10, t=0.2), dict(label="SUBJECT", h=124, w=9, t=0.4, accent=True)],
         counter=dict(value=124, suffix=" m", sub="407 ft"), source="Source: official figures"),
    dict(dur=3, scene="quote", ground="marine", text="A short line someone really said.", size=84, name="Speaker Name", role="their role", t0=0.1),
    dict(dur=3, scene="timeline", ground="ink", title="WHAT HAPPENED", items=[dict(t=0.3, date="2024", text="first thing"),
         dict(t=1.0, date="2025", text="second thing"), dict(t=1.7, date="NOW", text="where it stands")]),
    dict(dur=3, scene="logo", ground="bronze", title="MY SHOW", sub="FULL EPISODE ON YOUTUBE", t0=0.1),
]

if __name__ == "__main__":
    a = sys.argv[1:]
    lib.use_brand()
    if a[0] == "gallery":
        out = os.path.abspath(a[1]); os.makedirs(out, exist_ok=True)
        lib.REVIEW = os.path.join(out, "graphics-review")
        jobs = [(dict(s, hud=s["scene"].upper()), os.path.join(out, f"{k:02d}-{s['scene']}.mp4")) for k, s in enumerate(GALLERY)]
        if lib.BRAND.get("logo"): jobs[-1][0]["logo"] = lib.BRAND["logo"]
        lib.kit_batch(jobs, 6)
        for _, o in jobs: print(lib.kit_review(o))
    else:
        spec = json.load(open(a[0])); out = os.path.abspath(a[1])
        lib.REVIEW = os.path.join(os.path.dirname(out), "graphics-review")
        lib.kit_render(spec, out)
        print(out); print(lib.kit_review(out))
        probs = lib.layout_check(spec, band=spec.get("band"), mp4=out)
        print("layout:", "ok" if not probs else probs)
