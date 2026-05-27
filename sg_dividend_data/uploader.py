"""Upload the universe JSON to Cloudflare R2 (S3-compatible)."""
from __future__ import annotations
import os
from pathlib import Path

import boto3


def upload_to_r2(path: Path, *, key: str = "sg_dividend_universe.json") -> None:
    account = os.environ["R2_ACCOUNT_ID"]
    bucket = os.environ["R2_BUCKET"]
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    s3.upload_file(
        str(path), bucket, key,
        ExtraArgs={"ContentType": "application/json", "CacheControl": "public, max-age=300"},
    )
