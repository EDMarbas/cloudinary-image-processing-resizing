# 📌 Image Upload & Transformation Pipeline
### Automated Cloudinary Image Fetcher, Uploader & Excel Generator  
*(Python script: `image_resize.py`)*

This project provides a fully automated workflow for downloading remote images, uploading them to Cloudinary, applying image transformations, and generating a clean Excel output file with all processed results.

It is designed for any workflow that requires high-volume image handling, such as e-commerce product imports, catalog automation, or media library processing.

---

## 🚀 Features

- Fetches remote images using real browser request headers  
- Supports optional **referer** headers for restricted images  
- Encodes images as base64 for reliable Cloudinary uploading  
- Generates SEO-friendly Cloudinary `public_id` values  
- Applies consistent Cloudinary delivery transforms  
- Exports final Cloudinary image URLs to Excel  
- Preserves **all original columns** from the source file  
- Adds `Variant SKU` and `Image Src` columns  
- Built-in throttling to prevent API rate limits  
- Uses `.env` for secure Cloudinary credentials

---

## 📁 Project Structure

```
project/
│── image_resize.py
│── source.xlsx               # Your input file
│── final_output.xlsx         # Auto-generated results
│── .env                      # Cloudinary credentials
```

---

## ⚙️ Requirements

Install dependencies:

```
pip install pandas requests python-dotenv openpyxl
```

---

## 🔧 Environment Variables (.env)

Create a `.env` file:

```
CLOUD_NAME=your_cloud_name
CLOUD_API_KEY=your_api_key
CLOUD_API_SECRET=your_api_secret
```

These values can be found in your Cloudinary Dashboard under **API Keys**.

---

## 📥 Input File Format: `source.xlsx`

Your Excel source file must contain:

### **Required Columns**
| Column | Description |
|--------|-------------|
| `SKU` | Unique identifier for the image/product |
| `Image` | Remote image URL to download |

### **Optional Columns**
| Column | Purpose |
|--------|---------|
| `Image Alt Text` | Used to name the Cloudinary public_id |
| `Product Name` | Fallback public_id naming |
| `Starting Url` | Used as a Referer header when fetching the image |

The script automatically handles missing optional fields.

---

## 📤 Output File: `final_output.xlsx`

After processing, the script generates:

- **All original columns preserved exactly**
- Plus two additional fields:

| Column | Description |
|--------|-------------|
| `Variant SKU` | Same SKU value (useful for Shopify, ERP pipelines) |
| `Image Src` | Final Cloudinary URL with transformations applied |

Example Cloudinary transform (customizable):

```
c_pad,w_800,h_800,b_white,f_auto,q_auto,dpr_auto
```

---

## ▶️ Run the Script

Run inside VS Code terminal or any shell:

```
python image_resize.py
```

The script will:

1. Read `source.xlsx`
2. Fetch each image URL
3. Upload it to Cloudinary
4. Apply the configured transform
5. Generate `final_output.xlsx`
6. Print success/failure logs in the console

---

## 📝 Example Console Output

```
✅ Row 2 ABC123 → https://res.cloudinary.com/.../image/upload/c_pad,w_800...
❌ Row 3 XYZ999: Fetch failed (404)
Done. Attempted: 14, Processed: 13
Output written to: final_output.xlsx
```

---

## 🛠 Troubleshooting

### Missing Cloudinary credentials
```
ERROR: Missing CLOUD_NAME / CLOUD_API_KEY / CLOUD_API_SECRET env vars.
```
Check your `.env` file.

### Image fetch failed  
Possible causes:
- Dead/invalid image URL  
- Server blocks unknown user agents  
- Missing `Starting Url` (needed for referer-based images)

### Upload failed  
Likely Cloudinary-related:
- Wrong API key  
- Cloud name misspelled  
- Request timed out

---

## 📄 License

This script may be used privately or in commercial automation pipelines.  
Modify freely to fit your workflow.
