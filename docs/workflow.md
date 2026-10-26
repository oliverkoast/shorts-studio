# The Shorts workflow (every type)

`studio` is the command `/shorts-setup` installs at `~/.shorts-studio/bin/studio`. Run everything from the user's
video folder (one folder per show or channel). If `studio` is missing, run `/shorts-setup` first.

## 1. Get the source

- A local file: use it where it is. A link: `yt-dlp -f "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/b" --merge-output-format mp4 -o "source/%(id)s.%(ext)s" <url>`.
- Check who owns it (`yt-dlp --print "%(channel)s %(channel_is_verified)s" <url>`). The user's own channel: fine to post.
  Someone else's: say so before cutting, and mark the Short `(PRIVATE - not for posting)` unless they confirm rights.

## 2. Transcribe

`studio transcribe source/<file>.mp4` writes `<file>.words.json` (word timings, the only timing the cuts trust),
`<file>.txt` (one line per phrase: `[m:ss  #first-last] words`, use it to pick moments and word indices) and a
Whisper `.srt` for reading.

## 3. Pick the moment and write the script

- One continuous stretch of real talk, kept in source order. Never stitch sentences from different places.
- 30 s minimum, 45 to 75 s typical, 2:00 maximum. Hook done by 3 s, first payoff by 10 s, big reveal at 45 to 55%.
  Over 60 s, a second payoff at about 75%.
- Drop restarts, false starts ("what is the... are these"), fillers and repeated phrases. The last line must be a
  complete sentence that lands (an answer, a punchline, an opinion), never a setup.
- Show the user the script (the exact words, start and end time) before rendering if the choice is not obvious.

ROWS lists what is kept: `{"keep": [(first_word_index, last_word_index), ...], "text": "the words as they should read"}`.
The text must have exactly one token per kept word (use `~` for a kept sound you do not want captioned, `_` to join
two tokens into one caption word). The indices come from the `#first-last` ranges in the `.txt`.

## 4. Write `shorts/<name>/spec.py`

Start from the matching file in `examples/` (one per type). It builds the Short with `studio.short.Builder`:
pictures cued by word (`b.T(i)`), graphics from the kit (`b.kit(...)`), b-roll (`b.footage(...)`), captions, end card.
Face positions: render a frame with a grid (`ffmpeg -ss <t> -i src -frames:v 1 -vf drawgrid=w=100:h=100:t=1:c=red@0.5 f.jpg`),
look at it, and pass the face centre to `track_face(src, t0, t1, cx, cy)` for each camera shot (the source's own cuts
are where the face moves: find them with `ffmpeg -vf "select='gt(scene,0.25)',showinfo"`).

## 5. Render, look, check

1. `studio render shorts/<name>/spec.py` writes `out/<name>.mp4` and a phone copy in `out/review/`.
2. Make a 1 fps contact sheet (`ffmpeg -i out/<name>.mp4 -vf "fps=1,scale=216:384,tile=12x6" -frames:v 1 sheet.jpg`) and
   LOOK at it: clipped text, a crop on the wrong thing, a bot-check page as b-roll, a graphic that repeats the caption.
3. `studio qa shorts/<name>/spec.py out/<name>.mp4`: the 13-check gate. Fix every FAIL and re-render. A Short is not
   done until it says ALL PASS.
4. Send the phone copy (`out/review/`). Then take notes in plain words ("there's a noise at 7 s", "remove 'which'",
   "end on a complete thought") and fix the cause in the spec, not just the symptom. Re-run the gate after every change.

## 6. Publish copy (when asked)

Write `out/<name> - publish.md` with a title, description and hashtags for each platform (see docs/platforms.md).
Never post or upload for the user without their explicit go-ahead.
