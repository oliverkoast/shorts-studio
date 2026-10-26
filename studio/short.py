"""The API a Short's spec.py uses. One Builder per Short:

    from studio.short import Builder
    b = Builder(src="talk.mp4", words="talk.words.json", rows=ROWS)          # cuts the audio on real words
    T = b.T                                                                  # T(i): when word i is said in the Short
    b.face(0, T(12), track)                                                  # the speaker, 9:16, face-tracked
    b.kit(T(12), T(20), "price", scene="counter", value=18.1, suffix="M")    # a motion graphic from the kit
    b.footage(T(20), T(25), "~/Movies/b-roll/launch.mp4", at=3.0, credit="Video: SpaceX")
    b.captions()                                                             # cards of 3 to 5 words, deduped against graphics
    b.key(T(30), b.total, "FULL EPISODE ON YOUTUBE")
    short = b.done()
    render(short, "out/My Short.mp4")

Every time is in seconds of the finished Short. Graphics and footage are cued by word with T(i)."""
import json, math, os
from . import lib
from .lib import (FPS, ev, at, caption_cards, clean, plan, render_audio, loudnorm, render_shots, finish, kit_batch, track_face,
                  src_to_out, out_to_src, compose_split, kit_texts, dupe, CARDTX, run)

POP = r"{\fscx70\fscy70\t(0,140,\fscx104\fscy104)\t(140,220,\fscx100\fscy100)}"


