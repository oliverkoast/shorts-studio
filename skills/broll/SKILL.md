---
name: broll
description: Finds and credits the right visual for every sentence of a Short. Give it the Short's script or spec.
---

# /broll

The full playbook is docs/broll-sourcing.md (plugin root is two folders up). In short:

1. Tag what each sentence names (a product, person, object, number, event or idea). Cue the visual to that word,
   hold it 1.5 s or more, change visuals every 2 to 2.5 s.
2. Use the first source that fits:
   1. **The real product UI or page**, re-rendered: `studio webshot <url> broll/<topic>/<name>.png` (540 wide for
      phone-shaped pages, `--width 1280` for desktop docs). LOOK at the PNG: a "verify you are human" or cookie wall
      is not b-roll. Show it with `scene="ui"` and highlights on the exact phrase.
   2. **The company's own footage** from its verified channel: check with
      `yt-dlp --print "%(channel)s | %(channel_is_verified)s | %(upload_date)s" <url>`, download to
      `broll/<topic>/`, clips under 5 s, `credit="Video: <Company>"`.
   3. **A motion graphic** (`/motion`), especially for numbers and claims.
   4. **Free-license footage** (NASA, Wikimedia Commons with the license checked, Pexels or Pixabay). Never CC BY-NC.
   5. **The speaker** for opinions and asides.
3. **Facts add something:** when the speaker claims "largest" or "fastest", find the real figure on the primary
   source, show it with a comparison, and put "Source: ..." on screen.
4. **People and archival photos:** the person's or their family's own post first (public X posts can be fetched
   without signing in through `https://cdn.syndication.twimg.com/tweet-result?id=<id>&token=4`), then the
   broadcaster's own archive upload, then a reputable outlet. Check fact-checkers for viral "childhood photos".
   Never AI-generated, face-swapped, colorized or watermarked images. Never sign in to anyone's account.
5. **Rights:** company footage and re-rendered pages are fine with credit for commentary. Film, TV and news
   footage go in private review copies only. B-roll is always muted.
6. **Log everything** in `broll/<topic>/sources.md`: file, URL, channel, verified, upload date, license, how used.
