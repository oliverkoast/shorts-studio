# B-roll sourcing playbook

How Shorts Studio finds b-roll. The `/broll` skill follows this.

## 1. Find what each sentence names

For every sentence of the cut script, tag what it names: a product, a person, an object, a number, an event or an idea. Then cue a visual to the exact word that names it, using the CTC word time, and hold it for at least 1.5 s. Aim to change the visual every 2–2.5 s.

## 2. Use the first source in this list that fits

1. **The real product UI.** Re-render the live page in headless Chrome at 2x, full page, scrolling it once so lazy-loaded images appear. Add highlights, arrows and circles in code, never by painting on the image. This works for products, docs, articles and patents.
2. **The company's own footage**, from its verified YouTube channel, X account or press kit. Check `channel_is_verified` in yt-dlp and that the channel name matches the company. Use clips under 5 s with an on-screen credit ("Video: SpaceX").
3. **A motion graphic** from the kit:
   - spoken numbers become a counter or comparison bars;
   - a size claim becomes a to-scale comparison;
   - a process becomes a diagram that builds on the words;
   - a transfer becomes a flow graphic;
   - a quote becomes a quote card.
4. **Free-license footage** for generic ideas: NASA, Wikimedia Commons after checking the license, or Pexels/Pixabay. Never use CC BY-NC.
5. **The speaker on camera**, for opinions, asides and the ending.

## 3. Facts must add something

When the speaker makes a claim ("the largest, most powerful"), show the actual figure from the primary source (124 m, 18.1M lbf, more than 2x Saturn V) instead of repeating the words. Check the figure on the live official page, put a small "Source: ..." credit on screen, and log the URL.

## 4. People and archival photos

- **Order of preference:**
  1. the person's own post, or a family member's (for example @mayemusk);
  2. the broadcaster's own archive upload (CNN 1999, CBS 1998);
  3. a reputable outlet that reproduces the post.
- **X posts without signing in:** public posts can be fetched through X's embed service (`cdn.syndication.twimg.com/tweet-result?id=...`). Never sign in to accounts.
- **Verify before use:** a photo from a fan or compilation channel is used only if a reputable outlet shows the same photo. Search fact-checkers for viral "childhood photos"; some are fake.
- **Never** use AI-generated, face-swapped, colorized, over-upscaled or watermarked-preview images.
- Give stills a slow push-in (about 0.1% zoom per frame) over a blurred fill of themselves.

## 5. Rights

- Company footage, re-rendered pages and our own graphics are fine for commentary, with credit.
- Film and TV clips (Star Wars, Star Trek), news archive (CNN) and third-party interviews (The Economist) go only into private review copies. They are marked "PRIVATE - not for posting" in the filename, burned into the video, and noted in notes.md.
- Mute b-roll unless its sound is the point. The voice is the only audio, plus a licensed music bed if one is chosen.

## 6. Log and cache everything

Cache every file under `broll/<topic>/` in the video folder, with a `sources.md` listing the file, URL, channel, verified status, upload date, license and how it was used.

## 7. Check before delivering

- The QA gate passes:
  - every graphic is inside the safe area and no text overflows its card;
  - no caption repeats the words on a card;
  - no visual is on screen for under 1 s;
  - there are no stray noises at cuts.
- A contact sheet of every graphic is reviewed by eye.
- Pages are checked for bot or verification screens. A "verify you are human" page is not b-roll; use a logo card instead.
