"""Interview split template: someone else's interview, the subject on top, the speaker below, captions on the divider.
Not your footage? Keep "(PRIVATE - not for posting)" in the name unless you have the rights."""
import json, os
from studio.short import Builder, render, row

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "source/interview.mp4"
WORDS = json.load(open("source/interview.words.json"))
NAME = "Interview moment (PRIVATE - not for posting)"
ROWS = [
    row(WORDS, "we've got starship which is the largest most powerful flying object ever made"),
    row(WORDS, "and we intend to launch that more than once per hour"),
]
# the source's own camera cuts (seconds) and the x centre of whoever is speaking in each shot
CUTS = [(0.0, 660), (19.24, 1500), (27.76, 870)]


def build():
    b = Builder(SRC, WORDS, ROWS, layout="split", work=os.path.join(HERE, "work"))
    T, i = b.T, lambda r, k=0: ROWS[r]["keep"][0][0] + k
    # bottom: the interview, cut where the source cuts
    marks = [(b.at_source(s) or 0.0, cx) for s, cx in CUTS]
    for k, (t, cx) in enumerate(marks):
        t1 = marks[k + 1][0] if k + 1 < len(marks) else b.total
        b.frame(t, t1, crop=(int(min(max(cx - 607, 0), 705)), 0, 1215, 1080), panel="bottom")
    # top: official footage, then the facts the claim implies
    b.footage(0, T(i(0, 5)), "broll/starship/flight.mp4", at=26.5, credit="Video: SpaceX", crop=(152, 0, 1215, 1080), panel="top")
    b.kit(T(i(0, 5)), T(i(1)), "height", panel="top", scene="height", ground="ink", ground_y=1150, top_y=560,
          items=[dict(label="STATUE OF LIBERTY", h=93, kind="statue", w=12, t=0.05), dict(label="SATURN V", h=110.6, w=10, t=0.2),
                 dict(label="STARSHIP", h=124, w=9, t=0.4, accent=True)], counter=dict(value=124, suffix=" m", sub="407 ft"))
    b.credit(T(i(0, 5)), T(i(1)), "Source: SpaceX, NASA", panel="top")
    b.kit(T(i(1)), b.total, "hourly", panel="top", scene="keyword", ground="ink", lines=[["LAUNCH IT", 0.05], ["ONCE PER HOUR", 1.0]])
    b.credit(0, b.total, "Video: <the interview's owner>", panel="bottom")
    b.captions()
    return b.done()


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    print(render(build(), f"out/{NAME}.mp4"))
