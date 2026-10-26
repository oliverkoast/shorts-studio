#!/usr/bin/env bash
# Makes a 1920x1080 sample "talk" we own outright (macOS speech + a drawn presenter), for trying the plugin.
#   bash make_sample.sh <out folder>
set -e
OUT="${1:-sample}"; mkdir -p "$OUT"; cd "$OUT"
TEXT="So here's the thing about short videos. Um, most people think editing takes hours. It really doesn't have to.
Last week I gave Claude a forty minute recording and asked it for three Shorts. It found the best moments, cut them on real words,
added captions, and pulled in b-roll from official sources. And when I said there was a noise at seven seconds, it found the cause.
It was half of a word I had cut. So it fixed the rule, not just the clip. The whole thing cost me nothing extra.
That's the part that surprised me most. Here's how it works. First it listens to every word, including the restarts.
Then it picks one continuous stretch of real talk, and cuts at the quiet moments between words, so nothing sounds choppy.
For every sentence it finds a visual. The real product page, the company's own footage, or a graphic with the actual numbers.
And before I see anything, it runs thirteen checks. Noises at cuts, text running off the screen, a weak ending.
I used to spend a whole afternoon on one Short. Now I give notes, the way I would to an editor.
Editing is becoming a conversation."
if command -v say >/dev/null; then say -v Samantha -r 175 -o voice.aiff "$TEXT"; ffmpeg -v error -y -i voice.aiff -ar 48000 -ac 2 voice.wav
else espeak-ng -s 160 -w voice.wav "$TEXT"; fi
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 voice.wav)
# a presenter: a head and shoulders that sway a little, on a studio-grey background, with a slow camera drift
ffmpeg -v error -y -f lavfi -i "color=c=0x2B3038:s=1920x1080:r=30:d=$D" -i voice.wav -filter_complex \
"[0:v]drawbox=x=0:y=820:w=1920:h=260:color=0x22262C:t=fill,\
geq=r='if(lt(hypot(X-960-20*sin(T*0.7),Y-430),150),232,if(lt(hypot((X-960-20*sin(T*0.7))*0.55,Y-900),220),70,r(X,Y)))':\
g='if(lt(hypot(X-960-20*sin(T*0.7),Y-430),150),190,if(lt(hypot((X-960-20*sin(T*0.7))*0.55,Y-900),220),90,g(X,Y)))':\
b='if(lt(hypot(X-960-20*sin(T*0.7),Y-430),150),160,if(lt(hypot((X-960-20*sin(T*0.7))*0.55,Y-900),220),130,b(X,Y)))'[v]" \
-map "[v]" -map 1:a -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest talk.mp4
rm -f voice.aiff voice.wav
echo "$OUT/talk.mp4 ($D s)"
