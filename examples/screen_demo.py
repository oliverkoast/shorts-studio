"""Screen demo template: your own screen recording, your face in a bubble, the product as the star.
Copy to shorts/<name>/spec.py in your video folder, fill in the paths, phrases and crops, then:
    studio render shorts/<name>/spec.py      and      studio qa shorts/<name>/spec.py "out/<name>.mp4"
"""
import json, os, sys
from studio.short import Builder, render, row
from studio.lib import track_face

HERE = os.path.dirname(os.path.abspath(__file__))
SCREEN = "source/demo.mp4"                 # the screen recording (its audio is your voice)
CAMERA = "source/demo camera.mp4"          # your camera, if it is a separate file (else None)
CAM_OFFSET = 1.60                          # camera time minus screen time (match the two audio tracks)
WORDS = json.load(open("source/demo.words.json"))
NAME = "My product demo"

ROWS = [
    row(WORDS, "the biggest launch this week was definitely dashboards"),
    row(WORDS, "you connect the data source and it builds a dashboard that queries it live"),
    row(WORDS, "and here you can see it built exactly what i wanted"),
    row(WORDS, "to me this is a startup killer product"),
]
FULL = (1040, -420, 2396)                  # (x, y, width) of the screen to show, in screen pixels: the whole app
RESULT = (2236, 760, 1200)                 # a punch-in on the result, about once per section


def build():
    b = Builder(SCREEN, WORDS, ROWS, work=os.path.join(HERE, "work"))
    T, i = b.T, lambda r: ROWS[r]["keep"][0][0]
    if CAMERA:
        b.camera(CAMERA, offset=CAM_OFFSET, window_x=950, window_w=864)
    b.cam_window(0, 0.75)                                                    # a 0.75 s face beat, then the subject
    b.screen(0.75, T(i(1)), keys=[(0.75, FULL)], bubble=(630, 110, 640))
    b.kit(T(i(1)), T(i(2)), "how", scene="diagram", ground="ink", title="HOW IT WORKS",
          nodes=[dict(id="a", label="DATA SOURCE", x=540, y=620, t=0.05), dict(id="b", label="THE MODEL", x=540, y=950, t=0.8, accent=True),
                 dict(id="c", label="LIVE DASHBOARD", x=540, y=1280, t=1.5)],
          edges=[{"from": "a", "to": "b", "t": 0.6}, {"from": "b", "to": "c", "t": 1.3}])
    b.screen(T(i(2)), T(i(3)), keys=[(T(i(2)), FULL), (T(i(2)) + 1.5, RESULT)], bubble=(630, 110, 640))
    b.cam_window(T(i(3)), b.total)                                           # the opinion and the ending on your face
    b.captions()
    b.key(T(i(3)) + 1.0, b.total, "FULL DEMO ON YOUTUBE")
    return b.done()


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    print(render(build(), f"out/{NAME}.mp4"))
