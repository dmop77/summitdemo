import os
import asyncio
import json
import base64
import numpy as np
import sounddevice as sd
import websockets

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")
SAMPLE_RATE = 24000  # alloy voice uses 24kHz mono PCM16


async def run_realtime_test():
    if not OPENAI_API_KEY:
        raise RuntimeError("Set OPENAI_API_KEY in your environment")

    url = f"wss://api.openai.com/v1/realtime?model={MODEL}"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    async with websockets.connect(url, extra_headers=headers, max_size=None) as ws:
        # Configure session for audio in/out
        await ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "voice": "alloy",
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                    },
                }
            )
        )

        # Request an audio response
        await ws.send(
            json.dumps(
                {
                    "type": "response.create",
                    "response": {
                        "modalities": ["audio"],
                        "instructions": "Hello! This is a realtime audio test from Python.",
                    },
                }
            )
        )

        # Stream PCM16 audio to default audio output
        with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue

                mtype = msg.get("type")

                if mtype in ("response.audio.delta", "output_audio.delta"):
                    data_b64 = msg.get("audio")
                    if not data_b64:
                        continue
                    pcm_bytes = base64.b64decode(data_b64)
                    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
                    stream.write(samples)

                if mtype in ("response.completed", "response.finished", "output_audio.done"):
                    break

                if mtype in ("error", "rate_limit_exceeded"):
                    print("Realtime error:", msg)
                    break


if __name__ == "__main__":
    asyncio.run(run_realtime_test())


