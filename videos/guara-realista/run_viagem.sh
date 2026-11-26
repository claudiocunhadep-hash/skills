cd "$(dirname "$0")"
SHOT=1 python3 guara_viagem.py v1 0 104 576 1024 16 > v1.log 2>&1
SHOT=2 python3 guara_viagem.py v2 0 89 576 1024 16 > v2.log 2>&1
SHOT=3 python3 guara_viagem.py v3 0 590 576 1024 16 > v3.log 2>&1
echo FIM $(ls v1 | wc -l) $(ls v2 | wc -l) $(ls v3 | wc -l)
