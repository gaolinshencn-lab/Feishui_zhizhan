"""Float32 WAV files as memory maps, so half-hour stems never have to sit in memory at once."""
import struct
import numpy as np
from scipy.io import wavfile


def create(path, frames, channels, sr):
    """A float32 WAV of the given length, zero-filled, returned as a writable (frames, channels) memmap."""
    data_bytes = frames * channels * 4
    hdr = b'RIFF' + struct.pack('<I', 36 + data_bytes) + b'WAVE' + b'fmt ' + struct.pack('<IHHIIHH', 16, 3, channels, sr, sr * channels * 4, channels * 4, 32) \
        + b'data' + struct.pack('<I', data_bytes)
    with open(path, 'wb') as f:
        f.write(hdr)
        f.truncate(44 + data_bytes)
    return np.memmap(path, dtype=np.float32, mode='r+', offset=44, shape=(frames, channels))


def read(path):
    """(sample rate, array) with the samples memory-mapped where the format allows; ints scaled to [-1, 1)."""
    sr, x = wavfile.read(path, mmap=True)
    if x.dtype == np.int16:
        return sr, x, 1 / 32768.0
    if x.dtype == np.int32:
        return sr, x, 1 / 2147483648.0
    return sr, x, 1.0
