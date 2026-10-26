"""Word timings for a video: wav2vec2 CTC (the timing the cuts trust) plus a readable Whisper transcript.

  python -m studio.transcribe <video> [--out <dir>]

Writes <name>.words.json ([{"w", "t0", "t1"}], every word the model hears, restarts included),
<name>.srt (Whisper, for reading) and <name>.txt (one line per pause, with source times, for picking moments)."""
import json, os, subprocess, sys, time

WHISPER_MODEL = os.path.expanduser(os.environ.get("SHORTS_STUDIO_WHISPER", os.path.join(os.environ.get("SHORTS_STUDIO_HOME", "~/.shorts-studio"), "models", "ggml-large-v3-turbo.bin")))


def ctc_words(wav16):
    import numpy as np, torch, torchaudio, scipy.io.wavfile as wavfile
    sr, a = wavfile.read(wav16)
    a = torch.from_numpy(a.astype(np.float32) / 32768.0)
    B = torchaudio.pipelines.WAV2VEC2_ASR_LARGE_LV60K_960H
    dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    model = B.get_model().to(dev).eval()
    labels = B.get_labels(); BLANK, SEP = 0, labels.index("|"); HOP = 320 / 16000
    WIN, STEP = 30.0, 27.0
    words, t_start, n = [], 0.0, len(a) / sr
    while t_start < n:
        s0, s1 = int(t_start * sr), int(min(n, t_start + WIN) * sr)
        with torch.inference_mode():
            em, _ = model(a[s0:s1].unsqueeze(0).to(dev))
        ids = em[0].argmax(-1).cpu().numpy()
        cur, f0, f1, prev, local = "", None, None, -1, []
        for f, k in enumerate(ids):
            if k != prev and k != BLANK:
                if k == SEP:
                    if cur: local.append((cur, f0, f1))
                    cur, f0 = "", None
                else:
                    if f0 is None: f0 = f
                    cur += labels[k]; f1 = f
            elif k == prev and k not in (BLANK, SEP) and cur:
                f1 = f
            prev = k
        if cur: local.append((cur, f0, f1))
        lo = t_start + (1.5 if t_start > 0 else 0.0)
        hi = t_start + WIN - 1.5 if t_start + WIN < n else n + 1
        for w, f0, f1 in local:
            t0, t1 = t_start + f0 * HOP, t_start + (f1 + 1) * HOP
            if lo <= (t0 + t1) / 2 < hi:
                words.append({"w": w.lower(), "t0": round(t0, 3), "t1": round(t1, 3)})
        t_start += STEP
    words.sort(key=lambda w: w["t0"])
    return words


def main(a):
    src = os.path.abspath(a[0])
    out = os.path.abspath(a[a.index("--out") + 1]) if "--out" in a else os.path.dirname(src)
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, os.path.splitext(os.path.basename(src))[0])
    wav = base + ".16k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ar", "16000", "-ac", "1", wav], check=True)
    tic = time.time()
    w = ctc_words(wav)
    json.dump(w, open(base + ".words.json", "w"))
    # a readable index: one line per phrase (split at pauses over 0.7 s), with word indices and source times
    lines, cur, prev = [], [], None
    for i, x in enumerate(w):
        if prev is not None and x["t0"] - prev > 0.7:
            lines.append(cur); cur = []
        cur.append((i, x)); prev = x["t1"]
    if cur: lines.append(cur)
    with open(base + ".txt", "w") as f:
        for ln in lines:
            t = ln[0][1]["t0"]
            f.write(f"[{int(t // 60)}:{t % 60:05.2f}  #{ln[0][0]}-{ln[-1][0]}] " + " ".join(x["w"] for _, x in ln) + "\n")
    print(f"{len(w)} words in {time.time() - tic:.0f}s -> {base}.words.json, {base}.txt")
    if os.path.exists(WHISPER_MODEL):
        subprocess.run(["whisper-cli", "-m", WHISPER_MODEL, "-f", wav, "-l", "en", "-osrt", "-of", base, "-np"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"readable transcript -> {base}.srt")


if __name__ == "__main__":
    main(sys.argv[1:])
