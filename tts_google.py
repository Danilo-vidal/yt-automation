import asyncio
import edge_tts

def gerar_audio_google(texto, output_path):
    async def run():
        communicate = edge_tts.Communicate(
            texto,
            voice="pt-BR-AntonioNeural"
        )
        await communicate.save(output_path)

    asyncio.run(run())
    print("[OK] Áudio gerado com Edge TTS")