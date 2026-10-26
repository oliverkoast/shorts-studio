# Platforms

All three take 1080x1920 at 30 fps, H.264 and AAC, loudness around -14 LUFS. One master works for all of them; the
difference is where their buttons and captions cover the picture.

| | Keep clear (in a 1080x1920 frame) | Captions | Length |
|---|---|---|---|
| YouTube Shorts | bottom ~300 px (title, channel), right ~120 px from y 900 down (buttons) | y 1500 (default) | up to 3 min |
| Instagram Reels | bottom ~320 px, right ~140 px from y 1000 down | y 1500 (default) | up to 3 min |
| TikTok | bottom ~420 px (caption text), right ~140 px from y 800 down | y 1300: `Builder(..., platform="tiktok")` | up to 10 min |

The kit keeps every graphic inside a 60 px safe area and above y 1650; captions sit at y 1500 (y 1300 for TikTok).
If a Short is mainly for TikTok, render it with `platform="tiktok"`.

## Publish copy, per platform

- **YouTube Shorts:** title under 60 characters, written as the hook (no clickbait the Short doesn't pay off); 1 to 2
  sentence description with the full-episode link; 3 hashtags (#Shorts plus two topic tags).
- **TikTok:** a caption of one line that restates the hook, 3 to 5 hashtags; no links (they don't work in captions).
- **Instagram Reels:** a caption of 1 to 3 short lines, the hook first; 3 to 5 hashtags at the end; "link in bio" if
  there is a full episode.
Credit any third-party footage in the description as well as on screen.
