---
name: interview-split
description: Makes Shorts from someone else's interview or talk, with visuals on top. Give it the video or link.
---

# /interview-split

Top half (1080x960): what they are talking about, as official footage, archival photos and fact graphics. Bottom half
(1080x960): the speaker, cropped to whoever is talking and cut where the source cuts. A 4 px divider in the brand's
deep colour, captions on the divider. Example: `examples/interview_split.py`.

Follow docs/workflow.md (plugin root is two folders up). Specific to this type:

- **Rights first:** if it is not the user's footage, say so, and name the file `<name> (PRIVATE - not for posting).mp4`
  unless they confirm they can post it. Credit the source on the bottom panel ("Video: The Economist").
- `Builder(..., layout="split")`; put pictures in `panel="top"` or `panel="bottom"`.
- **Bottom panel:** find the source's own cuts (`select='gt(scene,0.25)'`), and for each shot the x centre of the
  person speaking; switch to the interviewer while they ask a question.
- **Top panel:** a new visual every 2 to 2.5 s, cued to the word that names it. When the speaker makes a claim
  ("the largest", "the fastest"), show the real figure with a comparison (`scene="height"`, `scene="counter"` with
  `compare`), checked on the official source and credited on screen. Pair fiction with the real thing where it fits.
- Run `/broll` (official sources only, clips under 5 s, credited) and `/qa`.
