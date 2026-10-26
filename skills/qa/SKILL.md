---
name: qa
description: Checks a rendered Short with 13 automatic checks before anyone sees it. Give it the Short's spec and mp4.
---

# /qa

`studio qa shorts/<name>/spec.py out/<name>.mp4` prints PASS or FAIL for each check and writes
`out/<name> - QA.md`. A Short is done only when it says ALL PASS. The checks (studio/qa_gate.py):

1. frames and timestamps: constant 30 fps, no gaps or duplicates
2. freezes over 1.2 s outside intended holds
3. frame-to-frame jumps where no cut is intended (graphic pops, crop jumps)
4. black frames and single-frame white flashes
5. clicks at audio joins
6. voiced-level jumps over 3 dB between joined pieces
7. loudness -14 LUFS (+/- 0.6), true peak at or under -1.0 dBFS
8. crop, pan and face-track moves under 2% of the frame per frame
9. every graphic's text and cards inside the safe area, nothing overflowing (rendered in Chrome)
10. every caption and card narrower than the safe width
11. no visual held under 1 s (besides the opening face beat and punch-ins)
12. no stray noise (a cut word's fragment, a breath, a smack) in any gap that holds a cut
13. no false starts, restarts or fillers in the first or last 5 s, the last line is a complete sentence, and the
    Short is 30 s to 2:00 long

When something fails, fix the cause in the spec (a row, a cue, a crop), re-render and re-run. Also look at a 1 fps
contact sheet yourself: the gate cannot tell a bot-check page from b-roll, or a weak hook from a strong one.
When the user reports a problem the gate missed, fix it and say how the gate could catch it next time.
