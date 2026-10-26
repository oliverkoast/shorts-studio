"""The QA gate: thirteen checks every Short must pass before it is called done.

  python -m studio.qa_gate shorts/<name>/spec.py "out/<name>.mp4"

   1 frames and timestamps        constant 30 fps, no gaps, no duplicate timestamps
   2 freezes                      nothing frozen over 1.2 s outside intended holds
   3 jumps                        no frame-to-frame spike where no cut is intended
   4 flashes                      no black frames, no single-frame white flashes
   5 clicks                       no discontinuity at any audio join
   6 level jumps                  no voiced-level jump over 3 dB between joined pieces
   7 loudness                     -14 LUFS +/- 0.6, true peak at or under -1.0 dBFS
   8 moves                        crop, pan and face-track moves under 2% of the frame per frame
   9 graphics layout              every text and card inside the 60 px safe area, no overflow (rendered in Chrome)
  10 caption widths               every caption and card narrower than the safe width
  11 short shots                  no visual held under 1.0 s (besides the opening face beat and punch-ins)
  12 noise between words          no non-speech burst (> -40 dBFS, < 300 ms) in any gap that holds a cut
  13 clean start, end and length  no false starts, restarts or fillers in the first/last 5 s, the last line
                                  is a complete sentence a Whisper read-back confirms, and 30 s to 2:00 long
Checks: qa.gate (a-f), the kit layout safe-area check in Chrome on every kit clip, ASS overlay widths,
and the ending: the last spoken sentence before the end card must be complete (ends . ? !) and match
a Whisper read-back of the final file."""
import importlib, json, os, re, subprocess, sys
from . import lib, qa

D = os.path.abspath("work")
WHISPER_MODEL = os.path.expanduser(os.environ.get("SHORTS_STUDIO_WHISPER", os.path.join(os.environ.get("SHORTS_STUDIO_HOME", "~/.shorts-studio"), "models", "ggml-large-v3-turbo.bin")))


def whisper_tail(mp4):
    wav = os.path.join(D, "qa_tail.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-8", "-i", mp4, "-ar", "16000", "-ac", "1", wav])
    r = subprocess.run(["whisper-cli", "-m", WHISPER_MODEL, "-f", wav,
                        "-l", "en", "-np", "-nt"], capture_output=True, text=True)
    return " ".join(r.stdout.split())


FILLERS = {"um", "uh", "erm", "uhm", "hmm"}
OPENERS = {"so", "like", "and", "but", "well", "yeah"}


def false_starts(mp4, total):
    """Scan a word-level Whisper read-back of the whole Short for false starts, restarts and fillers.
    Anything in the first or last 5 s fails; elsewhere it is listed for review."""
    wav = os.path.join(D, "qa_full.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-ar", "16000", "-ac", "1", wav])
    r = subprocess.run(["whisper-cli", "-m", WHISPER_MODEL, "-f", wav, "-l", "en",
                        "-np", "-ml", "1", "-sow"], capture_output=True, text=True)
    ws = []
    for line in r.stdout.splitlines():
        mm = re.match(r"\[(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)\]\s*(.*)", line.strip())
        if mm and mm.group(7).strip():
            ws.append((int(mm.group(1)) * 3600 + int(mm.group(2)) * 60 + float(mm.group(3)), mm.group(7).strip()))
    hits = []
    low = [(t, re.sub(r"[^a-z']", "", w.lower()), w) for t, w in ws]
    for i, (t, w, raw) in enumerate(low):
        if w in FILLERS: hits.append((t, f"filler '{raw}'"))
        if i + 1 < len(low) and w and w == low[i + 1][1] and w not in ("that", "had", "very"): hits.append((t, f"repeated '{raw} {low[i + 1][2]}'"))
        if w in OPENERS and (i == 0 or ws[i - 1][1].rstrip().endswith((".", "?", "!"))) and w in ("like", "so") and i + 1 < len(low) and low[i + 1][1] in ("like", "so", "um", "uh"):
            hits.append((t, f"stacked opener '{raw} {low[i + 1][2]}'"))
    # a short question or sentence (<= 4 words) followed straight away by another one that restates it
    sents, cur = [], []
    for t, w in ws:
        cur.append((t, w))
        if w.rstrip().endswith((".", "?", "!")): sents.append(cur); cur = []
    if cur: sents.append(cur)
    for a, b in zip(sents, sents[1:]):
        if len(a) <= 4 and a[-1][1].endswith("?") and b[-1][1].endswith("?"):
            hits.append((a[0][0], "restart: '" + " ".join(w for _, w in a) + "' then another question"))
        if len(a) <= 3 and a[-1][1].lower().rstrip(".?!,") in ("the", "a", "is", "of", "to", "and", "so"):
            hits.append((a[0][0], "abandoned phrase: '" + " ".join(w for _, w in a) + "'"))
    edge = [(t, h) for t, h in hits if t < 5 or t > total - 5]
    mid = [(t, h) for t, h in hits if not (t < 5 or t > total - 5)]
    s = ("PASS " if not edge else "FAIL ") + f"(l) false starts, restarts and fillers in the first/last 5 s: {[(round(t, 1), h) for t, h in edge] or 'none'}"
    if mid: s += f"; elsewhere, for review: {[(round(t, 1), h) for t, h in mid]}"
    return s


