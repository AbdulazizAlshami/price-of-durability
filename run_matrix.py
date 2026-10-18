#!/usr/bin/env python3
import json
import os
import subprocess
import time

TARGETS = [
    ("ext4_ordered", "/mnt/test_ext4"),
    ("xfs", "/mnt/test_xfs"),
    ("btrfs", "/mnt/test_btrfs"),
]

MODES = [
    ("no_fsync", ["--fsync=0"]),
    ("fsync_per_write", ["--fsync=1"]),
    ("batched_fsync", ["--fdatasync=16"]),
]

RUNS = 5
BLOCK_SIZE = "4k"
RUNTIME = 15
FILE_SIZE = "1G"

def drop_caches():
    subprocess.run(["sync"])
    try:
        with open("/proc/sys/vm/drop_caches", "w") as f:
            f.write("3\n")
    except PermissionError:
        pass

def run_fio(name, directory, mode_flags, run_id):
    test_file = os.path.join(directory, f"bench_{run_id}.dat")
    cmd = [
        "fio",
        f"--name={name}",
        f"--filename={test_file}",
        "--ioengine=sync",
        "--rw=randwrite",
        f"--bs={BLOCK_SIZE}",
        f"--size={FILE_SIZE}",
        f"--runtime={RUNTIME}",
        "--time_based",
        "--output-format=json"
    ] + mode_flags

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Error on {name}: {res.stderr}")
        return None

    data = json.loads(res.stdout)
    job = data["jobs"][0]["write"]
    iops = job["iops"]
    mean_lat_us = job["lat_ns"]["mean"] / 1000.0
    p99_lat_us = job["clat_ns"]["percentile"]["99.000000"] / 1000.0

    if os.path.exists(test_file):
        os.remove(test_file)

    return iops, mean_lat_us, p99_lat_us

print("filesystem,sync_mode,run,iops,mean_latency_us,p99_latency_us")

for fs_name, path in TARGETS:
    for mode_name, flags in MODES:
        for r in range(1, RUNS + 1):
            drop_caches()
            time.sleep(1)
            result = run_fio(fs_name, path, flags, r)
            if result:
                iops, mean_lat, p99_lat = result
                print(f"{fs_name},{mode_name},{r},{iops:.2f},{mean_lat:.2f},{p99_lat:.2f}", flush=True)
