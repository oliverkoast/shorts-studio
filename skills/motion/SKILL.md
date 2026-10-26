---
name: motion
description: Adds animated graphics in your brand, timed to the spoken word. Give it the claim, number or idea to show.
---

# /motion

The graphics kit renders every scene in the user's brand (`/brand`). The rules and the "which graphic for which
claim" table are in docs/motion-graphics.md (plugin root is two folders up). Preview any scene on its own with
`studio kit scene.json out.mp4` (prints a contact sheet and a layout check), or every scene with
`studio kit gallery <dir>`.

In a spec: `b.kit(t0, t1, "<name>", scene="...", ...)`. Times inside a scene are seconds from its own start; cue
them to words with `b.T(i) - t0`.

| scene | parameters | use it for |
|---|---|---|
| `counter` | value, decimals, prefix, suffix, label, t0, t1, sub2, compare={a:{label,v,t}, b:{...}} | one big number, or a number against a rival |
| `keyword` | lines=[[text, t], ...], sub | a phrase or name that needs to land; jargon |
| `versus` | title, a={value,label,t,w}, b={...} | before/after, A vs B (shown in sequence) |
| `height` | items=[{label, h, w, t, kind:"statue"?, accent}], counter={value,suffix,sub}, source | "the biggest": to scale on one ground line |
| `timeline` | title, items=[{t, date, text}] | dates and sequences |
| `quote` | text, size, name, role, avatar, logo, t0 | a line someone said |
| `diagram` | title, nodes=[{id,label,x,y,t,accent}], edges=[{from,to,t}] | how something works |
| `moneyflow` | logo, title, left, right, lockLabel, t0, tLink, tLock, tFlow, risk, tRisk | money, data or access moving between two parties |
| `ui` | img, keys=[{t,x,y,w,ease}], calls=[{k:"hl"\|"circle"\|"arrow", x,y,w,h,t0,t1,ang}], label, labelT | a real page with highlights |
| `logo` | logo, title, sub, metal, t0 | end cards and product reveals |

Grounds: `ink` (dark), `marine` (deep colour), `bronze` (texture or accent), `bone` (light). Every scene keeps text
inside a 60 px safe area and shrinks text to fit; the QA gate checks it. After rendering, look at the contact sheet:
fix anything flat, crowded or clipped. Numbers come from a primary source, checked the same day.
