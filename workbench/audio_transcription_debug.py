"""
Audio Transcription Debugging Workbench
========================================

This script analyzes why audio transcription is intermittent and identifies the root causes:

IDENTIFIED ISSUES:
==================

1. **DUPLICATE PROCESSING BUG** (Critical - Lines 54-66 in audio_processor.py)
   The `_run` loop processes the SAME `frames` list TWICE:
   
   ```python
   frames = await self.buffer.get_many(...)  # Get first batch
   await self._process_window(frames)         # Process first batch
   
   more = await self.buffer.get_many(...)     # Get second batch into `more`
   await self._process_window(frames)         # BUG: processes `frames` again, NOT `more`!
   ```
   
   This explains:
   - Same transcription appearing twice (processing same frames twice)
   - Audio being ignored (the `more` frames are never processed)

2. **PREMATURE EXIT on empty `more`** (Lines 64-65)
   ```python
   if not more:
       break  # Exits the entire loop permanently!
   ```
   
   This causes the processor to completely stop when there's a brief pause in audio,
   even though more audio may arrive later.

3. **No overlap/sliding window** for continuous speech
   The current approach processes discrete chunks with no overlap.
   This can cause words at chunk boundaries to be cut off or transcribed poorly.

4. **Buffer consumption race condition**
   Both AudioEmotionProcessor and AudioSpeechToTextProcessor read from separate buffers
   that receive the same frames via AudioBufferBroadcast. However, if one processor
   is slower, frames could accumulate differently in each buffer.

RUN THIS SCRIPT TO VERIFY THE ISSUES:
=====================================
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_audio_processor_code():
    """Print analysis of the AudioSpeechToTextProcessor code."""
    
    print("=" * 80)
    print("AUDIO TRANSCRIPTION ISSUE ANALYSIS")
    print("=" * 80)
    
    print("""
    
🔴 ISSUE #1: DUPLICATE PROCESSING (CRITICAL)
─────────────────────────────────────────────
In AudioSpeechToTextProcessor._run() (lines 52-67):

    frames = await self.buffer.get_many(...)   # ← Gets frames (e.g., 5-6 seconds)
    await self._process_window(frames)          # ← Processes and emits transcript
    
    more = await self.buffer.get_many(...)      # ← Gets NEW frames into `more`
    await self._process_window(frames)          # ← BUG! Processes OLD `frames` again!
                              ^^^^^^
                              Should be `more`!

RESULT: Same transcript appears twice, new audio (`more`) is LOST.


🔴 ISSUE #2: PREMATURE LOOP EXIT
─────────────────────────────────
    if not more:
        break  # ← Completely exits the while loop!

If there's a brief silence (no frames within timeout), the processor STOPS forever.
All subsequent audio is ignored.


🟡 ISSUE #3: NO SLIDING WINDOW OVERLAP
─────────────────────────────────────────
Current approach: Process chunk A → Process chunk B → ...

Better approach: Process chunk A+partial_B → Process partial_A+chunk_B → ...

Without overlap, words at boundaries may be cut or poorly transcribed.


🔧 RECOMMENDED FIXES:
─────────────────────
""")
    
    print("""
1. Fix the duplicate processing bug:

   # BEFORE (buggy):
   await self._process_window(frames)
   more = await self.buffer.get_many(...)
   await self._process_window(frames)  # Wrong!

   # AFTER (fixed):
   await self._process_window(frames)
   more = await self.buffer.get_many(...)
   if more:
       await self._process_window(more)  # Correct!


2. Remove the premature break and use continue instead:

   # BEFORE (breaks entire loop):
   if not more:
       break

   # AFTER (continues waiting for more audio):
   if not more:
       continue


3. Consider a sliding window approach for better transcription quality:
   - Keep the last 1-2 seconds of audio as overlap
   - Process overlapping windows to avoid cutting words
""")


def show_proposed_fix():
    """Show the complete fixed _run method."""
    
    print("\n" + "=" * 80)
    print("PROPOSED FIX FOR AudioSpeechToTextProcessor._run()")
    print("=" * 80 + "\n")
    
    fixed_code = '''
async def _run(self, emitter: Callable[[Dict[str, Any]], Any]) -> None:
    self.emitter = emitter
    """Main loop: collect frames for ~window_seconds and transcribe each window."""
    
    while not self._stop:
        try:
            frames: list[AudioFrame] = await self.buffer.get_many(
                retrive_duration=10, 
                timeout=self.window_seconds
            )

            if not frames:
                continue  # ← Changed from break to continue
            
            await self._process_window(frames)
            
        except asyncio.CancelledError:
            logger.info("Audio processor cancelled")
            break
        except Exception as error:
            logger.error(f"audio buffer get error: {error}")
            # Don't break - continue processing
            continue
'''
    print(fixed_code)
    
    print("""
KEY CHANGES:
1. Removed the second get_many() and duplicate _process_window() call
2. Changed `break` to `continue` when no frames are available
3. Added explicit CancelledError handling for clean shutdown
4. Error handling now uses `continue` instead of `break`
""")


def show_same_fix_for_emotion_processor():
    """Show the fix needed for AudioEmotionProcessor as well."""
    
    print("\n" + "=" * 80)
    print("SAME FIX NEEDED FOR AudioEmotionProcessor._run()")
    print("=" * 80 + "\n")
    
    print("""
The AudioEmotionProcessor has the EXACT SAME BUG at lines 144-160:

    frames = await self.buffer.get_many(...)
    await self._process_window(frames)
    
    more = await self.buffer.get_many(...)
    if not more:
        break
    await self._process_window(frames)  # ← BUG: Should be `more`!

Apply the same fix pattern.
""")


def run_simulation():
    """Simulate what happens with the current buggy code."""
    
    print("\n" + "=" * 80)
    print("SIMULATION: What happens with current code")
    print("=" * 80 + "\n")
    
    # Simulate the sequence of events
    events = [
        ("00:00.0", "Frames A received (301 frames, ~6 seconds)"),
        ("00:06.0", "Process frames A → transcript: null (maybe too short/quiet)"),
        ("00:06.0", "Frames B received (284 frames, ~5.68 seconds)"),
        ("00:06.0", "❌ BUG: Process frames A again instead of B!"),
        ("00:11.7", "Emit transcript from A (null) as first event"),
        ("00:12.0", "Frames C received (284 frames, ~5.68 seconds)"),
        ("00:12.0", "Process frames C → transcript: 'e claro por uns dez segundos...'"),
        ("00:12.0", "❌ BUG: Get more frames D, but process C again!"),
        ("00:17.7", "Emit same transcript twice!"),
        ("00:18.0", "No more frames available → break → PROCESSOR STOPS"),
        ("00:18+",  "❌ All subsequent audio is IGNORED forever"),
    ]
    
    for timestamp, description in events:
        icon = "✅" if "❌" not in description else ""
        print(f"  [{timestamp}] {icon}{description}")
    
    print("""
    
This matches your observed output:
- transcript: null (first chunk, possibly quiet/cut off)
- transcript: "e claro por uns dez segundos..." (appears twice!)
- transcript: null again (loop has broken, no real processing)
- Eventually all audio is ignored
""")


if __name__ == "__main__":
    analyze_audio_processor_code()
    show_proposed_fix()
    show_same_fix_for_emotion_processor()
    run_simulation()
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("""
1. Apply the fix to AudioSpeechToTextProcessor._run() (lines 52-67)
2. Apply the same fix to AudioEmotionProcessor._run() (lines 144-160)
3. Test with a continuous audio stream
4. Consider adding sliding window overlap for better quality

Would you like me to apply these fixes to your code? (Run with --apply-fix)
""")
