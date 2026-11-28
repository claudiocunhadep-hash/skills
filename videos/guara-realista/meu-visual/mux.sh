cd "$(dirname "$0")"
sleep 30; while pgrep -f "guara_viagem.py v_visual" >/dev/null; do sleep 15; done
ffmpeg -v error -y -stream_loop 3 -i ../amb.wav -t 7.65 -ar 48000 amb.wav
printf '1\n00:00:00,950 --> 00:00:03,300\nPessoal, dá uma olhada no meu visual!\n\n2\n00:00:03,300 --> 00:00:06,450\nVê se você aprova, se melhorou ou não!\n' > v.srt
ffmpeg -v error -y -framerate 30 -i ../v_visual/%04d.png -i amb.wav -i m1.mp3 -filter_complex "[0]scale=1080:1920:flags=lanczos,format=yuv420p,subtitles=v.srt:force_style='FontName=DejaVu Sans,Fontsize=10,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00202020,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=24'[v];[1]volume=0.35[a];[2]adelay=821|821,volume=1.6[m];[a][m]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5,aresample=48000[o]" -map "[v]" -map "[o]" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart guara-meu-visual.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 guara-meu-visual.mp4
