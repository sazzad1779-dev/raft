import pandas as pd
from pathlib import Path
import re

# ---------- Helpers ----------
def url_to_filename_key(url: str) -> str:
    url = (url or "").strip()
    return re.sub(
        r"[^a-zA-Z0-9_]", "_",
        url.replace("https://", "").replace("http://", "")
    )[:50]

def read_raw_md(md_dir):
    md_content = {}
    for md_file in Path(md_dir).glob("*.md"):
        md_content[md_file.stem] = md_file.read_text(encoding="utf-8")
    return md_content

def save_contexts_by_url(context_by_url: dict, out_dir: str):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for url, text in context_by_url.items():
        key = url_to_filename_key(url)
        (out_path / f"{key}.md").write_text(text or "", encoding="utf-8")

    return str(out_path)

def _append_if_present(lines, label, value):
    value = (value or "").strip()
    if value:
        lines.append(f"{label}: {value}")

def _join_unique(values):
    vals = sorted({(v or "").strip() for v in values if (v or "").strip()})
    return ", ".join(vals)

# ---------- Core ----------
def build_context_pandas(df, md_content):
    # normalize
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    if "URL" not in df.columns:
        raise ValueError("CSV must contain a 'URL' column")
    df["URL"] = df["URL"].astype(str).str.strip()

    context_by_url = {}

    for url, g in df.groupby("URL", dropna=False):
        g = g.copy()

        # --- Header fields: pick first non-empty value per field ---
        header_lines = []
        field_map = [
            ("大カテゴリ", "大カテゴリ"),
            ("中カテゴリ", "中カテゴリ"),
            ("小カテゴリ", "小カテゴリ"),
            ("メーカ", "メーカ"),
            ("品名", "品名"),
        ]

        for col, label in field_map:
            if col in g.columns:
                first_non_empty = next((v.strip() for v in g[col].astype(str).tolist() if v.strip()), "")
                _append_if_present(header_lines, label, first_non_empty)

        # --- Model -> Model numbers mapping (prevents mixing) ---
        models_block = []
        model_col = "モデル" if "モデル" in g.columns else None
        modelnum_col = "型番" if "型番" in g.columns else None

        if model_col or modelnum_col:
            # group by Model value so model numbers stay attached to the right model
            # (empty model becomes "(no model)")
            g["_model_key"] = g[model_col].astype(str).str.strip() if model_col else ""
            g["_model_key"] = g["_model_key"].replace("", "(型番なし)")

            for model_key, mg in g.groupby("_model_key"):
                nums = _join_unique(mg[modelnum_col].astype(str).tolist()) if modelnum_col else ""
                if nums:
                    models_block.append(f"- モデル: {model_key}\n  型番: {nums}")
                else:
                    models_block.append(f"- モデル: {model_key}")

        csv_part = ""
        if header_lines:
            csv_part += "\n".join(header_lines) + "\n"

        if models_block:
            csv_part += "\nモデル:\n" + "\n".join(models_block) + "\n"

        # --- Attach raw markdown ---
        filename_key = url_to_filename_key(url)
        raw_text = md_content.get(filename_key, "")
        if not raw_text:
            print(f"Warning: No raw markdown found for URL: {url}")
            continue

        context_by_url[url] = (csv_part + "\n" + raw_text).strip() + "\n"

    return context_by_url

# ---------- Runner ----------
# csv_path = "web_crawling/202601_製品マスタ - translated -  Product Master.csv"
csv_path = "web_crawling/202601_製品マスタ - 製品マスタ (1).csv"
md_dir = "scraped_cleaned"

def process_raw_md():
    df = pd.read_csv(csv_path)
    md_content = read_raw_md(md_dir)
    context_by_url = build_context_pandas(df, md_content)
    save_contexts_by_url(context_by_url, "output_directory2")

process_raw_md()
