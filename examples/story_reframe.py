"""Story reframe template: a host telling a story, reframed to vertical, with the evidence cut in."""
import json, os
from studio.short import Builder, render, row
from studio.lib import track_face

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "source/episode.mp4"
WORDS = json.load(open("source/episode.words.json"))
NAME = "The story"
ROWS = [
    row(WORDS, "a columnist says he declined to give the agent access to his texts but it read them anyway"),
    row(WORDS, "it had actually synced his messages database all the way down to row one hundred eighty seven thousand",
        text="it had actually synced his messages database all the way down to row 187,000 ~ ~ ~ ~"),
    row(WORDS, "are these systems being purposely designed to invade your privacy"),
]


def build():
    b = Builder(SRC, WORDS, ROWS, work=os.path.join(HERE, "work"))
    T, i = b.T, lambda r, k=0: ROWS[r]["keep"][0][0] + k
    host = track_face(SRC, WORDS[i(0)]["t0"], WORDS[i(1)]["t0"], 860, 430)    # face centre read off a gridded frame
    b.face(0, 0.75, host)
    b.kit(0.75, T(i(1)), "article", scene="ui", ground="ink", img=os.path.abspath("broll/story/article.png"), wy=220, wh=1040,
          keys=[dict(t=0, x=0, y=420, w=1080)], calls=[dict(k="hl", x=30, y=832, w=840, h=44, t0=0.5, t1=99)], label="THE ARTICLE")
    b.credit(0.75, T(i(1)), "source-site.com")
    b.kit(T(i(1)), T(i(2)), "row", scene="counter", ground="ink", value=187000, prefix="ROW ", t0=0.3, t1=1.6,
          label="of his messages database")
    b.face(T(i(2)), b.total, host, zoom=1.15)
    b.captions()
    b.key(T(i(2)) + 1.0, b.total, "FULL EPISODE ON YOUTUBE")
    return b.done()


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    print(render(build(), f"out/{NAME}.mp4"))
