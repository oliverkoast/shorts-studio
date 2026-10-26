---
name: shorts-setup
description: Installs and checks everything Shorts Studio needs. Run it once before your first Short.
---

# /shorts-setup

The setup script is `scripts/setup.sh` in this plugin (two folders up from this skill). It never prompts; you ask.

1. Run `bash <plugin>/scripts/setup.sh check` and show the user the list.
2. For anything MISSING, tell them what it is and the size, and ask yes or no before installing:
   - brew (Mac only): the Homebrew package manager.
   - ffmpeg, ytdlp, whisper: command-line tools from Homebrew (on Linux: apt, pip, and a CPU build of whisper.cpp).
   - python, venv: Python 3.10+ and a private environment in ~/.shorts-studio/venv (about 0.9 GB, mostly PyTorch).
   - models: the speech models, about 2.7 GB, downloaded once into ~/.shorts-studio/models and torch's cache.
   - chrome: Google Chrome, used headless to render the graphics.
   - command: the `studio` command in ~/.shorts-studio/bin.
3. Run `bash <plugin>/scripts/setup.sh install <items...>` for the ones they approve. Use a long timeout (models take
   several minutes) and run it in the background if your tools allow, reporting when it finishes.
4. Run `check` again and confirm everything says ok.
5. Ask which brand to use; offer `/brand` now or the neutral default.
6. Suggest a folder per show or channel (for example ~/Videos/<show>/) and that they open it in Claude Code to make
   Shorts there.
