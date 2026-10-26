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
6. **Prefer clean frames.** Raw footage, photos and the product itself beat another creator's designed collage
   (their hand-drawn titles, their date stamps, their layout). Use a collage only when nothing clean exists, mark
   it `"kind": "collage"`, and say so in sources.md.
7. **Check every pick before it goes in the Short.** List the clips in `broll/clips.json`
   (`id, line, src, t, d, what, credit, license, kind`), then run
   `studio broll-sheet broll/clips.json script.md "broll/contact sheet.jpg"`. It renders the start, middle and end
   frame of every clip and, with tesseract, reads the on-screen text and flags years that contradict the line.
   Then LOOK at the sheet, clip by clip, against its line: is it the thing named (not a modern plane for 1984, not
   the wrong person), and does any on-screen text, date or label contradict the script? Fix every problem (move
   the in-point, pick another clip, or change the line) and re-run until it says ok, or explain the flag in
   sources.md. Show the user the sheet.
8. **Log everything** in `broll/<topic>/sources.md`: file, URL, channel, verified, upload date, license, how used,
   and any flag you accepted.
