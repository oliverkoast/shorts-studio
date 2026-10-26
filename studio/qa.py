"""QA gate for every Short. Run after a render; returns (ok, report lines).

  (a) frame count and PTS continuity: constant 30 fps, no gaps, no duplicate timestamps
  (b) mpdecimate + freezedetect: duplicated or frozen frames outside intended holds
  (c) frame-difference spikes (scene score) where no cut is intended: crop or pan jumps, graphic pops
  (d) blackdetect and a white-flash check
  (e) audio: clicks within 50 ms of a join, level jumps over 3 dB between adjacent segments, loudness and true peak
  (f) crop and pan curves: no step over 2% of the frame between consecutive frames unless it is a cut
"""
import json, math, re, subprocess
import numpy as np

FPS = 30


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ease_val(keys, t):
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t < t1:
            if t1 - t0 < 1e-3: return v1
            u = min(max((t - t0) / (t1 - t0), 0), 1); return v0 + (v1 - v0) * u * u * (3 - 2 * u)
    return keys[-1][1]


def gate(mp4, shots, res, total, label, holds=(), extra_cuts=(), wout=(), expected=None):
    rep, fail = [], False
    def add(ok, line):
        nonlocal fail
        rep.append(("PASS " if ok else "FAIL ") + line); fail |= not ok
    # intended cuts: shot boundaries, audio joins inside sync shots, extra (e.g. kit-internal scene changes)
    joins = [o for a, b, o in res][1:]
    cuts = sorted(set([round(s["t0"], 3) for s in shots][1:] + [round(j, 3) for j in joins] + list(extra_cuts)))
    # ---- (a) PTS -----------------------------------------------------------------------------------
    r = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time", "-of", "csv=p=0", mp4])
    pts = np.array([float(x.strip(",")) for x in r.stdout.split() if x.strip(",").strip()])
    d = np.diff(pts)
    n_expect = int(round(float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4]).stdout) * FPS))
    gaps = int(np.sum(np.abs(d - 1 / FPS) > 0.25 / FPS))
    add(gaps == 0 and abs(len(pts) - n_expect) <= 2,
        f"(a) frames {len(pts)} (expected ~{n_expect}), PTS steps off 1/30 s: {gaps}, duplicate timestamps: {int(np.sum(d <= 0))}")
    # ---- (b) frozen / duplicated frames outside holds -------------------------------------------------
    r = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-vf", "freezedetect=n=0.0008:d=1.2", "-an", "-f", "null", "-"])
    fr = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", r.stderr)]
    fe = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", r.stderr)]
    bad = [(a, b) for a, b in zip(fr, fe + [total]) if not any(h0 - 0.2 <= a and b <= h1 + 0.2 for h0, h1 in holds)]
    add(not bad, f"(b) freezes over 1.2 s outside intended holds: {[(round(a, 2), round(b, 2)) for a, b in bad] or 'none'}")
    r = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-vf", "mpdecimate=hi=64*2:lo=64*0.5:frac=0.5,showinfo", "-an", "-f", "null", "-"])
    kept = len(re.findall(r"pts_time:", r.stderr))
    rep.append(f"INFO (b) mpdecimate keeps {kept} of {len(pts)} frames (static UI and held graphics account for the rest)")
    # ---- (c) difference spikes at no intended cut ----------------------------------------------------
    r = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-vf", "scale=270:480,select='gte(scene,0)',metadata=print:file=-", "-an", "-f", "null", "-"])
    sc = []
    t = None
    for line in r.stdout.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m: t = float(m.group(1))
        m = re.search(r"lavfi.scene_score=([\d.]+)", line)
        if m and t is not None: sc.append((t, float(m.group(1))))
    broll = [(x["t0"], x["t1"]) for x in shots if x["kind"] == "clip" or (x["kind"] == "fit" and x.get("src"))]
    spikes = [(t, s) for t, s in sc if s > 0.22 and not any(abs(t - c) <= 2.0 / FPS for c in cuts)]
    inb = [(t, s) for t, s in spikes if any(a + 1.5 / FPS < t < b - 1.5 / FPS for a, b in broll)]
    spikes = [x for x in spikes if x not in inb]
    if inb: rep.append(f"INFO (c) {len(inb)} spikes fall inside official footage or kit animations (their own edits and slam-ins): {[round(t, 2) for t, s in inb]}")
    add(not spikes, f"(c) frame-difference spikes (scene > 0.22) away from intended cuts: {[(round(t, 2), round(s, 2)) for t, s in spikes] or 'none'}")
    # ---- (d) black and white flashes ------------------------------------------------------------------
    r = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-vf", "blackdetect=d=0.03:pix_th=0.06", "-an", "-f", "null", "-"])
    blk = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)
    r = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-vf", "scale=135:240,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-", "-an", "-f", "null", "-"])
    ys = [float(x) for x in re.findall(r"YAVG=([\d.]+)", r.stdout)]
    flash = [i / FPS for i in range(1, len(ys) - 1) if ys[i] > 235 and ys[i - 1] < 200 and ys[i + 1] < 200]
    add(not blk and not flash, f"(d) black frames: {blk or 'none'}; single-frame white flashes: {flash or 'none'}")
    # ---- (e) audio -------------------------------------------------------------------------------------
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-ac", "1", "-ar", "48000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    sr = 48000
    clicks, jumps = [], []
    for j in joins:
        c = int(j * sr)
        seg = x[max(0, c - int(0.05 * sr)): c + int(0.05 * sr)]
        if len(seg) < 100: continue
        # a click is a discontinuity AT the join (within 2 ms), much sharper than anything else around it;
        # a word onset a few tens of ms later is speech, not a click
        dd = np.abs(np.diff(seg)); mid_ = len(dd) // 2; w2 = int(0.002 * sr)
        at = dd[mid_ - w2: mid_ + w2].max(); ref = np.percentile(np.r_[dd[:mid_ - w2], dd[mid_ + w2:]], 99) + 1e-5
        if at > 0.02 and at > 2.0 * ref: clicks.append((round(j, 2), round(float(at), 3)))
    for (a0, b0, o0), (a1, b1, o1) in zip(res, res[1:]):
        def rms_db(t0, t1):
            s = x[int(t0 * sr):int(t1 * sr)]
            if len(s) < 100: return None
            # voiced level: the loudest 40% of 20 ms frames, so pauses do not count
            fr_ = s[:len(s) // 960 * 960].reshape(-1, 960)
            e = np.sqrt((fr_ ** 2).mean(1) + 1e-12); e = np.sort(e)[int(len(e) * 0.6):]
            return 20 * np.log10(e.mean() + 1e-9)
        A, B = rms_db(o0, o1), rms_db(o1, o1 + (b1 - a1))
        if A is not None and B is not None and abs(A - B) > 3 and (o1 - o0) > 0.6 and (b1 - a1) > 0.6:
            jumps.append((round(o1, 2), round(A - B, 1)))
    r = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-af", "ebur128=peak=true", "-f", "null", "-"])
    I = float(re.findall(r"I:\s+([-\d.]+) LUFS", r.stderr)[-1]); TP = float(re.findall(r"Peak:\s+([-\d.]+) dBFS", r.stderr)[-1])
    add(not clicks, f"(e) clicks within 50 ms of a join: {clicks or 'none'}")
    add(not jumps, f"(e) voiced-level jumps over 3 dB between adjacent segments: {jumps or 'none'}")
    add(abs(I + 14) <= 0.6 and TP <= -1.0, f"(e) loudness {I} LUFS (spec -14 +/- 0.6), true peak {TP} dBFS (spec <= -1.0)")
    # ---- (k) non-speech bursts between words ---------------------------------------------------------
    # Every gap between two spoken words should be quiet. A burst over -40 dBFS lasting under 300 ms in a gap
    # (keeping 100 ms after a word and 120 ms before the next clear of CTC timing error) is a fragment of a
    # dropped word, a breath or a mouth sound that survived a cut: the "noise after at the moment" kind.
    bursts = []
    if wout:
        f10 = x[:len(x) // 480 * 480].reshape(-1, 480)
        e10 = 20 * np.log10(np.sqrt((f10 ** 2).mean(1)) + 1e-9)
        ws_ = sorted(wout)
        for (a0, a1), (b0, b1) in zip(ws_, ws_[1:]):
            if not any(a1 - 0.05 <= j <= b0 + 0.05 for j in joins): continue      # only gaps that contain one of our cuts
            # an island: quiet (< -45 dBFS for 30 ms) after the word, then a short loud run, then quiet again before
            # the next word. A word's own tail (CTC ends early) is never separated from it by a quiet dip.
            g0, g1 = a1, b0
            seg = e10[int(g0 * 100):int(g1 * 100) + 1]
            if len(seg) < 8: continue
            q = seg < -45
            i = 0
            while i < len(seg) and not (q[i:i + 3].all() if i + 3 <= len(seg) else False): i += 1
            j = len(seg) - 1
            while j > i and not (q[j - 2:j + 1].all() if j >= 2 else False): j -= 1
            inner = seg[i + 3:j - 2] if j - 2 > i + 3 else seg[0:0]
            loud = np.where(inner > -40)[0]
            if len(loud) and (loud[-1] - loud[0] + 1) / 100 < 0.30:
                bursts.append((round(g0 + (i + 3 + loud[0]) / 100, 2), round(float(inner.max()), 1)))
    add(not bursts, f"(k) non-speech bursts (> -40 dBFS, < 300 ms) between words: {bursts or 'none'}")
    # Whisper listen-check of every join: words heard that are not in the script around that join
    if expected is not None and joins:
        import os, tempfile, wave
        sr16 = 16000
        raw16 = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
        y = np.frombuffer(raw16, np.int16)
        gap = np.zeros(sr16, np.int16); parts = []; spans = []; pos = 0
        for j in joins:
            a_, b_ = max(0, int((j - 0.7) * sr16)), int((j + 0.7) * sr16)
            parts += [y[a_:b_], gap]; spans.append((pos / sr16, (pos + b_ - a_) / sr16, j)); pos += (b_ - a_) + len(gap)
        wav = tempfile.mktemp(suffix=".wav")
        with wave.open(wav, "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr16); wf.writeframes(np.concatenate(parts).tobytes())
        r = subprocess.run(["whisper-cli", "-m", os.path.expanduser(os.environ.get("SHORTS_STUDIO_WHISPER", os.path.join(os.environ.get("SHORTS_STUDIO_HOME", "~/.shorts-studio"), "models", "ggml-large-v3-turbo.bin"))), "-f", wav, "-l", "en",
                            "-np", "-ml", "1", "-sow"], capture_output=True, text=True)
        heard = []
        for line in r.stdout.splitlines():
            m = re.match(r"\[(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)\]\s*(.*)", line.strip())
            if m:
                t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
                wd = re.sub(r"[^a-z0-9']", "", m.group(7).lower())
                if wd: heard.append((t, wd))
        exp = set(expected)
        odd = []
        for s0, s1, j in spans:
            extra = [wd for t, wd in heard if s0 <= t < s1 and wd not in exp and wd.rstrip("s") not in exp]
            if extra: odd.append((round(j, 2), extra[:4]))
        rep.append(f"INFO (k) Whisper at each join: {len(spans)} joins checked; words not in the script: {odd or 'none'}")
    # ---- (f) crop and pan curves -----------------------------------------------------------------------
    worst = (0, None)
    for s in shots:
        n = int(round((s["t1"] - s["t0"]) * FPS))
        if s["kind"] == "face916" and s.get("track"):
            tr = s["track"]
            xs = [ease_val([(p[0], p[1]) for p in tr], 0)]  # placeholder for type
            # the crop centre follows the smoothed track in source time; sample it on the output frames
            from . import lib
            ts_ = [lib.out_to_src(res, s["t0"] + k / FPS) if s.get("free") is None else s["free"] + k / FPS for k in range(n)]
            vals = [ease_val([(p[0], p[1]) for p in tr], x) for x in ts_]
            okf = [abs(ts_[i + 1] - ts_[i] - 1 / FPS) < 0.02 for i in range(len(ts_) - 1)]     # across an audio join the source jumps: that is a cut
            step = max([abs(b - a) for a, b, o in zip(vals, vals[1:], okf) if o] or [0]) / (1080 * 9 / 16 / s.get("zoom", 1.0))
        elif s["kind"] == "scr" and s.get("keys"):
            keys = s["keys"]
            tt = [s["t0"] + k / FPS for k in range(n)]
            vals = [ease_val([(kt, r[0]) for kt, r in keys], x) for x in tt]
            ws = [ease_val([(kt, r[2]) for kt, r in keys], x) for x in tt]
            okf = [not any(tt[i] - 1.5 / FPS <= c <= tt[i + 1] + 1.5 / FPS for c in cuts) for i in range(len(tt) - 1)]
            step = max([abs(b - a) / w for a, b, w, o in zip(vals, vals[1:], ws, okf) if o] +
                       [abs(b - a) / a for a, b, o in zip(ws, ws[1:], okf) if o] + [0])
        else:
            continue
        if step > worst[0]: worst = (step, round(s["t0"], 2))
    add(worst[0] <= 0.02, f"(f) largest frame-to-frame crop/pan step: {worst[0] * 100:.2f}% of frame (at shot {worst[1]}), limit 2%")
    return not fail, [f"{label}: " + ("ALL PASS" if not fail else "ISSUES")] + rep
