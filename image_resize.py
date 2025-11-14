import os
import time
import base64
import hashlib
import requests
import pandas as pd
from datetime import datetime
import unicodedata
import re

from dotenv import load_dotenv
load_dotenv()

# ---------- SETTINGS ----------
CLD_FOLDER = "husq_parts"
USE_IMAGE_ALT_TEXT_AS_PUBLIC_ID = True
THROTTLE_SEC = 0.3  # 300 ms
CLD_DELIVERY_TRANSFORM = "c_pad,w_800,h_800,b_white,f_auto,q_auto,dpr_auto"

SOURCE_XLSX = "source.xlsx"       # input Excel file
SOURCE_SHEET = "Sheet1"           # change if needed
DEST_XLSX = "final_output.xlsx"   # output Excel file

# Cloudinary credentials (set as env vars or hardcode here)
CLOUD_NAME = os.getenv("CLOUD_NAME")
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY")
CLOUD_API_SECRET = os.getenv("CLOUD_API_SECRET")

# ---------- HELPERS ----------
def to_public_id(s: str) -> str:
    """Sanitize text to be safe as a Cloudinary public_id."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = re.sub(r"[\u0300-\u036f]", "", s)       # strip accents
    s = re.sub(r"[^\w\-]+", "_", s)            # non-word to _
    s = re.sub(r"_+", "_", s).strip("_")       # collapse and trim _
    return s

def cld_signature(params: dict, api_secret: str) -> str:
    """Generate Cloudinary signature."""
    to_sign = "&".join(
        f"{k}={params[k]}"
        for k in sorted(params)
        if params[k] not in (None, "", False)
    ) + api_secret
    return hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

def cld_transform_url(secure_url: str, transform: str) -> str:
    """Insert transform segment into Cloudinary URL."""
    return str(secure_url).replace("/upload/", f"/upload/{transform}/")

def upload_to_cloudinary(remote_url: str, public_id: str, referer: str | None = None) -> str:
    """Download image bytes from remote_url and upload to Cloudinary."""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer

    resp = requests.get(remote_url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Fetch failed ({resp.status_code}) for URL: {remote_url}")

    content_type = resp.headers.get("content-type", "image/png")
    file_b64 = base64.b64encode(resp.content).decode("utf-8")
    data_url = f"data:{content_type};base64,{file_b64}"

    endpoint = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
    ts = str(int(datetime.now().timestamp()))

    sign_params = {
        "folder": CLD_FOLDER,
        "overwrite": "true",
        "unique_filename": "false",
        "timestamp": ts,
    }
    if public_id:
        sign_params["public_id"] = public_id

    sig = cld_signature(sign_params, CLOUD_API_SECRET)

    payload = {
        "file": data_url,
        **sign_params,
        "api_key": CLOUD_API_KEY,
        "signature": sig,
    }

    up = requests.post(endpoint, data=payload, timeout=60)
    if up.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed ({up.status_code}): {up.text}")

    data = up.json()
    return data.get("secure_url", "")

def cell_str(val) -> str:
    """Convert Excel cell to clean string (NaN-safe)."""
    if pd.isna(val):
        return ""
    return str(val).strip()

# ---------- MAIN ----------
def main():
    # Check Cloudinary env
    if not (CLOUD_NAME and CLOUD_API_KEY and CLOUD_API_SECRET):
        print("ERROR: Missing CLOUD_NAME / CLOUD_API_KEY / CLOUD_API_SECRET env vars.")
        return

    # Load Excel
    try:
        df = pd.read_excel(SOURCE_XLSX, sheet_name=SOURCE_SHEET)
    except Exception as e:
        print(f"ERROR reading {SOURCE_XLSX}: {e}")
        return

    required_cols = ["SKU", "Image"]
    for col in required_cols:
        if col not in df.columns:
            print(f"ERROR: source file must contain column: '{col}'")
            return

    source_cols = list(df.columns)  # all original columns
    out_rows = []
    attempted = processed = 0

    for idx, row in df.iterrows():
        excel_row_num = idx + 2  # 1-based with header row
        sku = cell_str(row.get("SKU"))
        if not sku:
            print(f"[Row {excel_row_num}] Missing SKU – skipping")
            continue

        img_url = cell_str(row.get("Image"))
        if not img_url:
            print(f"[Row {excel_row_num}] Empty Image cell for {sku} – skipping")
            continue

        alt_text = cell_str(row.get("Image Alt Text")) if "Image Alt Text" in df.columns else ""
        product_name = cell_str(row.get("Product Name")) if "Product Name" in df.columns else ""
        referer = cell_str(row.get("Starting Url")) if "Starting Url" in df.columns else ""

        alt_id = to_public_id(alt_text)
        name_id = to_public_id(product_name)
        public_id = alt_id if (USE_IMAGE_ALT_TEXT_AS_PUBLIC_ID and alt_id) else (name_id or sku)

        attempted += 1
        try:
            base_url = upload_to_cloudinary(img_url, public_id, referer or None)
            final_url = cld_transform_url(base_url, CLD_DELIVERY_TRANSFORM)

            # Start with ALL original columns + their values (dynamic)
            out_row = {col: cell_str(row.get(col)) for col in source_cols}

            # Add your output columns
            out_row["Variant SKU"] = sku
            out_row["Image Src"] = final_url

            out_rows.append(out_row)
            processed += 1
            print(f"✅ Row {excel_row_num} {sku} → {final_url}")
        except Exception as e:
            print(f"❌ Row {excel_row_num} {sku}: {e}")
        finally:
            time.sleep(THROTTLE_SEC)

    # Write output Excel
    if out_rows:
        # Ensure column order: all source columns first, then the new ones
        extra_cols = ["Variant SKU", "Image Src"]
        all_cols = source_cols.copy()
        for col in extra_cols:
            if col not in all_cols:
                all_cols.append(col)

        out_df = pd.DataFrame(out_rows)
        out_df = out_df[all_cols]

        out_df.to_excel(DEST_XLSX, index=False)
        print(f"\nDone. Attempted: {attempted}, Processed: {processed}")
        print(f"Output written to: {DEST_XLSX}")
    else:
        print("No rows processed; nothing to write.")

if __name__ == "__main__":
    main()
