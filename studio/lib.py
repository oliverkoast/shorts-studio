"""Shorts Studio core builder.

A spec gives rows of real talk (word-index ranges of a CTC word list), shots cued by word, and graphics
cued by word. The builder cuts the audio on word boundaries (pauses capped, never stitched across the
source order), renders each shot piece with ffmpeg, then burns captions and graphics from one ASS file.
"""
import json, math, os, random, re, shutil, struct, subprocess, wave

FPS = 30
W, H = 1080, 1920
from . import brand as _brand

# The brand drives every colour and font. use_brand() is called by a Short's spec (or defaults on import).
BRAND = None
FONTDIR = None
BONE = INK = SAND = NAVY = None
DISPLAY_FONT = TEXT_FONT = None


def use_brand(name=None, folder="."):
    global BRAND, FONTDIR, BONE, INK, SAND, NAVY, DISPLAY_FONT, TEXT_FONT
    BRAND = _brand.load(name, folder)
    c = BRAND["colors"]
    BONE, INK, SAND, NAVY = (_brand.ass_colour(c["light"]), _brand.ass_colour(c["dark"]), _brand.ass_colour(c["accent"]),
                             _brand.ass_colour(c["deep"]))
    DISPLAY_FONT, TEXT_FONT = BRAND["fonts"]["display"], BRAND["fonts"]["text"]
    FONTDIR = os.path.dirname(DISPLAY_FONT["file"])
    return BRAND
FFX = ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS)]


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise SystemExit("FAILED: " + " ".join(map(str, cmd))[:600] + "\n" + r.stderr[-3000:])
    return r


# ---------------------------------------------------------------- audio plan
_ENV = {}


