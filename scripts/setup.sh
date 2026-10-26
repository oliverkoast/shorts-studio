#!/usr/bin/env bash
# Shorts Studio setup. Non-interactive on purpose: Claude asks you yes/no in the chat, then runs one of these.
#
#   setup.sh check                 what is installed, what is missing (one line each)
#   setup.sh install <item>...     install items: brew ffmpeg ytdlp whisper python venv models fonts chrome
#   setup.sh all                   everything that is missing
#
# Everything the plugin keeps lives in ~/.shorts-studio (venv, models, brands, the `studio` command).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOME_DIR="${SHORTS_STUDIO_HOME:-$HOME/.shorts-studio}"
VENV="$HOME_DIR/venv"
MODELS="$HOME_DIR/models"
WHISPER_MODEL="$MODELS/ggml-large-v3-turbo.bin"
WHISPER_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin"
OS="$(uname -s)"
export TORCH_HOME="${TORCH_HOME:-$HOME_DIR/torch}"      # the word-timing model lives with everything else
mkdir -p "$HOME_DIR/bin" "$MODELS"
if [ "$OS" = "Darwin" ]; then export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"; fi

have() { command -v "$1" >/dev/null 2>&1; }
chrome_path() {
  for p in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" "/Applications/Chromium.app/Contents/MacOS/Chromium" \
           "$(command -v google-chrome 2>/dev/null)" "$(command -v chromium 2>/dev/null)" "$(command -v chromium-browser 2>/dev/null)"; do
    [ -n "$p" ] && [ -x "$p" ] && { echo "$p"; return 0; }
  done
  return 1
}
pybin() {
  for p in python3.13 python3.12 python3.11 python3.10 python3; do
    if have "$p" && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then command -v "$p"; return 0; fi
  done
  return 1
}

check() {
  st() { printf "%-8s %-8s %s\n" "$1" "$2" "$3"; }
  if [ "$OS" = "Darwin" ]; then have brew && st brew ok "$(command -v brew)" || st brew MISSING "Homebrew installs the tools below"; fi
  have ffmpeg && ffmpeg -hide_banner -filters 2>/dev/null | grep -q " ass " && st ffmpeg ok "$(command -v ffmpeg)" \
    || st ffmpeg MISSING "video cutting and captions (needs libass)"
  have yt-dlp && st ytdlp ok "$(command -v yt-dlp)" || st ytdlp MISSING "downloads source videos and official b-roll"
  have whisper-cli && st whisper ok "$(command -v whisper-cli)" || st whisper MISSING "readable transcript and the QA listen-check"
  pybin >/dev/null && st python ok "$(pybin)" || st python MISSING "Python 3.10 or newer"
  [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import torch, torchaudio, numpy, scipy, PIL, websocket, fontTools" 2>/dev/null \
    && st venv ok "$VENV" || st venv MISSING "Python packages: torch, torchaudio, numpy, scipy, pillow, websocket-client, fonttools"
  [ -s "$WHISPER_MODEL" ] && st models ok "$MODELS" || st models MISSING "speech models, about 2.7 GB download (once)"
  chrome_path >/dev/null && st chrome ok "$(chrome_path)" || st chrome MISSING "Google Chrome renders the motion graphics"
  [ -x "$HOME_DIR/bin/studio" ] && st command ok "$HOME_DIR/bin/studio" || st command MISSING "the studio command"
}

install_one() {
  case "$1" in
    brew)
      [ "$OS" = "Darwin" ] || { echo "brew: not needed on $OS"; return 0; }
      have brew && { echo "brew: already installed"; return 0; }
      NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" ;;
    ffmpeg)
      if [ "$OS" = "Darwin" ]; then brew install ffmpeg; else sudo apt-get install -y ffmpeg; fi ;;
    ytdlp)
      if [ "$OS" = "Darwin" ]; then brew install yt-dlp; else "$(pybin)" -m pip install --user -U yt-dlp; fi ;;
    whisper)
      if [ "$OS" = "Darwin" ]; then brew install whisper-cpp
      else  # CPU build from source
        sudo apt-get install -y build-essential cmake git
        rm -rf "$HOME_DIR/whisper.cpp" && git clone --depth 1 https://github.com/ggerganov/whisper.cpp "$HOME_DIR/whisper.cpp" \
          && cmake -S "$HOME_DIR/whisper.cpp" -B "$HOME_DIR/whisper.cpp/build" -DCMAKE_BUILD_TYPE=Release \
          && cmake --build "$HOME_DIR/whisper.cpp/build" -j --config Release \
          && ln -sf "$HOME_DIR/whisper.cpp/build/bin/whisper-cli" "$HOME_DIR/bin/whisper-cli"
      fi ;;
    python)
      if [ "$OS" = "Darwin" ]; then brew install python@3.12; else sudo apt-get install -y python3 python3-venv python3-pip; fi ;;
    venv)
      PY="$(pybin)" || { echo "python missing"; return 1; }
      "$PY" -m venv "$VENV" && "$VENV/bin/pip" install -q --upgrade pip \
        && "$VENV/bin/pip" install -q torch torchaudio numpy scipy pillow websocket-client fonttools ;;
    models)
      if [ ! -s "$WHISPER_MODEL" ]; then
        curl -L --fail -o "$WHISPER_MODEL.part" "$WHISPER_URL" && mv -f "$WHISPER_MODEL.part" "$WHISPER_MODEL" || return 1
      fi
      # the word-timing model (wav2vec2, about 1.2 GB) downloads into torch's cache on first load
      "$VENV/bin/python" -c "import torchaudio; torchaudio.pipelines.WAV2VEC2_ASR_LARGE_LV60K_960H.get_model(); print('word-timing model ready')" ;;
    chrome)
      if [ "$OS" = "Darwin" ]; then brew install --cask google-chrome; else echo "Install Google Chrome or Chromium with your package manager, then run check again."; fi ;;
    command)
      cat > "$HOME_DIR/bin/studio" <<EOF
