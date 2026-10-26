# Shorts Studio

**Long video in. Finished Shorts out.** A Claude Code plugin that turns your recordings, interviews and podcasts into
Shorts for YouTube, TikTok and Instagram: cut on real words, captioned, with real b-roll, motion graphics in your
brand, and a 13-check QA gate before you see anything.

```
/plugin marketplace add oliverkoast/shorts-studio
/plugin install shorts-studio@shorts-studio
/shorts-setup
```

Then, in a folder with your video: **"Make 3 Shorts from this video."**

## What you need

- **A paid Claude plan (Pro or Max)** for Claude Code. Use the Code tab in the Claude desktop app, or `claude` in a
  terminal. The plain chat can't do this: editing video needs your computer.
- **A Mac or Linux.** Windows isn't supported yet. Apple Silicon is fastest (the speech models run on its GPU).
- **About @DISK@ of free disk space** for the tools and speech models, plus room for your videos.
- **Free tools that `/shorts-setup` installs for you** (it asks before each one):
  - ffmpeg: cutting, audio and captions
  - Whisper and the speech models (@MODELS@ download, once): word timings and transcripts
  - yt-dlp: works with YouTube links
  - Python, with a private environment for the plugin (@VENV@)
  - Google Chrome: renders the motion graphics (most people already have it)
- **On a Mac, setup uses Homebrew**, which may ask for your Mac password once.
- **Optional:** a free Pexels API key for generic stock footage.

First-time setup took **@SETUP@** on a clean test (most of it downloads).

## The four Short types

Each is its own command. `/short` picks the right one for you.

| Command | Makes Shorts from | Looks like |
|---|---|---|
| `/screen-demo` | your own screen recording | the product in a window, your face in a corner bubble, highlights, the reveal mid-way |
| `/interview-split` | someone else's interview or talk | the subject on top (official footage, facts), the speaker below, captions on the divider |
| `/story-reframe` | a podcast or news segment where a host tells a story | the host reframed to vertical, the evidence cut in: the article, the product, the numbers |
| `/quick-clip` | one strong 30 to 45 second answer | fast cuts, punch-ins, 1 to 2 word pop captions, an end card |

## The helpers

| Command | What it does |
|---|---|
| `/broll` | finds the right visual for every sentence: the real product page, the company's own footage, real figures with sources; credits and logs everything |
| `/motion` | animated graphics timed to the spoken word: counters, comparisons, to-scale size charts, diagrams, flows, quote cards, UI callouts |
| `/qa` | 13 automatic checks: noises and clicks at cuts, text cut off, false starts, a complete ending, loudness, and more |
| `/brand` | your fonts, colours and logo, set up once from your website or your files |
| `/shorts-setup` | installs and checks everything |

## Prompts that work

- "Make 3 Shorts from `talk.mp4`" / "Here's a podcast: <link>. Find the 2 best moments."
- "Make a screen demo of the part where the dashboard builds itself."
- "When he says 'largest', show how big it actually is compared to something people know."
- "There's a noise at 7 seconds, fix it." / "Remove 'which' from the first line." / "End on a complete thought."
- "Set up my brand from <website>." / "Run the QA check." / "Write the TikTok and YouTube captions."

## How it works

Everything runs on your computer, inside Claude Code:

1. **Transcribe**: a word-timing model (wav2vec2) hears every word, restarts included; Whisper writes a readable copy.
2. **Pick and script**: one continuous stretch of real talk, fillers and false starts removed, ending on a complete thought.
3. **Build**: a short Python spec cues every picture, graphic and caption to the word that introduces it.
4. **Render**: ffmpeg cuts at the quiet points between words; headless Chrome renders the graphics in your brand.
5. **Check**: the QA gate runs 13 checks; anything that fails gets fixed before you see it.
6. **Notes**: tell it what's wrong in plain words; it fixes the cause, not just the clip.

Your brands live in `~/.shorts-studio/brands/`, your videos and Shorts in whatever folder you work in (one per show
works well). Nothing is uploaded anywhere, and nothing is posted for you.

## Try it without your own video

`bash <plugin>/examples/make_sample.sh sample` makes a short talk we own outright (macOS speech and a drawn presenter).
Open the `sample` folder in Claude Code and say "make a quick clip from talk.mp4".

## Rights

Shorts Studio credits every clip it uses, and marks a Short `(PRIVATE - not for posting)` when it uses footage you
don't own. Company footage and re-rendered pages are usually fine with credit for commentary; film, TV and news footage
are for private review only. You decide what you post.

## License

MIT, see LICENSE. The default brand's font (Inter) is under the SIL Open Font License.
