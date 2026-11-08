#!/usr/bin/env python3
"""Chata benchmark helper for the Steam Deck.

Launches the AppImage with the trace variables on, waits until you close the emulator, then
writes one summary file (FPS, GPU time, slowest items, thread waits) plus the raw trace lines
to ~/chata-bench/. Send the summary file back instead of running grep by hand.

    python3 bench.py --label baseline
    python3 bench.py --label writer-wait --env EDEN_NX2_DMA_WRITER_WAIT=1
    python3 bench.py --analyze ~/.local/share/eden/log/eden_log.txt --label old-run

Play the same scene each time (Kokiri Forest idle). --skip drops the first seconds of the run.
"""
import argparse
import datetime
import glob
import os
import re
import statistics
import subprocess
import sys
from collections import defaultdict

LOG = os.path.expanduser("~/.local/share/eden/log/eden_log.txt")
OUT_DIR = os.path.expanduser("~/chata-bench")
TRACE_ENV = {
    "EDEN_DKB_FRAME_TRACE": "1",
    "EDEN_NX2_GPU_PROFILE": "1",
    "EDEN_NX2_COPY_TRACE": "1",
}
STAMP = re.compile(r"^\[\s*([0-9.]+)\]")
PIECE = re.compile(r"^([A-Za-z][A-Za-z0-9 ]*?) ([0-9]+(?:\.[0-9]+)?) ms \((\d+)/s\)$")
HASHED = re.compile(r"(s6:[0-9a-f]{16}|s1:[0-9a-f]{16}\+s5:[0-9a-f]{16})=([0-9.]+)ms")


def number(line, name):
    match = re.search(rf"\b{name}=(-?[0-9]+(?:\.[0-9]+)?)", line)
    return float(match.group(1)) if match else None


def find_appimage():
    names = ("chata-linux-x86_64.AppImage", "Chata*.AppImage", "chata*.AppImage")
    for folder in (os.getcwd(), "~/Applications", "~/Downloads", "~"):
        for name in names:
            hits = sorted(glob.glob(os.path.join(os.path.expanduser(folder), name)))
            if hits:
                return hits[-1]
    return None


def zone_pieces(line, marker):
    body = line.split(marker, 1)[1]
    body = body.replace("waits for the back by site:", "|")
    for piece in re.split(r"[|,]", body):
        match = PIECE.match(piece.strip())
        if match:
            yield match.group(1), float(match.group(2)), int(match.group(3))


