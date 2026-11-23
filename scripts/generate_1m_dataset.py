#!/usr/bin/env python3
"""
Generate 1,000,000 Diverse Multi-Region AWS Usage Records.
Outputs:
- data/aws_1m_usage.parquet (Full 1,000,000 records)
- data/aws_1m_usage.csv.gz (Full 1,000,000 records compressed CSV)
- data/aws_1m_sample.csv (First 10,000 records uncompressed for quick inspection)
"""

import csv
import datetime as dt
import gzip
import io
import json
import os
import sys
import time
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from paginator import (
    TOTAL_RECORDS,
    get_record_by_offset,
    REGIONS_CONFIG,
    ARCHETYPES,
    SERVICE_CATALOG,
)

DATA_DIR = os.path.join(REPO_ROOT, "data")
PARQUET_PATH = os.path.join(DATA_DIR, "aws_1m_usage.parquet")
CSV_GZ_PATH = os.path.join(DATA_DIR, "aws_1m_usage.csv.gz")
SAMPLE_CSV_PATH = os.path.join(DATA_DIR, "aws_1m_sample.csv")

BATCH_SIZE = 50_000


def generate_all():
    print("==================================================================")
    print(f" Generating {TOTAL_RECORDS:,} Multi-Region Production Records")
    print("==================================================================")
    t0 = time.time()

    os.makedirs(DATA_DIR, exist_ok=True)

    # Parquet writer setup
    schema = pa.schema([
        ("date", pa.string()),
        ("region", pa.string()),
        ("workload_type", pa.string()),
        ("gross_usd", pa.float64()),
        ("color_class", pa.string()),
        ("status_label", pa.string()),
        ("primary_service", pa.string()),
        ("top_5_services_json", pa.string()),
        ("raw_services_json", pa.string()),
    ])

    pq_writer = pq.ParquetWriter(PARQUET_PATH, schema, compression="snappy")
    gz_file = gzip.open(CSV_GZ_PATH, "wt", encoding="utf-8")
    sample_file = open(SAMPLE_CSV_PATH, "w", encoding="utf-8")

    csv_headers = [
        "date",
        "region",
        "workload_type",
        "gross_usd",
        "color_class",
        "status_label",
        "primary_service",
        "top_5_services_json",
        "raw_services_json",
    ]

    gz_writer = csv.writer(gz_file)
    sample_writer = csv.writer(sample_file)

    gz_writer.writerow(csv_headers)
    sample_writer.writerow(csv_headers)

    total = TOTAL_RECORDS
    num_batches = math.ceil(total / BATCH_SIZE)

    for b in range(num_batches):
        b_start = b * BATCH_SIZE
        b_end = min(total, b_start + BATCH_SIZE)
        batch_n = b_end - b_start

        dates = []
        regions = []
        workload_types = []
        grosses = []
        color_classes = []
        status_labels = []
        primary_services = []
        top5_jsons = []
        raw_jsons = []

        for k in range(b_start, b_end):
            rec = get_record_by_offset(k)
            top5 = rec["top_5_services"]
            prim_svc = top5[0]["service"] if top5 else "Unknown"
            top5_str = json.dumps(top5, separators=(",", ":"))
            raw_str = json.dumps(rec["raw_services"], separators=(",", ":"))

            dates.append(rec["date"])
            regions.append(rec["region"])
            workload_types.append(rec["workload_type"])
            grosses.append(rec["gross_usd"])
            color_classes.append(rec["color_class"])
            status_labels.append(rec["status_label"])
            primary_services.append(prim_svc)
            top5_jsons.append(top5_str)
            raw_jsons.append(raw_str)

            row = [
                rec["date"],
                rec["region"],
                rec["workload_type"],
                rec["gross_usd"],
                rec["color_class"],
                rec["status_label"],
                prim_svc,
                top5_str,
                raw_str,
            ]
            gz_writer.writerow(row)
            if k < 10_000:
                sample_writer.writerow(row)

        table = pa.Table.from_arrays(
            [
                pa.array(dates),
                pa.array(regions),
                pa.array(workload_types),
                pa.array(grosses),
                pa.array(color_classes),
                pa.array(status_labels),
                pa.array(primary_services),
                pa.array(top5_jsons),
                pa.array(raw_jsons),
            ],
            schema=schema,
        )
        pq_writer.write_table(table)

        progress = b_end / total * 100
        elapsed = time.time() - t0
        rate = b_end / elapsed if elapsed > 0 else 0
        print(f"  Processed {b_end:,} / {total:,} records ({progress:.1f}%) [{rate:,.0f} records/sec]")

    pq_writer.close()
    gz_file.close()
    sample_file.close()

    total_time = time.time() - t0
    pq_sz = os.path.getsize(PARQUET_PATH) / 1024 / 1024
    gz_sz = os.path.getsize(CSV_GZ_PATH) / 1024 / 1024
    sm_sz = os.path.getsize(SAMPLE_CSV_PATH) / 1024 / 1024

    print("==================================================================")
    print(f" ✅ Finished in {total_time:.2f} seconds ({total / total_time:,.0f} records/sec)")
    print(f" Parquet:   {PARQUET_PATH} ({pq_sz:.2f} MB)")
    print(f" CSV.gz:    {CSV_GZ_PATH} ({gz_sz:.2f} MB)")
    print(f" Sample:    {SAMPLE_CSV_PATH} ({sm_sz:.2f} MB)")
    print("==================================================================")


if __name__ == "__main__":
    import math
    generate_all()