class Builder:
    def __init__(self, src, words, rows, brand=None, folder=".", work=None, maxgap=0.30, pad=0.15, tail=0.06, offset=0.0,
                 end_hold=0.0, layout="full", platform="youtube"):
        """src: the source video (its audio is the voice). words: the word-timing JSON from studio.transcribe.
        rows: [{"keep": [(i0, i1), ...], "text": "the exact words, one token per kept word"}], in source order.
        layout: "full" (one picture) or "split" (top panel over the speaker, captions on the divider).
        platform: "youtube" (YouTube Shorts, Instagram Reels) or "tiktok" (captions sit higher, clear of TikTok's
        caption and button overlay). See docs/platforms.md for the safe zones."""
        lib.use_brand(brand, folder)
        self.brand = lib.BRAND
        self.src = os.path.abspath(os.path.expanduser(src))
        self.words = json.load(open(words)) if isinstance(words, str) else words
        if offset:
            self.words = [dict(w=x["w"], t0=x["t0"] - offset, t1=x["t1"] - offset) for x in self.words]
        self.rows = rows
        self.res, self.wm, self.cap, self.total = plan(self.words, rows, maxgap=maxgap, pad=pad, tail=tail, audio=self.src)
        self.total_v = self.total + end_hold
        self.work = os.path.abspath(work or "work")
        os.makedirs(os.path.join(self.work, "kit"), exist_ok=True)
        self.layout = layout
        self.platform = platform
        self.shots, self.top, self.bot, self.kits, self.cred, self.extra = [], [], [], [], [], []
        self.ass = lib.ass_header()
        self._z = 0
        CARDTX.clear()

    # ---- time -------------------------------------------------------------------------------------
    def T(self, i):
        """When word i starts in the finished Short."""
        return self.wm[i][0]

    def E(self, i):
        return self.wm[i][1]

    def at_source(self, s):
        """Where source second s lands in the Short (None if it was cut)."""
        return src_to_out(self.res, s)

    def _put(self, shot, panel):
        (self.top if panel == "top" else self.bot if panel == "bottom" else self.shots).append(shot)

    # ---- pictures -----------------------------------------------------------------------------------
    def face(self, t0, t1, track, zoom=1.0, dy=40, panel=None):
        """The speaker as a 9:16 crop that follows the face (track from studio.lib.track_face)."""
        self._put(dict(t0=t0, t1=t1, kind="face916", track=track, zoom=zoom, dy=dy), panel)

    def punch(self, t0, t1, track, dy=70, every=(1.2, 2.0), zooms=(1.0, 1.2)):
        """Face shots that alternate zoom on word starts every 1.2 to 2 s (the quick-clip look)."""
        starts = sorted(v[0] for v in self.wm.values())
        t = t0
        while t < t1 - 0.05:
            nxt = [x for x in starts if t + every[0] <= x <= t + every[1] and x < t1 - 0.6]
            e = nxt[0] if nxt else t1
            self.shots.append(dict(t0=t, t1=e, kind="face916", track=track, zoom=zooms[self._z % 2], dy=dy)); self._z += 1; t = e

    def frame(self, t0, t1, crop, place=(0, 0, 1080), at=None, blur=False, hold=False, bubble=None, panel=None, src=None):
        """A crop of a video (the source by default), placed on the brand ground or over its own blur.
        crop=(x, y, w, h) in source pixels; place=(x, y, width) in the 1080x1920 frame; at: source second to start
        (default: in sync with the voice). bubble=(x, y, size): a round face bubble cropped from the source."""
        sh = dict(t0=t0, t1=t1, kind="fit", crop=crop, place=place, blurbg=blur, hold=hold)
        if src: sh["src"] = os.path.abspath(os.path.expanduser(src))
        if at is not None: sh["free"] = at
        if bubble: sh.update(bubble=True, bubble_crop=bubble)
        self._put(sh, panel)

    def footage(self, t0, t1, src, at, credit=None, crop=None, place=None, panel=None, max_clip=4.5):
        """B-roll from a file, over its own blur, split into clips under max_clip seconds. Muted."""
        src = os.path.abspath(os.path.expanduser(src))
        if crop is None:
            w, h = probe_size(src)
            crop = (0, 0, w, h)
        if place is None:
            place = (0, 0, 1080) if panel == "top" else (0, 420, 1080)
        n = max(1, math.ceil((t1 - t0) / max_clip))
        for k in range(n):
            a, b = t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n
            self._put(dict(t0=a, t1=b, kind="fit", src=src, free=at + 7.0 * k, crop=crop, place=place, blurbg=True), panel)
        if credit: self.credit(t0, t1, credit, panel)

    def screen(self, t0, t1, keys, src=None, size=None, ui_bg="FFFFFF", at=None, bubble=None, patch=()):
        """A screen recording in a rounded window with eased crops: keys=[(t, (x, y, w)), ...] in source pixels.
        bubble=(x, y, size) crops the presenter from the camera file set with camera()."""
        src = os.path.abspath(os.path.expanduser(src or self.src))
        self.look = getattr(self, "look", {})
        self.look.update(scr=src, scr_size=size or probe_size(src), ui_bg=ui_bg)
        sh = dict(t0=t0, t1=t1, kind="scr", keys=keys, patch=list(patch))
        if at is not None: sh["free"] = at
        if bubble: sh["bubble"] = True; self.look["bubble"] = bubble
        self.shots.append(sh)

    def camera(self, cam, offset=0.0, window_x=None, window_w=None):
        """For screen demos with a separate camera file: offset = camera time minus screen time."""
        self.look = getattr(self, "look", {})
        self.look.update(cam=os.path.abspath(os.path.expanduser(cam)), cam_off=offset)
        if window_x is not None: self.look["cam_win"] = (window_x, window_w)

    def cam_window(self, t0, t1):
        self.shots.append(dict(t0=t0, t1=t1, kind="cam"))

    def kit(self, start, end, name, panel=None, band=None, **k):
        """A motion graphic from the kit, rendered for exactly this slot (start to end, seconds of the Short).
        Times inside k (t, t0, t1, ...) are seconds from the graphic's own start. See skills/motion for scenes."""
        out = os.path.join(self.work, "kit", name + ".mp4")
        k.setdefault("hud", "")
        self.kits.append((dict(dur=round(end - start + 0.6, 3), **k), out))
        CARDTX.append((start, end, kit_texts(k)))
        sh = dict(t0=start, t1=end, kind="clip", src=out, free=0.0)
        if panel == "top": sh["band"] = 330 if band is None else band
        self._put(sh, panel)

    # ---- text ---------------------------------------------------------------------------------------
    def credit(self, t0, t1, text, panel=None):
        self.cred.append((t0, t1, text, panel))

    def key(self, t0, t1, text, y=1300, style="Box"):
        """A card over the picture (Box: small, Key: big)."""
        self.ass += ev(8, t0, t1, style, r"{\pos(540,%d)}" % y + POP + text)

    def captions(self, style="cards", keywords=(), y=None):
        """cards: one line, 3 to 5 words, hard swaps. pop: 1 to 2 words, keywords in the accent colour.
        A caption is skipped while a graphic shows the same words."""
        y = y or (960 if self.layout == "split" else 1300 if self.platform == "tiktok" else 1500)
        if style == "cards":
            for t0, t1, c in caption_cards(self.cap, self.wm, end=self.total):
                txt = " ".join(clean(w) for _, w in c if w != "~")
                if any(a < (t0 + t1) / 2 < b and dupe(txt, tx) for a, b, tx in CARDTX): continue
                self.ass += ev(10, t0, t1, "Cap", r"{\pos(540,%d)}" % y + txt)
        else:
            if "Style: Pop" not in self.ass:
                self.ass = self.ass.replace("Style: Tag,", "Style: Pop,%s,96,%s,%s,%s,&H96000000,-1,0,0,0,100,100,0,0,1,8,3,5,40,40,0,1\nStyle: Tag,"
                                            % (lib.DISPLAY_FONT["family"], lib.BONE, lib.BONE, lib.INK))
            kw = {w.upper() for w in keywords}
            seq = [(i, clean(w)) for i, w in self.cap if w != "~" and i in self.wm]
            k = 0
            while k < len(seq):
                i, w = seq[k]
                grp = [(i, w)]
                if w not in kw and k + 1 < len(seq) and seq[k + 1][1] not in kw and len(w) + len(seq[k + 1][1]) < 13 \
                        and self.wm[seq[k + 1][0]][0] - self.wm[i][1] < 0.12:
                    grp.append(seq[k + 1])
                k += len(grp)
                t0 = self.wm[grp[0][0]][0]
                t1 = self.wm[seq[k][0]][0] if k < len(seq) else self.total
                if any(a < (t0 + t1) / 2 < b and dupe(" ".join(x for _, x in grp), tx) for a, b, tx in CARDTX): continue
                txt = " ".join((r"{\c%s}%s{\c%s}" % (lib.SAND, x, lib.BONE)) if x in kw else x for _, x in grp)
                self.ass += ev(10, t0, t1, "Pop", r"{\pos(540,%d)\fscx80\fscy80\t(0,90,\fscx106\fscy106)\t(90,150,\fscx100\fscy100)}" % (y - 20) + txt)

    def endcard(self, seconds=1.8, title=None, sub=None):
        """Hold a branded end card after the last word (adds to the Short's length)."""
        e = self.brand.get("endcard", {})
        t0 = self.total_v
        self.total_v += seconds
        self.kit(t0, self.total_v, "endcard", scene="logo", ground="bronze", metal=bool(self.brand.get("texture")),
                 logo=self.brand.get("logo"), title=title or e.get("title", ""), sub=sub or e.get("sub", ""), t0=0.0)

    def done(self):
        for t0, t1, text, panel in self.cred:
            if self.layout == "split":
                y = 930 if panel == "top" else 1900
                self.ass += ev(9, t0, t1, "Cred", r"{\an1\pos(30,%d)}" % y + text)
            else:
                self.ass += ev(9, t0, t1, "Cred", r"{\pos(540,1610)}" + text)
        look = dict(cam=self.src, cam_off=0.0)
        look.update(getattr(self, "look", {}))
        return dict(layout=self.layout, shots=self.shots, top=self.top, bot=self.bot, kits=self.kits, res=self.res, wm=self.wm,
                    total=self.total, total_v=self.total_v, ass=self.ass, look=look, src=self.src, rows=self.rows, work=self.work)


