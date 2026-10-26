---
name: short
description: Makes Shorts from any long video, picking the best of the four types for you. Give it a video file or link.
---

# /short: pick the type, then make the Short

Look at what the user gave you and route to one of the four types. Each type has its own skill with the details.

| What they have | Type | Skill |
|---|---|---|
| Their own screen recording (often with their camera) | Screen demo | `/screen-demo` |
| Someone else's interview, keynote or talk, where the subject needs showing | Interview split | `/interview-split` |
| A podcast or news segment where a host tells a story | Story reframe | `/story-reframe` |
| One strong 30 to 45 s answer or opinion from a guest | Quick clip | `/quick-clip` |

If they asked for several Shorts from one video, find the best moments first (read the transcript, see
docs/workflow.md step 3), list them with a one-line hook and a type each, and make the ones they pick.

Before anything else: if `~/.shorts-studio/bin/studio` does not exist, run `/shorts-setup`.
Then follow the chosen type's skill and docs/workflow.md (paths are relative to this plugin's root, two folders up
from this skill).