def energy_track(audio):
    """10 ms RMS (dBFS) of a whole source file, 16 kHz mono, cached."""
    import numpy as np
    if audio not in _ENV:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        f = x[:len(x) // 160 * 160].reshape(-1, 160)
        _ENV[audio] = 20 * np.log10(np.sqrt((f ** 2).mean(1)) + 1e-9)
    return _ENV[audio]


def valley(audio, lo, hi, side):
    """The quietest 10 ms frame between lo and hi (source seconds). CTC onsets can be late by up to 100 ms
    (the 'I' in Short 1 began at 570.16 s, CTC said 570.24 s), so cuts go where the audio is actually quiet."""
    e = energy_track(audio)
    a, b = max(0, int(lo * 100)), min(len(e) - 1, int(hi * 100))
    if b <= a: return lo if side == "end" else hi
    seg = e[a:b + 1]; m = seg.min()
    thr = max(m + 3, -50)                                    # quiet = room tone, not a breath, smack or a word's onset
    quiet = [i for i, v in enumerate(seg) if v <= thr]
    i = quiet[0] if side == "end" else quiet[-1]          # end: first quiet frame after the word; start: last quiet frame before it
    return (a + i) / 100 + (0.0 if side == "end" else 0.01)


def plan(words, rows, maxgap=0.30, pad=0.15, tail=0.06, audio=None, offset=0.0):
    """rows: [{"keep": [(i0, i1), ...], "text": "clean words for every kept word"}].
    Returns pieces [(src_a, src_b, out_a)], wmap {idx: (out_t0, out_t1)}, cap [(idx, text)]."""
    kept, cap, pre = [], [], {}
    for r in rows:
        if "pre" in r: pre[r["keep"][0][0]] = r["pre"]
        ids = [i for a, b in r["keep"] for i in range(a, b + 1)]
        toks = r["text"].split()
        if len(toks) != len(ids):
            raise SystemExit(f"text/word count mismatch {len(toks)} vs {len(ids)}: {r['text'][:60]}\n"
                             + " ".join(words[i]["w"] for i in ids))
        kept += ids
        cap += list(zip(ids, toks))
    pieces, cur = [], None
    for k, i in enumerate(kept):
        w = words[i]
        if cur is None:
            cur = [w["t0"] - pre.get(i, pad), None]
        nxt = kept[k + 1] if k + 1 < len(kept) else None
        if nxt is None:
            cur[1] = w["t1"] + pad + tail
            pieces.append(cur); break
        g = words[nxt]["t0"] - w["t1"]
        if nxt != i + 1 or g > maxgap:
            half = min(pad, max(0.04, g / 2)) if nxt == i + 1 else pad
            cur[1] = w["t1"] + min(half + tail, max(g - 0.02, 0.03)) if nxt == i + 1 else w["t1"] + pad + tail
            pieces.append(cur)
            cur = None
    # a pad must never reach into a word that was dropped (the "I do have it" fragment at Short 1, 7 s)
    keepset = set(kept)
    fixed = []
    for a, b in pieces:
        ia = min((i for i in kept if words[i]["t0"] >= a - 1e-6), key=lambda i: words[i]["t0"])
        ib = max((i for i in kept if words[i]["t1"] <= b + 1e-6), key=lambda i: words[i]["t1"])
        if ia - 1 >= 0 and ia - 1 not in keepset:
            a = max(a, words[ia - 1]["t1"] + 0.03)
        if ib + 1 < len(words) and ib + 1 not in keepset:
            b = min(b, words[ib + 1]["t0"] - 0.03)
        fixed.append([a, b])
    pieces = fixed
    if audio:
        # move every boundary into the quietest moment of its gap, measured on the source audio
        fixed = []
        for a, b in pieces:
            ia = min((i for i in kept if words[i]["t0"] >= a - 1e-6), key=lambda i: words[i]["t0"])
            ib = max((i for i in kept if words[i]["t1"] <= b + 1e-6), key=lambda i: words[i]["t1"])
            lo = words[ia - 1]["t1"] + 0.02 if ia > 0 else a - 0.25
            hi_e = words[ib + 1]["t0"] - 0.02 if ib + 1 < len(words) else b + 0.25
            a2 = valley(audio, max(lo, words[ia]["t0"] - 0.30) + offset, words[ia]["t0"] - 0.01 + offset, "start") - offset
            b2 = valley(audio, words[ib]["t1"] + 0.03 + offset, min(hi_e, words[ib]["t1"] + 0.30) + offset, "end") - offset
            fixed.append([min(a2, words[ia]["t0"] - 0.01), max(b2, words[ib]["t1"] + 0.03)])
        pieces = fixed
    # output times
    out, res = 0.0, []
    for a, b in pieces:
        res.append((a, b, out)); out += b - a
    wmap = {}
    for i in kept:
        for a, b, o in res:
            if a - 1e-6 <= words[i]["t0"] <= b:
                wmap[i] = (o + words[i]["t0"] - a, o + min(words[i]["t1"], b) - a); break
    return res, wmap, cap, out


def src_to_out(res, s):
    for a, b, o in res:
        if a <= s <= b: return o + s - a
    return None


def out_to_src(res, t):
    for a, b, o in res:
        if o <= t < o + (b - a) + 1e-6: return a + t - o
    a, b, o = res[-1]
    return b


def render_audio(res, src, dst, sr=48000, pre_gain_db=0.0):
    """Cut pieces from src with 8 ms fades, concat, two-pass loudnorm to -14 LUFS / -1 dBTP."""
    tmp = dst + ".raw.wav"
    import numpy as np
    # level-match the joined pieces: voiced level (loudest 40% of 20 ms frames) pulled toward the median
    lv = []
    for a, b, o in res:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.4f}", "-t", f"{b - a:.4f}", "-i", src, "-ac", "1", "-ar", "16000",
                              "-f", "s16le", "-"], capture_output=True).stdout
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        if len(x) < 640: lv.append(None); continue
        f = x[:len(x) // 320 * 320].reshape(-1, 320); e = np.sqrt((f ** 2).mean(1) + 1e-12); e = np.sort(e)[int(len(e) * 0.6):]
        lv.append(20 * np.log10(e.mean() + 1e-9))
    med = float(np.median([v for v in lv if v is not None]))
    gains = [0.0 if v is None else float(np.clip((med - v) * 0.85, -6, 6)) for v in lv]
    fc, labels = [], []
    for k, (a, b, o) in enumerate(res):
        d = b - a; fd = min(0.012, d / 4)
        fc.append(f"[0:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS,aformat=sample_rates={sr}:channel_layouts=stereo,volume={gains[k]:.2f}dB,"
                  f"afade=t=in:d={fd:.4f},afade=t=out:st={max(d - fd, 0):.4f}:d={fd:.4f}[a{k}]")
        labels.append(f"[a{k}]")
    fc.append("".join(labels) + f"concat=n={len(res)}:v=0:a=1[out]")
    script = dst + ".fc.txt"
    open(script, "w").write(";\n".join(fc))
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-/filter_complex", script, "-map", "[out]", tmp])
    return tmp


def loudnorm(src, dst, extra_inputs=(), mixexpr=None):
    m = run(["ffmpeg", "-hide_banner", "-i", src, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"]).stderr
    j = json.loads(m[m.rfind("{"):m.rfind("}") + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=9:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
          f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample=48000,alimiter=limit=0.84:level=false")
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", "48000", dst])


def whoosh(path, dur=0.38, sr=48000, seed=1):
    """A soft filtered-noise swell, generated here (no third-party SFX)."""
    random.seed(seed)
    n = int(dur * sr); out = []
    lp = 0.0; lp2 = 0.0
    for k in range(n):
        x = k / n
        env = math.sin(math.pi * x) ** 2
        c = 0.02 + 0.25 * x                     # rising cutoff
        lp += c * (random.uniform(-1, 1) - lp)
        lp2 += c * (lp - lp2)
        out.append(lp2 * env * 2.2)
    with wave.open(path, "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
        f.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32000)) for v in out))


# ---------------------------------------------------------------- picture
def ease_expr(keys, var="in/30"):
    """keys: [(t, value)] in clip-local seconds -> ffmpeg expression with smoothstep between keys."""
    if len(keys) == 1: return f"{keys[0][1]:.3f}"
    e = f"{keys[-1][1]:.3f}"
    for (t0, v0), (t1, v1) in reversed(list(zip(keys, keys[1:]))):
        if t1 - t0 < 1e-3:
            seg = f"{v1:.3f}"
        else:
            u = f"clip(({var}-{t0:.3f})/{t1 - t0:.3f},0,1)"
            seg = f"({v0:.3f}+({v1 - v0:.3f})*({u})*({u})*(3-2*({u})))"
        e = f"if(lt({var},{t1:.3f}),{seg},{e})"
    return f"if(lt({var},{keys[0][0]:.3f}),{keys[0][1]:.3f},{e})"


def ass_header():
    if BRAND is None: use_brand()
    D, T = DISPLAY_FONT["family"], TEXT_FONT["family"]
    return ("""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,@D@,60,%s,%s,%s,&H96000000,-1,0,0,0,100,100,0,0,1,6,2,5,40,40,0,1
Style: Box,@D@,58,%s,%s,%s,&H00000000,-1,0,0,0,100,100,0,0,3,14,0,5,40,40,0,1
Style: Key,@D@,84,%s,%s,%s,&H00000000,-1,0,0,0,100,100,-1,0,3,18,0,5,40,40,0,1
Style: Draw,@D@,20,%s,%s,%s,&H00000000,0,0,0,0,100,100,0,0,1,4,0,7,0,0,0,1
Style: Tag,@D@,38,%s,%s,%s,&H00000000,-1,0,0,0,100,100,2,0,1,0,0,4,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".replace("\n\n[Events]", "\nStyle: Cred,@T@,30,%s,%s,%s,&H00000000,0,0,0,0,100,100,0,0,1,3,0,5,40,40,0,1\n\n[Events]" % (SAND, SAND, INK)) % (BONE, BONE, INK, INK, INK, SAND, SAND, SAND, INK, SAND, SAND, INK, SAND, SAND, INK)).replace("@D@", D).replace("@T@", T)


def at(t):
    t = max(t, 0); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


_FS = {"Cap": 60, "Box": 58, "Key": 84, "Pop": 96}


def ev(layer, t0, t1, style, text):
    """One ASS event. Card and caption text that would be wider than the 960 px safe width is scaled down to fit."""
    if style in _FS and not re.search(r"\\fs\d", text):
        try:
            from PIL import ImageFont
            plain = re.sub(r"\{[^}]*\}", "", text)
            if BRAND is None: use_brand()
            f = ImageFont.truetype(DISPLAY_FONT["file"], _FS[style])
            w = f.getlength(plain) + 2 * (18 if style == "Key" else 14 if style == "Box" else 8)
            if w > 940:
                text = text.replace("}", "\\fs%d}" % int(_FS[style] * 940 / w), 1) if text.startswith("{") else "{\\fs%d}" % int(_FS[style] * 940 / w) + text
        except Exception:
            pass
    return f"Dialogue: {layer},{at(t0)},{at(t1)},{style},,0,0,0,,{text}\n"


def caption_cards(cap, wmap, maxw=4, maxc=22, gapsplit=0.14, end=None, upper=True):
    """[(t0, t1, [(idx, word)])] cards of 3-5 words split at pauses; hard swaps."""
    cards, cur = [], []
    for k, (i, w) in enumerate(cap):
        if i not in wmap: continue
        if cur:
            g = wmap[i][0] - wmap[cur[-1][0]][1]
            chars = sum(len(x) + 1 for _, x in cur) + len(w)
            if len(cur) >= maxw or chars > maxc or (g > gapsplit and len(cur) >= 2) or g > 0.45 \
                    or (cur[-1][1].endswith((".", ",", "?")) and len(cur) >= 2):
                cards.append(cur); cur = []
        cur.append((i, w))
    if cur: cards.append(cur)
    out = []
    for k, c in enumerate(cards):
        t0 = wmap[c[0][0]][0]
        t1 = wmap[cards[k + 1][0][0]][0] if k + 1 < len(cards) else (end or wmap[c[-1][0]][1] + 0.4)
        if t1 - wmap[c[-1][0]][1] > 0.6: t1 = wmap[c[-1][0]][1] + 0.6
        out.append((t0, t1, c))
    return out


def clean(w, upper=True):
    w = w.replace("_", " ")
    w = re.sub(r"[.,?!]+$", "", w) if w not in ("...",) else w
    return w.upper() if upper else w


def arrow(x, y, ang=0, size=1.0):
    """ASS drawing: an arrow whose tip sits at (x, y), pointing along ang (deg, 0 = pointing right)."""
    s = size
    pts = [(0, 0), (-46, -34), (-46, -14), (-120, -14), (-120, 14), (-46, 14), (-46, 34)]
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    P = [(x + s * (px * ca - py * sa), y + s * (px * sa + py * ca)) for px, py in pts]
    d = "m %d %d " % P[0] + "l " + " ".join("%d %d" % p for p in P[1:])
    return d


def rect(x0, y0, x1, y1):
    return f"m {x0:.0f} {y0:.0f} l {x1:.0f} {y0:.0f} {x1:.0f} {y1:.0f} {x0:.0f} {y1:.0f}"


# ---------------------------------------------------------------- shot rendering
def masks(d):
    from PIL import Image, ImageDraw
    os.makedirs(d, exist_ok=True)
    s = 4 * 230
    m = Image.new("L", (s, s), 0); ImageDraw.Draw(m).ellipse((0, 0, s - 1, s - 1), fill=255)
    m.resize((230, 230), Image.LANCZOS).save(os.path.join(d, "circle.png"))
    r = Image.new("RGBA", (s, s), (0, 0, 0, 0)); dr = ImageDraw.Draw(r)
    dr.ellipse((0, 0, s - 1, s - 1), outline=(0xE6, 0xD4, 0xC4, 255), width=4 * 7)
    r.resize((230, 230), Image.LANCZOS).save(os.path.join(d, "ring.png"))


def frames_grid(t): return int(round(t * FPS))


def render_shots(spec, res, total, work):
    """spec["shots"]: [{"t0": out_s, "t1": out_s, "kind": cam|scr|blank|face916, "free": src_s|None,
    "keys": [(out_t, (x, y, w))], "bubble": bool, "patch": [(x, y, w, h)]}]  ->  work/video.mp4"""
    os.makedirs(work, exist_ok=True); masks(work)
    clips = []
    cuts = sorted({0.0, total} | {o for a, b, o in res} | {o + b - a for a, b, o in res})
    snap_shots(spec["shots"], cuts)
    pan_cuts(spec["shots"])
    for si, sh in enumerate(spec["shots"]):
        bounds = [sh["t0"]] + [c for c in cuts if sh["t0"] < c < sh["t1"]] + [sh["t1"]]
        if sh.get("free") is not None:
            bounds = [sh["t0"], sh["t1"]] if not sh.get("bubble") else bounds
        for t0, t1 in zip(bounds, bounds[1:]):
            f0, f1 = frames_grid(t0), frames_grid(t1)
            if f1 <= f0: continue
            clips.append((si, f0, f1))
    lst = []
    for n, (si, f0, f1) in enumerate(clips):
        sh = spec["shots"][si]
        t0, d = f0 / FPS, (f1 - f0) / FPS
        a = out_to_src(res, t0 + 0.5 / FPS) - 0.5 / FPS
        out = os.path.join(work, f"c{n:03d}.mp4")
        lst.append(out)
        key = json.dumps([sh, f0, f1, a, spec.get("look", {}), os.path.getmtime(__file__), os.path.getmtime(sh["src"]) if sh.get("src") and os.path.exists(sh["src"]) else 0], sort_keys=True, default=str)
        stamp = out + ".key"
        if os.path.exists(out) and os.path.exists(stamp) and open(stamp).read() == key: continue
        ins, fc = [], []
        L = spec["look"]
        if sh["kind"] == "face916":
            s0 = a if sh.get("free") is None else sh["free"] + (t0 - sh["t0"])
            ins += ["-ss", f"{s0 + L.get('cam_off', 0):.4f}", "-t", f"{d + 0.5:.3f}", "-i", L["cam"]]
            zx = sh.get("zoom", 1.0)
            h = 1080 / zx; w = h * 9 / 16
            tr = [(p[0] - s0, p[1], p[2]) for p in sh["track"] if s0 - 2 <= p[0] <= s0 + d + 2] or [(0, sh["track"][0][1], sh["track"][0][2])]
            xe = ease_expr([(t, min(max(cx - w / 2, 0), 1920 - w)) for t, cx, cy in tr], "t")
            ye = ease_expr([(t, min(max(cy + sh.get("dy", 60) - h / 2, 0), 1080 - h)) for t, cx, cy in tr], "t")
            fc.append(f"[0:v]setpts=PTS-STARTPTS,fps={FPS},crop={w:.0f}:{h:.0f}:'{xe}':'{ye}',scale={W}:{H}:flags=lanczos,setsar=1[v]")
        elif sh["kind"] in ("fit", "clip"):
            s0 = a if sh.get("free") is None else sh["free"] + (t0 - sh["t0"])
            src = sh.get("src", L["cam"])
            ins += ["-ss", f"{max(s0, 0):.4f}", "-t", f"{d + 0.5:.3f}", "-i", src]
            hold = f"trim=end_frame=1,tpad=stop_mode=clone:stop_duration={d + 0.5:.3f}," if sh.get("hold") else ""
            if sh["kind"] == "clip":
                band = f",crop={W}:960:0:{sh['band']},pad={W}:{H}:0:0:color=0x221F1E" if sh.get("band") is not None else ""
                fc.append(f"[0:v]setpts=PTS-STARTPTS,{hold}fps={FPS},scale={W}:{H}:flags=lanczos{band},setsar=1[b1]")
            else:
                cx_, cy_, cw_, ch_ = sh["crop"]; X, Y, WW = sh["place"]; HH = int(round(WW * ch_ / cw_ / 2)) * 2
                fc.append(f"[0:v]setpts=PTS-STARTPTS,{hold}fps={FPS},split=2[s1][s2];"
                          f"[s1]crop={cw_}:{ch_}:{cx_}:{cy_},scale={WW}:{HH}:flags=lanczos,setsar=1[fg];"
                          + (f"[s2]crop={cw_}:{ch_}:{cx_}:{cy_},scale=-2:{H},crop={W}:{H},gblur=sigma=40,eq=brightness=-0.22,setsar=1[bg0];"
                             if sh.get("blurbg") else f"[s2]nullsink;color=c=0x221F1E:s={W}x{H}:r={FPS}:d={d + 0.5:.3f}[bg0];")
                          + f"[bg0][fg]overlay={X}:{Y}[b1]")
            if sh.get("bubble"):
                bx, by, bs = sh.get("bubble_crop", L.get("bubble"))
                ins += ["-ss", f"{a + L.get('cam_off', 0):.4f}", "-t", f"{d + 0.5:.3f}", "-i", L["cam"],
                        "-i", os.path.join(work, "circle.png"), "-i", os.path.join(work, "ring.png")]
                fc.append(f"[1:v]setpts=PTS-STARTPTS,fps={FPS},crop={bs}:{bs}:{bx}:{by},scale=230:230:flags=lanczos,format=rgba[bc];"
                          f"[2:v]format=gray[m];[bc][m]alphamerge[bm];[b1][bm]overlay=826:26[b2];[b2][3:v]overlay=826:26[v]")
            else:
                fc[-1] = fc[-1].replace("[b1]", "[v]")
        else:
            win = "[win]"
            if sh["kind"] == "cam":
                ins += ["-ss", f"{a + L['cam_off']:.4f}", "-t", f"{d + 0.5:.3f}", "-i", L["cam"]]
                cx, cw = L["cam_win"]
                fc.append(f"[0:v]setpts=PTS-STARTPTS,fps={FPS},crop={cw}:{cw * 5 // 4}:{cx - cw // 2}:0,scale=1000:1250:flags=lanczos,setsar=1{win}")
            elif sh["kind"] == "scr":
                s0 = a if sh.get("free") is None else sh["free"] + (t0 - sh["t0"])
                ins += ["-ss", f"{s0:.4f}", "-t", f"{d + 0.5:.3f}", "-i", L["scr"]]
                SW, SH = L["scr_size"]; PH = SW * 5 // 4; oy = (PH - SH) // 2
                keys = [(kt - t0, r) for kt, r in sh["keys"]]
                zk = [(t, SW / r[2]) for t, r in keys]; xk = [(t, r[0]) for t, r in keys]; yk = [(t, r[1] + oy) for t, r in keys]
                patches = "".join(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0x{L['ui_bg']}:t=fill," for x, y, w, h in sh.get("patch", []))
                hold = "loop=loop=-1:size=1:start=0," if sh.get("hold") else ""
                fc.append(f"[0:v]setpts=PTS-STARTPTS,{hold}fps={FPS},{patches}pad={SW}:{PH}:0:{oy}:color=0x{L['ui_bg']},"
                          f"zoompan=z='{ease_expr(zk, 'in/30')}':x='{ease_expr(xk, 'in/30')}':y='{ease_expr(yk, 'in/30')}'"
                          f":d=1:s=1000x1250:fps={FPS},setsar=1{win}")
            else:
                fc.append(f"color=c=0x{L['blank']}:s=1000x1250:r={FPS}:d={d + 0.5:.3f}{win}")
            fc.append(f"color=c=0x221F1E:s={W}x{H}:r={FPS}:d={d + 0.5:.3f}[bg];[bg]{win}overlay=40:180[b1]")
            last = "[b1]"
            if sh.get("bubble"):
                k = len([x for x in ins if x == "-i"])
                ins += ["-ss", f"{a + L['cam_off']:.4f}", "-t", f"{d + 0.5:.3f}", "-i", L["cam"],
                        "-i", os.path.join(work, "circle.png"), "-i", os.path.join(work, "ring.png")]
                bx, by, bs = L["bubble"]
                fc.append(f"[{k}:v]setpts=PTS-STARTPTS,fps={FPS},crop={bs}:{bs}:{bx}:{by},scale=230:230:flags=lanczos,format=rgba[bc];"
                          f"[{k + 1}:v]format=gray[m];[bc][m]alphamerge[bm];{last}[bm]overlay=826:26[b2];[b2][{k + 2}:v]overlay=826:26[v]")
            else:
                fc[-1] = fc[-1].replace("[b1]", "[v]")
        script = out + ".fc"
        open(script, "w").write(";".join(fc))
        run(["ffmpeg", "-v", "error", "-y", *ins, "-/filter_complex", script, "-map", "[v]",
             "-frames:v", str(f1 - f0), "-an", *FFX, out])
        open(stamp, "w").write(key)
    cl = os.path.join(work, "clips.txt")
    open(cl, "w").write("".join(f"file '{p}'\n" for p in lst))
    vid = os.path.join(work, "video.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", cl, "-c", "copy", vid])
    return vid


def finish(vid, aud, ass, dst, review):
    run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", aud, "-vf", f"ass={ass}:fontsdir={FONTDIR}",
         "-map", "0:v", "-map", "1:a", *FFX, "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", dst])
    run(["ffmpeg", "-v", "error", "-y", "-i", dst, "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264", "-preset", "medium",
         "-crf", "25", "-maxrate", "2500k", "-bufsize", "5000k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", review])


# ---------------------------------------------------------------- face tracking (template match, smoothed)
def track_face(src, t0, t1, cx, cy, fps=5, scale=4, tw=48, th=60, search=40, smooth=1.6):
    """Follow a face from (cx, cy) at src time t0. Returns [(src_t, cx, cy)] in full-res pixels, smoothed."""
    import numpy as np
    w, h = 1920 // scale, 1080 // scale
    raw = run_bytes(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", src, "-vf",
                     f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"])
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    x, y = cx / scale, cy / scale
    def patch(f, x, y):
        x0, y0 = int(round(x - tw / 2)), int(round(y - th / 2))
        x0 = min(max(x0, 0), w - tw); y0 = min(max(y0, 0), h - th)
        return f[y0:y0 + th, x0:x0 + tw]
    T = patch(fr[0], x, y).copy()
    pts = []
    for k, f in enumerate(fr):
        best, bx, by = None, x, y
        for dy in range(-search // 2, search // 2 + 1, 2):
            for dx in range(-search, search + 1, 2):
                p = patch(f, x + dx, y + dy)
                a = p - p.mean(); b = T - T.mean()
                s = (a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6)
                if best is None or s > best: best, bx, by = s, x + dx, y + dy
        if best > 0.45:
            x, y = bx, by
            T = 0.9 * T + 0.1 * patch(f, x, y)
        pts.append((t0 + k / fps, x * scale, y * scale))
    # moving average
    n = max(1, int(smooth * fps))
    out = []
    for k in range(len(pts)):
        win = pts[max(0, k - n):k + n + 1]
        out.append((pts[k][0], sum(p[1] for p in win) / len(win), sum(p[2] for p in win) / len(win)))
    return out


def run_bytes(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode: raise SystemExit("FAILED: " + " ".join(cmd) + r.stderr.decode()[-1500:])
    return r.stdout


# ---------------------------------------------------------------- kit clips (headless Chrome, deterministic t)
KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit", "kit.html")


def _find_chrome():
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium",
              shutil.which("google-chrome") or "", shutil.which("chromium") or "", shutil.which("chromium-browser") or ""):
        if p and os.path.exists(p): return p
    return "google-chrome"


CHROME = os.environ.get("SHORTS_STUDIO_CHROME") or _find_chrome()


def kit_render(spec, out, port=9711):
    """spec: the KIT dict (dur, scene, ...). Renders 1080x1920 at FPS to out (mp4), cached by content."""
    import base64, tempfile, time, urllib.request, websocket
    if BRAND is None: use_brand()
    if "brand" not in spec: spec = dict(spec, brand=_brand.kit_brand(BRAND))
    key = json.dumps(spec, sort_keys=True) + str(os.path.getmtime(KIT))
    if os.path.exists(out) and os.path.exists(out + ".key") and open(out + ".key").read() == key: return out
    out = os.path.abspath(out); js = out + ".js"
    open(js, "w").write("window.KIT = " + json.dumps(spec) + ";")
    prof = tempfile.mkdtemp()
    p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                          "--force-device-scale-factor=1", "--window-size=1080,1920", f"--remote-debugging-port={port}",
                          "--remote-allow-origins=*", f"--user-data-dir={prof}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    enc = None
    try:
        for _ in range(150):
            try: tg = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json")); break
            except Exception: time.sleep(0.1)
        ws = websocket.create_connection(next(x for x in tg if x["type"] == "page")["webSocketDebuggerUrl"], max_size=None)
        mid = [0]
        def call(m, **pr):
            mid[0] += 1; ws.send(json.dumps({"id": mid[0], "method": m, "params": pr}))
            while True:
                r = json.loads(ws.recv())
                if r.get("id") == mid[0]:
                    if "error" in r: raise RuntimeError(r["error"])
                    return r.get("result", {})
        call("Page.enable"); call("Runtime.enable")
        call("Emulation.setDeviceMetricsOverride", width=1080, height=1920, deviceScaleFactor=1, mobile=False)
        call("Page.navigate", url=f"file://{KIT}?spec=file://{js}&t=0")
        for _ in range(1500):
            r = call("Runtime.evaluate", expression="document.body && document.body.dataset.ready === 'true'", returnByValue=True)
            if r.get("result", {}).get("value"): break
            tt = call("Runtime.evaluate", expression="document.title", returnByValue=True)
            if "ERROR" in str(tt.get("result", {}).get("value", "")): raise RuntimeError(tt["result"]["value"])
            time.sleep(0.01)
        else:
            raise RuntimeError("kit page never became ready: " + str(call("Runtime.evaluate", expression="document.title", returnByValue=True)))
        n = int(round(spec["dur"] * FPS))
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                                *FFX, out], stdin=subprocess.PIPE)
        for f in range(n):
            r = call("Runtime.evaluate", expression=f"window.__twiaFrame({f / FPS:.5f})", returnByValue=True)
            if r.get("exceptionDetails"): raise RuntimeError(json.dumps(r["exceptionDetails"])[:600])
            s = call("Page.captureScreenshot", format="jpeg", quality=93, captureBeyondViewport=False)
            enc.stdin.write(base64.b64decode(s["data"]))
        enc.stdin.close(); enc.wait()
        ws.close()
    finally:
        p.terminate()
    open(out + ".key", "w").write(key)
    return out


def kit_batch(jobs, workers=6):
    """jobs: [(spec, out)] rendered in parallel, each on its own Chrome port."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(workers) as ex:
        base = 9711 + (os.getpid() % 150) * 12          # unique ports per process: two Shorts rendering at once must never share a Chrome
        futs = [ex.submit(kit_render, s, o, base + k % 12) for k, (s, o) in enumerate(jobs)]
        return [f.result() for f in futs]


def webshot(url, out, width=540, height=960, scale=2, full=True, wait=4.0, port=9790, js=None):
    """Re-render a live page in headless Chrome (desktop UA), full page at 2x. Returns (w, h) in pixels."""
    import base64, tempfile, time, urllib.request, websocket
    prof = tempfile.mkdtemp()
    p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--remote-debugging-port={port}",
                          "--remote-allow-origins=*", f"--user-data-dir={prof}", f"--window-size={width},{height}", "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(150):
            try: tg = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json")); break
            except Exception: time.sleep(0.1)
        ws = websocket.create_connection(next(x for x in tg if x["type"] == "page")["webSocketDebuggerUrl"], max_size=None)
        mid = [0]
        def call(m, **pr):
            mid[0] += 1; ws.send(json.dumps({"id": mid[0], "method": m, "params": pr}))
            while True:
                r = json.loads(ws.recv())
                if r.get("id") == mid[0]: return r.get("result", {})
        call("Page.enable"); call("Runtime.enable")
        call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=scale, mobile=False)
        call("Page.navigate", url=url); time.sleep(wait)
        if js: call("Runtime.evaluate", expression=js); time.sleep(1.0)
        # walk the page so lazy images load, then back to the top
        hh = call("Runtime.evaluate", expression="document.documentElement.scrollHeight", returnByValue=True)["result"]["value"]
        for y in range(0, min(hh, 9000), 700):
            call("Runtime.evaluate", expression=f"window.scrollTo(0,{y})"); time.sleep(0.15)
        call("Runtime.evaluate", expression="window.scrollTo(0,0)"); time.sleep(1.0)
        hh = min(call("Runtime.evaluate", expression="document.documentElement.scrollHeight", returnByValue=True)["result"]["value"], 9000)
        if full:
            call("Emulation.setDeviceMetricsOverride", width=width, height=hh, deviceScaleFactor=scale, mobile=False); time.sleep(1.0)
        s = call("Page.captureScreenshot", format="png", captureBeyondViewport=True)
        open(out, "wb").write(base64.b64decode(s["data"]))
        ws.close()
    finally:
        p.terminate()
    return width * scale, (hh if full else height) * scale


REVIEW = os.path.abspath("graphics-review")      # next to the Shorts, in the video folder


def kit_review(mp4, name=None):
    """1 fps contact sheet + 3 key frames (25 / 60 / 95 %) side by side, into graphics-review/."""
    os.makedirs(REVIEW, exist_ok=True)
    name = name or os.path.splitext(os.path.basename(mp4))[0]
    d = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4]).stdout)
    n = max(1, int(d))
    run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", f"fps=1,scale=270:480,tile={min(n, 8)}x{(n + 7) // 8}", "-frames:v", "1",
         os.path.join(REVIEW, f"{name}_1fps.jpg")])
    fr = []
    for k, p in enumerate((0.25, 0.6, 0.95)):
        f = os.path.join(REVIEW, f".{name}_{k}.png")
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{d * p:.3f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=540:960", f]); fr.append(f)
    run(["ffmpeg", "-v", "error", "-y", *sum([["-i", f] for f in fr], []), "-filter_complex", "hstack=3", os.path.join(REVIEW, f"{name}_keys.jpg")])
    for f in fr: os.remove(f)
    return os.path.join(REVIEW, f"{name}_keys.jpg")


def compose_split(top, bot, out, divider=None):
    """Top half of `top` over top half of `bot` (each 1080x960), a 4 px divider on the seam."""
    if divider is None:
        if BRAND is None: use_brand()
        divider = BRAND["colors"]["deep"].lstrip("#")
    run(["ffmpeg", "-v", "error", "-y", "-i", top, "-i", bot, "-filter_complex",
         f"[0:v]crop={W}:960:0:0[t];[1:v]crop={W}:960:0:0[b];[t][b]vstack,drawbox=x=0:y=958:w={W}:h=4:color=0x{divider}:t=fill[v]",
         "-map", "[v]", *FFX, out])
    return out


# ---------------------------------------------------------------- caption de-duplication and layout gate
def kit_texts(spec):
    """Every string a kit scene puts on screen."""
    out = []
    def walk(v, k=None):
        if isinstance(v, dict):
            for kk, vv in v.items(): walk(vv, kk)
        elif isinstance(v, list):
            for vv in v: walk(vv, k)
        elif isinstance(v, str) and k in (None, "value", "label", "text", "title", "sub", "date", "name") and not v.endswith((".png", ".svg", ".jpg")):
            out.append(v)
    walk({k: v for k, v in spec.items() if k in ("lines", "a", "b", "label", "text", "title", "sub", "items", "nodes", "name")})
    if spec.get("scene") == "counter":
        out.append(f"{spec.get('prefix', '')}{spec['value']:,}{spec.get('suffix', '')}")
    return out


def norm_words(s): return [w for w in re.sub(r"[^a-z0-9 ]", " ", s.lower()).split() if w]


def dupe(caption, texts, frac=0.6):
    """True when most of the caption's words already sit on screen in a card."""
    stop = {"the", "a", "an", "and", "of", "to", "it", "is", "in", "on", "that", "this", "i", "you", "he", "his", "was", "for", "with", "be", "or", "but"}
    cw = [w for w in norm_words(caption) if w not in stop]
    pool = set(w for t in texts for w in norm_words(t))
    return bool(cw) and sum(w in pool for w in cw) / len(cw) >= frac


def layout_check(spec, band=None, port=9888, margin=60, mp4=None):
    """Render the kit scene in Chrome and read back every text and card box (window.__boxes) at rest on each
    keyframe. Returns problems: boxes outside the safe area, and text wider than the card it sits in."""
    if BRAND is None: use_brand()
    if "brand" not in spec: spec = dict(spec, brand=_brand.kit_brand(BRAND))
    import base64, tempfile, time, urllib.request, websocket
    times = set()
    def walk(v, k=None):
        if isinstance(v, dict):
            for kk, vv in v.items(): walk(vv, kk)
        elif isinstance(v, list):
            for vv in v: walk(vv, k)
        elif isinstance(v, (int, float)) and k in ("t", "t0", "t1", "labelT"): times.add(float(v))
    walk(spec)
    D = spec["dur"]
    pts = sorted({min(D - 0.6, t + 0.8) for t in times if t < D} | {D * 0.95 - 0.5, D * 0.6})
    pts = [p for p in pts if p > 0]
    js = tempfile.mktemp(suffix=".js"); open(js, "w").write("window.KIT = " + json.dumps(spec) + ";")
    prof = tempfile.mkdtemp()
    p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                          "--force-device-scale-factor=1", "--window-size=1080,1920", f"--remote-debugging-port={port}",
                          "--remote-allow-origins=*", f"--user-data-dir={prof}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    probs = []
    try:
        for _ in range(150):
            try: tg = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json")); break
            except Exception: time.sleep(0.1)
        ws = websocket.create_connection(next(x for x in tg if x["type"] == "page")["webSocketDebuggerUrl"], max_size=None)
        mid = [0]
        def call(m, **pr):
            mid[0] += 1; ws.send(json.dumps({"id": mid[0], "method": m, "params": pr}))
            while True:
                r = json.loads(ws.recv())
                if r.get("id") == mid[0]: return r.get("result", {})
        call("Page.enable"); call("Runtime.enable")
        call("Emulation.setDeviceMetricsOverride", width=1080, height=1920, deviceScaleFactor=1, mobile=False)
        call("Page.navigate", url=f"file://{KIT}?spec=file://{js}&t=0")
        for _ in range(1500):
            r = call("Runtime.evaluate", expression="document.body && document.body.dataset.ready === 'true'", returnByValue=True)
            if r.get("result", {}).get("value"): break
            time.sleep(0.01)
        y0, y1 = (band + margin, band + 960 - margin) if band is not None else (margin, 1920 - margin)
        for t in pts:
            call("Runtime.evaluate", expression=f"window.__twiaFrame({t:.4f})")
            boxes = call("Runtime.evaluate", expression="JSON.stringify(window.__boxes)", returnByValue=True)["result"]["value"]
            boxes = [b for b in json.loads(boxes) if b["alpha"] > 0.9 and b["w"] > 5 and b["h"] > 5]
            cards = [b for b in boxes if b["kind"] == "card"]
            for b in boxes:
                if b["kind"] == "card" and spec.get("scene") == "ui" and band is None: pass
                if b["x"] < margin - 1 or b["x"] + b["w"] > 1080 - margin + 1 or b["y"] < y0 - 1 or b["y"] + b["h"] > y1 + 1:
                    if b.get("s", "").startswith("00:00") or b.get("s") in (spec.get("hud"), spec.get("credit"), spec["brand"].get("hud")):
                        continue          # HUD labels sit outside the panel band by design
                    probs.append(f"t={t:.2f} {b['kind']} {b.get('s', '')!r} at x={b['x']:.0f}..{b['x'] + b['w']:.0f}, y={b['y']:.0f}..{b['y'] + b['h']:.0f} outside safe area")
                if b["kind"] == "text":
                    cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
                    host = [c for c in cards if c["x"] <= cx <= c["x"] + c["w"] and c["y"] <= cy <= c["y"] + c["h"]]
                    if host:
                        c = min(host, key=lambda c: c["w"] * c["h"])
                        if b["x"] < c["x"] + 8 or b["x"] + b["w"] > c["x"] + c["w"] - 8:
                            probs.append(f"t={t:.2f} text {b.get('s', '')!r} overflows its card")
        if mp4 and os.path.exists(mp4):
            # the rendered clip must be this spec: compare a fresh frame with the clip's frame at the same time
            import base64, io
            from PIL import Image, ImageChops, ImageStat
            tt = round(D * 0.6 * FPS) / FPS
            call("Runtime.evaluate", expression=f"window.__twiaFrame({tt:.4f})")
            shot = call("Page.captureScreenshot", format="png", captureBeyondViewport=False)
            a_ = Image.open(io.BytesIO(base64.b64decode(shot["data"]))).convert("L").resize((108, 192))
            fr = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{tt:.4f}", "-i", mp4, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                                capture_output=True).stdout
            b_ = Image.open(io.BytesIO(fr)).convert("L").resize((108, 192))
            diff = ImageStat.Stat(ImageChops.difference(a_, b_)).mean[0]
            if diff > 12: probs.append(f"rendered clip does not match its spec (mean pixel difference {diff:.0f}); re-render it")
        ws.close()
    finally:
        p.terminate()
    return sorted(set(probs))


CARDTX = []     # (t0, t1, [strings]) for every card on screen, filled by the Short scripts' kit() helpers


def ass_overflow(ass, margin=60):
    """Every positioned ASS event whose rendered width would leave the safe area (PIL metrics, same font)."""
    from PIL import ImageFont
    styles = {}
    for line in ass.splitlines():
        if line.startswith("Style:"):
            f = line[6:].split(","); styles[f[0].strip()] = (float(f[2]), float(f[16]), int(f[15]))
    probs = []
    for line in ass.splitlines():
        if not line.startswith("Dialogue:"): continue
        parts = line.split(",", 9); st = parts[3]; txt = parts[9]
        if st not in ("Cap", "Box", "Key", "Pop", "Cred"): continue
        m = re.search(r"\\pos\(([\d.]+),([\d.]+)\)", txt)
        if not m: continue
        x = float(m.group(1)); an1 = "\\an1" in txt; an3 = "\\an3" in txt
        plain = re.sub(r"\{[^}]*\}", "", txt)
        size, bord, bs = styles[st]
        mf = re.search(r"\\fs(\d+)", txt)
        if mf: size = float(mf.group(1))
        font = ImageFont.truetype(TEXT_FONT["file"] if st == "Cred" else DISPLAY_FONT["file"], int(size))
        w = font.getlength(plain) + 2 * bord
        x0 = x if an1 else x - w if an3 else x - w / 2
        if x0 < margin - 30 or x0 + w > 1080 - margin + 30:
            probs.append(f"{st} {plain!r} is {w:.0f} px wide at x={x0:.0f}, outside the safe area")
    return probs


def snap_shots(shots, cuts):
    """A picture cut within 0.3 s of an audio join snaps onto the join: never two cuts in a row."""
    for k in range(1, len(shots)):
        t = shots[k]["t0"]
        near = [c for c in cuts if 0 < abs(c - t) <= 0.3 and shots[k - 1]["t0"] + 0.5 < c < shots[k]["t1"] - 0.5]
        if near and abs(shots[k - 1]["t1"] - t) < 1e-6:
            c = min(near, key=lambda c: abs(c - t))
            if c - shots[k - 1]["t0"] >= 1.0 and shots[k]["t1"] - c >= 1.0:      # never squeeze a shot under 1 s
                shots[k - 1]["t1"] = shots[k]["t0"] = c
    return shots


def pan_cuts(shots, limit=0.02):
    """A crop move faster than `limit` of the frame per frame becomes a deliberate hard cut at its end key.
    Returns the cut times (the QA gate treats them as intended cuts)."""
    out = []
    for s in shots:
        if s["kind"] != "scr" or not s.get("keys"): continue
        k = s["keys"]
        for i in range(len(k) - 1):
            (t0, r0), (t1, r1) = k[i], k[i + 1]
            dt = t1 - t0
            if dt <= 1e-3: continue
            wa = (r0[2] + r1[2]) / 2
            move = max(abs(r1[0] - r0[0]) / wa, abs(r1[1] - r0[1]) / wa, abs(r1[2] - r0[2]) / wa)
            if 1.5 * move / (dt * 30) > limit:                 # smoothstep peaks at 1.5x the mean speed
                k[i] = (t1 - 0.0005, r0); out.append(round(t1, 3))
        s["keys"] = k
    return out
