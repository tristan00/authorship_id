import zstandard

from .config import MAX_WINDOW_SIZE, READ_SIZE


def produce(path, full, free):
    try:
        with open(path, "rb") as fh:
            expected = zstandard.frame_content_size(fh.read(18))
            fh.seek(0)
            with zstandard.ZstdDecompressor(max_window_size=MAX_WINDOW_SIZE).stream_reader(fh, read_size=READ_SIZE) as reader:
                tail = b""
                decompressed = 0
                while True:
                    buf = free.get()
                    if len(buf) < 2 * len(tail):
                        buf.extend(bytes(2 * len(tail)))
                    buf[:len(tail)] = tail
                    size = reader.readinto(memoryview(buf)[len(tail):])
                    if not size:
                        break
                    decompressed += size
                    size += len(tail)
                    end = buf.rfind(b"\n", 0, size) + 1
                    tail = bytes(buf[end:size])
                    full.put((buf, end, decompressed, fh.tell()))
                if expected != -1 and decompressed != expected:
                    raise ValueError(f"{path} decompressed to {decompressed} bytes, frame header says {expected}")
                if tail:
                    full.put((bytearray(tail + b"\n"), len(tail) + 1, decompressed, fh.tell()))
        full.put(None)
    except BaseException as error:
        full.put(error)
