---
name: screen-demo
description: Makes Shorts from your own screen recording. Give it the recording (and your camera file if separate).
---

# /screen-demo

The product is the star: the screen in a rounded window, the presenter's face in a round bubble in a top corner,
highlights on the prompt and the result, the reveal in the middle. Example: `examples/screen_demo.py`.

Follow docs/workflow.md (plugin root is two folders up). Specific to this type:

- **Voice:** usually the screen file's audio. If the camera is a separate file, find the offset by matching the two
  audio tracks (cross-correlate a 30 s stretch) and pass it to `b.camera(cam, offset=...)`.
- **Window crops:** `b.screen(t0, t1, keys=[(t, (x, y, width)), ...])` in screen pixels. Default to the FULL screen so
  the viewer sees the navigation; punch in only to read a result, about once per section. A crop that would move
  faster than 2% of the frame per frame becomes a hard cut automatically.
- **Hide what must not air:** the presenter's script, private names, a burned-in camera box: `patch=[(x, y, w, h)]`.
- **Waits:** if the product takes time (a build, a render), cut to the moment it finishes; never show a loading screen
  for more than a second.
- **No prompt on screen?** Add a "Prompt:" card with the real prompt (`b.key(...)`), or a short working one in their
  words.
- **Hook:** the first line says what the product does in plain words, over a 0.75 s face beat and then the result.
- Run `/broll` for the official launch footage and product pages, `/motion` for the numbers, `/qa` before you deliver.