def probe_size(src):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", src])
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def render(short, out_mp4, review_dir=None):
    """Graphics, then audio (two-pass loudness to -14 LUFS), then pictures, then captions burned in.
    Writes the master and a phone review copy (720p, under 30 MB) in review/."""
    w = short["work"]
    kit_batch(short["kits"], 6)
    raw = render_audio(short["res"], short["src"], os.path.join(w, "voice.wav"))
    if short["total_v"] > short["total"] + 0.01:
        padded = os.path.join(w, "voice_pad.wav")
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", f"apad=pad_dur={short['total_v'] - short['total']:.3f}", padded]); raw = padded
    aud = os.path.join(w, "audio.wav"); loudnorm(raw, aud)
    res = short["res"]
    if short["total_v"] > short["total"]:
        res = res + [(res[-1][1], res[-1][1] + short["total_v"] - short["total"], short["total"])]
    if short["layout"] == "split":
        tv = render_shots(dict(shots=short["top"], look=short["look"]), res, short["total_v"], os.path.join(w, "top"))
        bv = render_shots(dict(shots=short["bot"], look=short["look"]), res, short["total_v"], os.path.join(w, "bot"))
        vid = compose_split(tv, bv, os.path.join(w, "video.mp4"))
    else:
        vid = render_shots(dict(shots=short["shots"], look=short["look"]), res, short["total_v"], w)
    ass = os.path.join(w, "short.ass"); open(ass, "w").write(short["ass"])
    out_mp4 = os.path.abspath(out_mp4)
    review_dir = review_dir or os.path.join(os.path.dirname(out_mp4), "review")
    os.makedirs(review_dir, exist_ok=True)
    review = os.path.join(review_dir, os.path.splitext(os.path.basename(out_mp4))[0] + " (phone).mp4")
    finish(vid, aud, ass, out_mp4, review)
    return out_mp4, review


