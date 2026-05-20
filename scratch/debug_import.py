import sys
import os

print("Importing nemo...")
import nemo
print("Importing nemo.collections...")
import nemo.collections
print("Importing nemo.collections.asr...")
try:
    import nemo.collections.asr
    print("Success!")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
except BaseException as e:
    print(f"FAILED (BaseException): {e}")
    import traceback
    traceback.print_exc()
