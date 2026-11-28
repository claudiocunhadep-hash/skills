cd "$(dirname "$0")"
sleep 20; while pgrep -f "guara_viagem.py v_teste" >/dev/null; do sleep 10; done
ffmpeg -v error -y -stream_loop 3 -i ../amb.wav -t 7.49 -ar 48000 amb.wav
printf '1\n00:00:01,000 --> 00:00:02,890\nIgualzinho às águas do nosso mangue!\n\n2\n00:00:03,380 --> 00:00:05,690\nConcordo! Mar calmo é com a gente mesmo!\n' > t.srt
ffmpeg -v error -y -framerate 30 -i ../v_teste/%04d.png -i amb.wav -i m2.mp3 -i f2.mp3 -filter_complex "[0]scale=1080:1920:flags=lanczos,format=yuv420p,subtitles=t.srt:force_style='FontName=DejaVu Sans,Fontsize=10,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00202020,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=24'[v];[1]volume=0.35[a];[2]adelay=837|837,volume=1.6[m];[3]adelay=3217|3217,volume=1.6[f];[a][m][f]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5,aresample=48000[o]" -map "[v]" -map "[o]" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart teste-olhos-camera.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 teste-olhos-camera.mp4