def run_spec(spec_path, mp4):
    """Import a Short's spec.py, rebuild its plan (deterministic) and run every check on the rendered mp4."""
    import importlib.util
    sp = importlib.util.spec_from_file_location("short_spec", spec_path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    s = m.build()
    res, total, total_v = s["res"], s["total"], s["total_v"]
    if total_v > total: res = res + [(res[-1][1], res[-1][1] + total_v - total, total)]
    shots = s["top"] + s["bot"] if s["layout"] == "split" else s["shots"]
    bands = {sh["src"]: sh.get("band") for sh in shots if sh["kind"] == "clip"}
    cuts = sorted({0.0, total} | {o for a, b, o in s["res"]} | {o + b - a for a, b, o in s["res"]})
    for group in ((s["top"], s["bot"]) if s["layout"] == "split" else (s["shots"],)): lib.snap_shots(group, cuts)
    pc = lib.pan_cuts(shots)
    holds = [(x["t0"], x["t1"]) for x in shots if x.get("hold") or x["kind"] in ("scr", "fit", "cam")]
    expected = set()
    for r_ in s["rows"]:
        for w_ in re.sub(r"[^a-z0-9' _]", " ", r_["text"].lower().replace("_", " ")).split(): expected.add(w_)
    expected |= {"the", "a", "and", "so", "i", "it", "you", "know", "like", "um", "uh"}
    ok, rep = qa.gate(mp4, shots, s["res"], total_v, os.path.basename(mp4), holds=holds, extra_cuts=pc,
                      wout=list(s["wm"].values()), expected=expected)
    lay = []
    for k, (ks, o) in enumerate(s["kits"]):
        p = lib.layout_check(ks, band=bands.get(o), port=9850 + k % 20, mp4=o)
        lay += [f"{os.path.basename(o)}: {x}" for x in p]
    rep.append(("PASS " if not lay else "FAIL ") + f"(g) graphics layout safe area / text fit: {lay or 'all boxes inside, no text overflow'}")
    vis = s["top"] if s["layout"] == "split" else shots
    short = [(round(x["t0"], 2), round(x["t1"] - x["t0"], 2)) for k, x in enumerate(vis)
             if (x["t1"] - x["t0"] < 1.0 and k > 0 and x["kind"] != "face916") or x["t1"] - x["t0"] <= 0]
    rep.append(("PASS " if not short else "FAIL ") + f"(j) visuals held under 1.0 s: {short or 'none'}")
    ov = lib.ass_overflow(s["ass"])
    rep.append(("PASS " if not ov else "FAIL ") + f"(h) caption and card widths: {ov or 'all inside the safe area'}")
    rep.append(false_starts(mp4, total_v))
    last = s["rows"][-1]["text"].strip()
    tail = whisper_tail(mp4)
    lastw = [w for w in re.sub(r"[^a-z ]", " ", last.lower().replace("~", " ")).split()][-3:]
    good = last.endswith((".", "?", "!")) and all(w in tail.lower() for w in lastw)
    rep.append(("PASS " if good else "FAIL ") + f"(i) ending: last line {last[-70:]!r}; heard: {tail[-140:]!r}")
    rep.append(("PASS " if 30 <= total_v <= 120 else "FAIL ") + f"(m) length {total_v:.1f} s (30 s to 2:00; 45 to 75 s is the sweet spot)")
    allok = not any(r.startswith("FAIL") for r in rep[1:])
    return allok, [f"{os.path.basename(mp4)}: " + ("ALL PASS" if allok else "ISSUES")] + rep[1:]


if __name__ == "__main__":
    os.makedirs(D, exist_ok=True)
    ok, lines = run_spec(sys.argv[1], sys.argv[2])
    print("\n".join(lines))
    rp = os.path.splitext(sys.argv[2])[0] + " - QA.md"
    open(rp, "w").write("\n".join(lines) + "\n")
    print("report:", rp)
    sys.exit(0 if ok else 1)
