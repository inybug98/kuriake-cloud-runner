"""
Video & Audio Integrity Gatekeeper
==================================
Performs strict pre-flight checks on media files before uploading to YouTube:
1. Detects dead silence / missing preacher audio using FFmpeg volumedetect.
2. Checks minimum duration.
3. Checks audio stream presence.
Prevents empty, silent, or corrupt files from ever being published.
"""

import subprocess
import os
import re

def check_media_integrity(file_path, min_duration_sec=30):
    if not os.path.exists(file_path):
        return False, f"File does not exist: {file_path}"

    size_bytes = os.path.getsize(file_path)
    if size_bytes < 100000: # < 100KB
        return False, f"File is too small ({size_bytes} bytes), likely a placeholder or corrupted."

    # 1. Run FFmpeg volumedetect to inspect audio levels
    cmd = [
        "ffmpeg", "-i", file_path,
        "-af", "volumedetect",
        "-f", "null", "-"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = res.stderr

        # Extract mean volume
        mean_match = re.search(r"mean_volume:\s*(-?[\d\.]+)\s*dB", output)
        max_match = re.search(r"max_volume:\s*(-?[\d\.]+)\s*dB", output)

        if not mean_match:
            return False, "No audio stream found in the video file."

        mean_db = float(mean_match.group(1))
        max_db = float(max_match.group(1))

        # Silence threshold: Anything below -55dB is dead silence / anullsrc
        if mean_db < -55.0 and max_db < -50.0:
            return False, f"HARD REJECT: Video audio is silent (Mean: {mean_db} dB, Max: {max_db} dB). Missing preacher voice."

        # Duration check
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):([\d\.]+)", output)
        if dur_match:
            hours = int(dur_match.group(1))
            minutes = int(dur_match.group(2))
            seconds = float(dur_match.group(3))
            total_sec = hours * 3600 + minutes * 60 + seconds

            if total_sec < min_duration_sec:
                return False, f"Duration is too short ({total_sec:.1f}s < {min_duration_sec}s target). Incomplete compilation."

        return True, f"PASSED: Audible speech verified (Mean: {mean_db} dB, Max: {max_db} dB)."

    except Exception as e:
        return False, f"Media inspection error: {e}"

if __name__ == "__main__":
    # Test on the dummy 11-second silent clip
    test_clip = r"assets\test_production_clip.mp4"
    valid, reason = check_media_integrity(test_clip, min_duration_sec=15)
    print("Test Clip Check:")
    print("  Valid:", valid)
    print("  Reason:", reason)
