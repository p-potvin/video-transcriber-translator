import time
import os
import sys
import traceback

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def profile_load():
    try:
        from vaultwares_media_processing.parakeet_wrapper import ParakeetTranscriber
        print("--- Starting VRAM Load Profile ---")
        start_total = time.time()
        
        print("Step 1: Initializing ParakeetTranscriber...")
        s1 = time.time()
        # ParakeetTranscriber constructor does the heavy lifting
        transcriber = ParakeetTranscriber()
        e1 = time.time()
        print(f"ParakeetTranscriber initialized in {e1 - s1:.2f}s")
        
        print("\n--- Summary ---")
        print(f"Total load time: {time.time() - start_total:.2f}s")
    except Exception as e:
        print("\n!!! ERROR DURING PROFILE !!!")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    profile_load()