#!/usr/bin/env bash
# Runs a Shorts Studio module with the plugin's Python: studio short|transcribe|qa|brand|webshot ...
export PATH="$HOME_DIR/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH"
export PYTHONPATH="$ROOT\${PYTHONPATH:+:\$PYTHONPATH}"
export TORCH_HOME="$TORCH_HOME"
export SHORTS_STUDIO_HOME="$HOME_DIR"
cmd="\$1"; shift
case "\$cmd" in
  transcribe) exec "$VENV/bin/python" -m studio.transcribe "\$@" ;;
  qa)         exec "$VENV/bin/python" -m studio.qa_gate "\$@" ;;
  brand)      exec "$VENV/bin/python" -m studio.brand "\$@" ;;
  render)     exec "$VENV/bin/python" "\$@" ;;
  kit)        exec "$VENV/bin/python" -m studio.kitcli "\$@" ;;
  webshot)    exec "$VENV/bin/python" -m studio.webshot "\$@" ;;
  python)     exec "$VENV/bin/python" "\$@" ;;
  *) echo "studio: transcribe <video> | render <spec.py> | qa <spec.py> <out.mp4> | brand ... | kit ... | webshot <url> <out.png>"; exit 2 ;;
esac
EOF
      chmod +x "$HOME_DIR/bin/studio" && echo "command: $HOME_DIR/bin/studio" ;;
    *) echo "unknown item: $1"; return 1 ;;
  esac
}

case "${1:-check}" in
  check) check ;;
  install) shift; for i in "$@"; do echo "== $i"; install_one "$i" || { echo "FAILED: $i"; exit 1; }; done; echo; check ;;
  all)
    t0=$(date +%s)
    for i in brew ffmpeg ytdlp whisper python venv models chrome command; do
      check | grep -q "^$i .*MISSING" && { echo "== $i"; install_one "$i" || { echo "FAILED: $i"; exit 1; }; }
    done
    echo; check; echo "setup took $(( $(date +%s) - t0 )) s" ;;
  *) sed -n 2,8p "$0" ;;
esac
