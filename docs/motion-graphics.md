# Motion graphics playbook: charts, numbers and explainers

How the kit's graphics are meant to be used (`studio/kit/kit.html`). The example below is a to-scale height comparison: a rocket claimed to be "the largest" shown next to a rival and a familiar landmark.

## Why the Starship graphic works

1. **It answers the claim.** He says "largest". The graphic shows how large (124 m) and against what (Saturn V, the Statue of Liberty). Use one familiar reference and one rival.
2. **It is to scale.** The heights are real ratios on a shared ground line with a metre ruler, so the eye reads the difference before any text.
3. **It builds on the word.** The silhouettes rise in sequence, smallest first, and the subject comes last and highest. The counter climbs as the rocket grows.
4. **One accent.** Only the subject gets the brand's accent colour. The references stay in the second accent and the light colour.
5. **The number sits on the thing,** not in a legend: "124 m / 407 ft" rides on top of the rocket.
6. **Sourced.** "Source: SpaceX, NASA" sits in small type, and the figures were checked on the official page.

## Picking a chart for each kind of claim

| What they say | Graphic |
|---|---|
| "the biggest / tallest / heaviest" | To-scale size comparison: the subject plus one familiar object and one rival |
| "X times more", "faster than" | Comparison bars: two bars on a shared baseline, ratio labelled ("more than 2x") |
| a single big number | Counter in an accent-coloured box that eases up to the exact figure, with a unit sub-line and a meter that fills |
| A vs B | Versus: two cards in sequence, never stacked on top of each other |
| growth or change over time | Line chart: draw the line, then dot and label one highlighted point |
| rankings | Bar race or ranked bars that build top-down, with the subject highlighted |
| share or split | Donut: a single segment highlighted, with the rest muted |
| a sequence of events | Timeline: a rail draws down, and dots land on each spoken date |
| how something works | Diagram: boxes and arrows built on each noun, with pulses travelling along the arrows |
| money, data or access moving | Flow: source icon, link, permission lock, then items streaming along an eased arc; the lock turns red if it's a risk |
| a quoted line | Quote card: metal quote marks and words revealed one by one, with a real avatar and logo |

## Rules every graphic follows

- **Show the exact number.** If they say "almost 20 million", show 18.1M. Round only on the unit line.
- **One idea per graphic,** at most about 6 words of headline. A second fact gets its own graphic in sequence.
- **Cue to the word,** using CTC word times. Hold at least 1.5 s and no more than about 4 s, then cut to something else.
- **Motion:**
  - ease every move; nothing is linear except tickers;
  - at least 2 elements moving;
  - a slow camera push under the whole graphic;
  - motion blur from sub-frame averaging.
- **Safe area:** every box rests 60 px or more inside its panel, and text shrinks to fit or wraps. Cards slide in from no more than about 90 px away. The QA gate checks this in Chrome on every keyframe.
- **Captions:** hide the caption while a card shows the same words.
- **Brand:**
  - the brand's display font for numbers and headlines, its text font for labels;
  - the brand's five colours, with the accent reserved for the subject;
  - the brand's texture (if it has one) as metal;
  - real logos only, never redrawn;
  - no emoji: icons are clean vector shapes.
- **Ground:** use `ink` (dark) or `marine` (deep) for data and `bone` (light) for light explainers. A dark ground carries a faint dot grid and, with a texture, a drifting light band. Never put light text on the light ground.
- **HUD frame:** corner brackets, the brand's micro label, the topic tag, and a running timecode with a progress hairline. It makes every graphic feel like part of one system.
- **Sources:** small type at the bottom, and the URL logged in notes.md.

## Checklist before a graphic ships

- [ ] It adds a fact or a picture the words alone don't give.
- [ ] The numbers come from a primary source, checked on the day.
- [ ] Scale is honest: shared baseline, true ratios.
- [ ] The contact sheet (1 fps plus 3 key frames) has been looked at: nothing clipped, crowded or flat.
- [ ] The QA gate passes: layout, caption duplicates, held at least 1 s.
