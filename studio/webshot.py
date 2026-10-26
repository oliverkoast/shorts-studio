"""Re-render a live web page at 2x for b-roll.  studio webshot <url> <out.png> [--width 540|1280]

Check the result before using it: a "verify you are human" or cookie wall is not b-roll."""
import sys
from .lib import webshot

if __name__ == "__main__":
    a = sys.argv[1:]
    w = int(a[a.index("--width") + 1]) if "--width" in a else 540
    print(webshot(a[0], a[1], w, 960 if w <= 600 else 900, 2, True, 5.0))
