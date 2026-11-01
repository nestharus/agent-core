"""Capture a bounded opaque output prefix and drain the child's remaining output."""
import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--max-bytes', required=True, type=int)
    options = parser.parse_args()
    if options.max_bytes <= 0:
        parser.error('--max-bytes must be positive')
    seen = captured = 0
    failure = None
    mirror_open = True
    descriptor = None
    try:
        descriptor = os.open(options.log, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
    except OSError as error:
        failure = error.errno
    try:
        while True:
            chunk = os.read(0, 65536)
            if not chunk:
                break
            seen += len(chunk)
            prefix = chunk[:max(0, options.max_bytes - captured)] if failure is None else b''
            written = 0
            while written < len(prefix):
                try:
                    count = os.write(descriptor, prefix[written:])
                    if count == 0:
                        raise OSError(5, 'zero-byte log write')
                    written += count
                    captured += count
                except OSError as error:
                    failure = error.errno
                    break
            if written and mirror_open:
                try:
                    sys.stdout.buffer.write(prefix[:written])
                    sys.stdout.buffer.flush()
                except OSError:
                    mirror_open = False
        if descriptor is not None:
            try:
                os.fsync(descriptor)
            except OSError as error:
                failure = error.errno
    finally:
        if descriptor is not None:
            os.close(descriptor)
    summary = {
        'max_bytes': options.max_bytes,
        'seen_bytes': seen,
        'captured_bytes': captured,
        'dropped_bytes': seen - captured,
        'complete': failure is None and captured == seen,
        'io_error_number': failure,
        'raw_output_decoded': False,
    }
    with open(options.summary, 'x', encoding='utf-8') as stream:
        json.dump(summary, stream, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    if not summary['complete'] and mirror_open:
        try:
            sys.stdout.buffer.write(b'\nDIRECT_CODEX_LOG_INCOMPLETE: see capture.json\n')
            sys.stdout.buffer.flush()
        except OSError:
            pass
    return 1 if failure is not None else (0 if summary['complete'] else 3)


if __name__ == '__main__':
    raise SystemExit(main())
