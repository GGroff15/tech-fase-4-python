r"""Performance test: simulate concurrent streams running the frame pipeline.

This script runs N concurrent "streams" where each stream processes M frames
through the decode -> validate/resize -> infer pipeline. It forces the
Roboflow client to use the lightweight mock path (no local Ultralytics load)
by setting `ROBOFLOW_USE_LOCAL_FALLBACK=false` in the environment.

Run with the project's virtualenv to ensure correct deps. Example:

    & .venv\Scripts\python.exe tests/perf/run_concurrent_streams.py

This prints p50/p95 latency and throughput per simulated stream.
"""
import sys
import pathlib
# ensure repo root is first on sys.path so local packages import correctly
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import asyncio
import os
import time
from statistics import median, quantiles

import numpy as np

from preprocessing.resizer import resize_to_720p
from preprocessing.validator import validate_resolution
from inference.roboflow_client import infer_image


async def process_single_frame(img: np.ndarray) -> float:
    start = time.perf_counter()
    # validate/resize
    if not validate_resolution(img):
        img = resize_to_720p(img)
    # inference (uses mock if env disables local fallback)
    preds = infer_image(img)
    if hasattr(preds, "__await__"):
        await preds
    dur = (time.perf_counter() - start) * 1000.0
    return dur


async def run_stream(stream_id: int, frames: int, latencies: list):
    # create a small test image >50px width to trigger mock detection
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    for i in range(frames):
        dur = await process_single_frame(img)
        latencies.append(dur)


async def run_concurrent(streams: int = 5, frames_per_stream: int = 20):
    # Force mock path to avoid loading local YOLO during perf runs
    os.environ["ROBOFLOW_MODEL_URL"] = ""
    os.environ["ROBOFLOW_API_KEY"] = ""
    os.environ["ROBOFLOW_USE_LOCAL_FALLBACK"] = "false"

    tasks = []
    all_latencies = []
    for s in range(streams):
        lat = []
        all_latencies.append(lat)
        tasks.append(run_stream(s, frames_per_stream, lat))

    t0 = time.perf_counter()
    await asyncio.gather(*tasks)
    total_ms = (time.perf_counter() - t0) * 1000.0

    # flatten
    flat = [v for sub in all_latencies for v in sub]
    flat.sort()

    def pctile(p):
        if not flat:
            return 0.0
        # p in [0,100]
        if p == 50:
            return median(flat)
        q = quantiles(flat, n=100)[int(p) - 1]
        return q

    print(f"Streams: {streams}, frames/stream: {frames_per_stream}")
    print(f"Total frames: {len(flat)}, total_time_ms: {total_ms:.1f}")
    print(f"Throughput fps (approx): {len(flat) / (total_ms/1000.0):.1f}")
    print(f"p50 latency ms: {pctile(50):.1f}")
    print(f"p95 latency ms: {pctile(95):.1f}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--streams", type=int, default=5)
    parser.add_argument("-f", "--frames", type=int, default=20)
    args = parser.parse_args()

    asyncio.run(run_concurrent(streams=args.streams, frames_per_stream=args.frames))
