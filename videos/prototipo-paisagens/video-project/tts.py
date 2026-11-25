import certifi, asyncio
certifi.where = lambda: "/root/.ccr/ca-bundle.crt"
import edge_tts
V = {"M": "pt-BR-AntonioNeural", "F": "pt-BR-FranciscaNeural"}
async def main():
    for i, line in enumerate(open("lines.tsv").read().strip().split("\n")):
        who, text, _ = line.split("\t")
        await edge_tts.Communicate(text, V[who]).save(f"assets/l{i}_{who}.mp3")
asyncio.run(main())