def summarize(lines, skip):
    stamps = [(float(m.group(1)), line) for line in lines if (m := STAMP.match(line))]
    renderer = [(t, line) for t, line in stamps if "DKB renderer" in line]
    t0 = renderer[0][0] if renderer else (stamps[0][0] if stamps else 0.0)
    keep = [(t, line) for t, line in stamps if t >= t0 + skip]
    out = []

    frame_ms = [v for t, line in keep if "DKB renderer" in line
                if (v := number(line, "cpu_frame_wall_ms")) and v > 0]
    out.append(f"== Frame rate (1 sample per second, first {skip:g}s skipped)")
    if frame_ms:
        fps = sorted(1000.0 / v for v in frame_ms)
        out.append(f"samples={len(fps)} fps avg={statistics.mean(fps):.1f} "
                   f"median={statistics.median(fps):.1f} min={fps[0]:.1f} max={fps[-1]:.1f} "
                   f"p10={fps[len(fps) // 10]:.1f}")
        out.append(f"frame_ms avg={statistics.mean(frame_ms):.1f} "
                   f"median={statistics.median(frame_ms):.1f} max={max(frame_ms):.1f}")
    else:
        out.append("no 'DKB renderer' lines found (was EDEN_DKB_FRAME_TRACE=1 set?)")

    gpu = [(number(line, "gpu_frame_span_ms"), number(line, "gpu_submission_sum_ms"))
           for t, line in keep if "DKB gpu_frame" in line]
    gpu = [(a, b) for a, b in gpu if a is not None and b is not None]
    if gpu:
        out.append("== GPU frame")
        out.append(f"gpu_frame_span_ms avg={statistics.mean(a for a, _ in gpu):.1f} "
                   f"gpu_submission_sum_ms avg={statistics.mean(b for _, b in gpu):.1f}")

    gaps = [(number(line, "timed_sum_ms"), number(line, "gap_total_ms"))
            for t, line in keep if "DKB gap_trace" in line]
    gaps = [(a, b) for a, b in gaps if a is not None and b is not None]
    if gaps:
        out.append("== Timed GPU work vs gaps (per sampled frame)")
        out.append(f"timed_sum_ms avg={statistics.mean(a for a, _ in gaps):.1f} "
                   f"gap_total_ms avg={statistics.mean(b for _, b in gaps):.1f}")

    census = [number(line, "items") for t, line in keep if "DKB draw_census" in line]
    census = [v for v in census if v is not None]
    if census:
        out.append("== Timed items per sampled frame")
        out.append(f"avg={statistics.mean(census):.0f} min={min(census):.0f} max={max(census):.0f}")

    top = defaultdict(list)
    for t, line in keep:
        if "DKB top_items" in line:
            for key, ms in HASHED.findall(line):
                top[key].append(float(ms))
    if top:
        out.append("== Slowest items (hash: appearances in top 5, avg ms)")
        ranked = sorted(top.items(), key=lambda kv: -statistics.mean(kv[1]) * len(kv[1]))
        for key, values in ranked[:6]:
            out.append(f"{key}: {len(values)}x avg {statistics.mean(values):.2f} ms")

    for title, marker in (("GPU front thread (ms per second)", "GPU thread per second:"),
                          ("GPU back thread (ms per second)", "GPU back thread per second:")):
        zones = defaultdict(list)
        rates = defaultdict(list)
        for t, line in keep:
            if marker in line:
                for name, ms, rate in zone_pieces(line, marker):
                    zones[name].append(ms)
                    rates[name].append(rate)
        if zones:
            out.append(f"== {title}, averaged over {len(next(iter(zones.values())))} reports")
            ranked = sorted(zones.items(), key=lambda kv: -statistics.mean(kv[1]))
            for name, values in ranked[:14]:
                out.append(f"{name}: {statistics.mean(values):.1f} ms "
                           f"({statistics.mean(rates[name]):.0f}/s)")

    copy = [line for t, line in keep if "COPYTRACE" in line]
    if copy:
        out.append("== Copy trace (last)")
        out.append(copy[-1].strip())
    return out


def header(lines):
    out = ["== Build and patches"]
    seen = set()
    for line in lines:
        if ("Version" in line and "|" in line) or "Applying built-in patch" in line \
                or "Native zstd" in line or "Booting game" in line:
            text = STAMP.sub("", line).strip()
            if text not in seen:
                seen.add(text)
                out.append(text)
        if len(out) > 14:
            break
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--appimage", help="path to the AppImage (default: search common folders)")
    parser.add_argument("--label", default="run", help="name for this run")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VAL",
                        help="extra environment variable for this run (repeatable)")
    parser.add_argument("--skip", type=float, default=15.0,
                        help="seconds to ignore at the start (default 15)")
    parser.add_argument("--analyze", metavar="LOG", help="summarize an existing log, do not launch")
    args = parser.parse_args()

    env_used = dict(TRACE_ENV)
    for item in args.env:
        key, _, value = item.partition("=")
        env_used[key] = value

    log_path = args.analyze or LOG
    if not args.analyze:
        appimage = args.appimage or find_appimage()
        if not appimage:
            sys.exit("AppImage not found; pass --appimage PATH")
        print(f"Launching {appimage}\nEnvironment: "
              + " ".join(f"{k}={v}" for k, v in env_used.items()))
        print("Play your test, then close the emulator. The summary is written when it exits.")
        subprocess.call([appimage], env={**os.environ, **env_used})

    try:
        with open(log_path, errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError as error:
        sys.exit(f"cannot read {log_path}: {error}")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.join(OUT_DIR, f"{stamp}-{args.label}")
    summary = [f"Chata bench '{args.label}' {stamp}",
               "env: " + ("(analyze mode)" if args.analyze else
                          " ".join(f"{k}={v}" for k, v in env_used.items()))]
    summary += header(lines) + summarize(lines, args.skip)
    text = "\n".join(summary) + "\n"
    with open(base + ".txt", "w") as handle:
        handle.write(text)
    with open(base + ".raw.txt", "w") as handle:
        handle.write("\n".join(line for line in lines
                               if "DKB " in line or "profile.h" in line or "COPYTRACE" in line)
                     + "\n")
    print(text)
    print(f"Saved: {base}.txt\n       {base}.raw.txt (all trace lines)")


if __name__ == "__main__":
    main()