def find(words, phrase, after=0.0, before=None):
    """(first, last) word indices of `phrase` in a word list, matched loosely (the word-timing model misspells:
    'clowd code'), searching from source second `after`. Raises if nothing scores well."""
    import difflib, re
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    want = [norm(w) for w in phrase.split() if norm(w)]
    best = (0.0, None)
    idx = [i for i, w in enumerate(words) if w["t0"] >= after and (before is None or w["t0"] <= before)]
    for k in range(len(idx) - len(want) + 1):
        i = idx[k]
        got = [norm(words[i + j]["w"]) for j in range(len(want))]
        sc = sum(difflib.SequenceMatcher(None, a, b).ratio() for a, b in zip(want, got)) / len(want)
        if sc > best[0]: best = (sc, i)
    if best[0] < 0.7: raise SystemExit(f"phrase not found (best match {best[0]:.2f}): {phrase!r}")
    return best[1], best[1] + len(want) - 1


def row(words, phrase, text=None, after=0.0, before=None, drop=()):
    """A ROWS entry for a phrase: keeps its words, minus any `drop` phrases inside it (restarts, fillers).
    text defaults to the phrase itself."""
    i0, i1 = find(words, phrase, after, before)
    out = [(i0, i1)]
    for d in drop:
        d0, d1 = find(words, d, words[i0]["t0"] - 0.01, words[i1]["t1"])
        new = []
        for a, b in out:
            if d0 > b or d1 < a: new.append((a, b)); continue
            if a < d0: new.append((a, d0 - 1))
            if d1 < b: new.append((d1 + 1, b))
        out = new
    kept = sum(b - a + 1 for a, b in out)
    text = text or " ".join(phrase.split())
    if len(text.split()) != kept:
        raise SystemExit(f"row text has {len(text.split())} words but {kept} are kept: {text!r}")
    return {"keep": out, "text": text}
