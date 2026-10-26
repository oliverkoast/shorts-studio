---
name: story-reframe
description: Makes Shorts from a podcast or news segment where a host tells a story. Give it the episode or link.
---

# /story-reframe

The host's face reframed to 9:16 (face-tracked and smoothed), with the evidence cut in: the actual article with
highlights, the product's own footage, and graphics for the key facts. Example: `examples/story_reframe.py`.

Follow docs/workflow.md (plugin root is two folders up). Specific to this type:

- **Source resolution:** check it first. A 1080p source gives a 608 px wide face crop, which looks soft; say so.
- **Hook:** the first line states the story in under 12 words; add a big keyword card over the face if the spoken
  line is long ("META'S AI READ HIS TEXTS").
- **Evidence over every claim:** the article (re-rendered with `studio webshot`, highlights on the exact phrase), the
  company's official footage of the product, a counter for a number ("ROW 187,462"), a quote card for a quote,
  a flow graphic for money or data moving (`scene="moneyflow"`). If the source shows the article as a screen share,
  use that stretch with the host in a bubble (`b.frame(..., bubble=(x, y, size))`).
- **Ending:** the host's question or verdict, as a complete sentence. Cut any false start before it.
- Run `/broll`, `/motion` and `/qa`.
