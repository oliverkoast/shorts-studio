---
name: brand
description: Sets up your look (fonts, colours, logo) once, for every Short. Give it your website or your brand files.
---

# /brand

Brands are plain files in `~/.shorts-studio/brands/<name>/`: `theme.json` (colours, font names, logo, end card text,
frame label), `fonts/`, the logo, an optional texture. A video folder's `shorts-studio.json` names its brand. A
neutral `default` brand ships with the plugin.

Steps:
1. Ask for a source: their website link, or files (fonts as .ttf or .otf, a logo PNG with transparency, colour codes).
2. `studio brand init <name>` (copies the default to start from).
3. Fill it in:
   - **From a website:** open it in a browser tool if one is available (or `studio webshot <url> site.png` and read
     the page source with curl), read the fonts in use (CSS `font-family`) and the main colours (backgrounds, text,
     buttons). Fonts: Google Fonts can be downloaded from `https://github.com/google/fonts` (OFL); for paid fonts,
     ask the user for the files. Logo: their own logo file, never redrawn.
   - `studio brand font <name> display <file.ttf>` and `studio brand font <name> text <file.ttf>` (variable fonts
     become static weights automatically).
   - Edit `theme.json`: `colors.light`, `colors.dark`, `colors.accent` (the one highlight colour), `colors.accent2`,
     `colors.deep`; `logo`; `texture` (optional image); `hud` (the small label in the graphic frame); `endcard`.
4. Preview: `studio brand use <name> <tmp folder>`, then `cd` there and `studio kit gallery preview`. Show the user the
   contact sheets and adjust ("make the accent warmer") before calling it done.
5. In each video folder: `studio brand use <name>` writes `shorts-studio.json`.

Never put brand files inside the plugin folder; they would be lost on update.
