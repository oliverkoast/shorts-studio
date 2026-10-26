"""Quick clip, ready to run on the sample talk (bash make_sample.sh sample, then run this from the sample folder):
    studio render <plugin>/examples/quick_clip.py        studio qa <plugin>/examples/quick_clip.py "out/Editing is a conversation.mp4"
Copy it to shorts/<name>/spec.py and change SRC, the phrases and the face position for your own video."""
import json, os
from studio.short import Builder, render, row, find
from studio.lib import track_face

SRC = os.path.abspath("talk.mp4")
WORDS = json.load(open("talk.words.json"))
NAME = "Editing is a conversation"
WORK = os.path.abspath("work/quick-clip")

ROWS = [
    row(WORDS, "most people think editing takes hours"),
    row(WORDS, "it really doesn't have to"),
    row(WORDS, "last week i gave claude a forty minute recording and asked it for three shorts",
        text="last week I gave Claude a forty minute recording and asked it for three Shorts."),
    row(WORDS, "it found the best moments cut them on real words added captions"),
    row(WORDS, "and when i said there was a noise at seven seconds it found the cause",
        text="and when I said there was a noise at seven seconds, it found the cause."),
    row(WORDS, "it was half of a word i had cut", text="It was half of a word I had cut."),
    row(WORDS, "so it fixed the rule not just the clip", text="So it fixed the rule, not just the clip."),
    row(WORDS, "before i see anything it runs thirteen checks noises at cuts text running off the screen a weak ending",
        text="before I see anything, it runs thirteen checks. Noises at cuts, text running off the screen, a weak ending."),
    row(WORDS, "i used to spend a whole afternoon on one short now i give notes the way i would to an editor",
        text="I used to spend a whole afternoon on one Short. Now I give notes, the way I would to an editor."),
    row(WORDS, "editing is becoming a conversation", text="Editing is becoming a conversation."),
]
KEYWORDS = ["THIRTEEN", "AFTERNOON", "EDITOR", "HOURS", "CLAUDE", "FORTY", "MINUTE", "THREE", "SHORTS", "NOISE", "SEVEN", "SECONDS", "RULE", "CONVERSATION"]


def build():
    b = Builder(SRC, WORDS, ROWS, maxgap=0.10, pad=0.05, tail=0.04, work=WORK)
    T = b.T
    first = lambda r: ROWS[r]["keep"][0][0]
    face = track_face(SRC, 0.0, WORDS[-1]["t1"], 960, 430)               # the presenter's face centre (from a gridded frame)
    b.punch(0, T(first(2)), face)
    b.kit(T(first(2)), T(first(3)), "forty", scene="counter", ground="ink", value=40, suffix=" MIN", t0=0.1, t1=1.2,
          label="of recording in, three Shorts out")
    b.kit(T(first(3)), T(first(4)), "how", scene="diagram", ground="ink", title="WHAT IT DID",
          nodes=[dict(id="a", label="BEST MOMENTS", x=540, y=620, t=0.05), dict(id="b", label="CUT ON WORDS", x=540, y=950, t=0.9, accent=True),
                 dict(id="c", label="CAPTIONS", x=540, y=1280, t=1.8)],
          edges=[{"from": "a", "to": "b", "t": 0.7}, {"from": "b", "to": "c", "t": 1.6}])
    b.punch(T(first(4)), T(first(6)), face)
    b.kit(T(first(6)), T(first(7)), "rule", scene="keyword", ground="marine", lines=[["THE RULE,", 0.1], ["NOT THE CLIP", 0.6]])
    b.punch(T(first(7)), T(first(7)) + 2.2, face)
    b.kit(T(first(7)) + 2.2, T(first(8)), "checks", scene="counter", ground="ink", value=13, suffix=" CHECKS", t0=0.1, t1=1.0,
          label="before anyone sees the Short")
    b.punch(T(first(8)), b.total, face)
    b.captions(style="pop", keywords=KEYWORDS)
    b.endcard(2.4)
    return b.done()


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    print(render(build(), f"out/{NAME}.mp4"))
