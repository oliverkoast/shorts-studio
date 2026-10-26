---
name: quick-clip
description: Makes fast, punchy Shorts from one strong 30-45 second answer. Give it the video and roughly where it is.
---

# /quick-clip

One continuous answer, cut tight: every filler and pause over 0.1 s gone, punch-ins alternating 1.0x and 1.2x every
1 to 2 s, pop captions of 1 to 2 words with key words in the accent colour, a few quick graphics, an end card.
Example: `examples/quick_clip.py`.

Follow docs/workflow.md (plugin root is two folders up). Specific to this type:

- `Builder(..., maxgap=0.10, pad=0.05, tail=0.04)` and `b.punch(t0, t1, track)` for the face; `b.captions(style="pop",
  keywords=[...])`.
- **Context in the first 3 s:** who is talking (a name and role card) and, if they name something a cold viewer won't
  know, what it is, in under 8 words and in their own words (check what they or their company say it is).
- **Start on the question if there is one** ("What's your agent harness of choice?"), then the answer.
- **End on a complete thought** that pays off the hook, then `b.endcard()`. If the answer trails off, end on the last
  strong sentence before it.
- Gallery or screen-share stretches of a call: cover them with b-roll or graphics.
- Run `/qa` before you deliver.
