# tech_challange_fase4# Tech Challenge – Fase 4
## Análise Multimodal para Saúde da Mulher

Este repositório apresenta uma prova de conceito funcional de um sistema multimodal para análise de vídeo e áudio, desenvolvido conforme os requisitos do Tech Challenge – Fase 4.

## Objetivos

## Estrutura do Projeto
challenge/
├── sample_video.mp4
├── sample_audio.wav
├── main.py
├── video/
├── audio/
├── alerts/
└── venv/

## Tecnologias

## Execução
Certifique-se de que os arquivos sample_video.mp4 e sample_audio.wav estejam na raiz do projeto.

python main.py

## Observação
Os dados utilizados são sintéticos, empregados exclusivamente para validação acadêmica do pipeline.

## WebSocket Realtime API

Endpoint: `ws://<host>:<port>/ws/analyze`

Protocol summary:
- Client connects via WebSocket and optionally supplies `?token=<API_KEY>` as a query parameter.
- Client sends binary messages containing a JPEG or PNG encoded frame.
- Server responds with JSON messages describing detections or errors.

Message types sent by the server:
- `session_started`: initial message containing `session_id` and config.
- `detection_result`: per-frame detection with fields: `session_id`, `frame_index`, `timestamp_ms`, `has_wounds`, `wounds` (array), `metadata` (processing_time_ms, frames_dropped_since_last).
- `error`: error events describing validation or inference failures.
- `idle_timeout`: sent when no frames are received within idle timeout and connection closed.
- `stream_closed`: final summary containing totals and duration.

Example client (Python) — send a single JPEG frame and receive a result:

```python
import asyncio
import websockets

async def send_frame(jpeg_path):
	uri = "ws://localhost:8000/ws/analyze?token=YOUR_API_KEY"
	async with websockets.connect(uri) as ws:
		# receive session_started (if implemented)
		msg = await ws.recv()
		print("server:", msg)

		with open(jpeg_path, 'rb') as f:
			data = f.read()
		await ws.send(data)

		# receive detection_result
		resp = await ws.recv()
		print("result:", resp)

		await ws.close()

asyncio.run(send_frame('sample.jpg'))
```

Command-line example using `wscat`:

```bash
wscat -c ws://localhost:8000/ws/analyze
# binary frames can be sent using tools that support WebSocket binary send
```

See `specs/001-realtime-wound-detection/contracts/websocket-api.md` for full message contract and examples.
