"""Turn the UCI "Online Retail" workbook into a basket CSV that qfim-bench can load.

Source: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C5BW33   License: CC BY 4.0 (attribution required).

Rules, fixed here so the derived file is reproducible:
  * one basket per InvoiceNo; invoices starting with "C" (cancellations) are dropped;
  * the item is the product Description, upper-cased and stripped; rows with a blank description
    are dropped;
  * only the TOP_N most frequent items (by number of baskets containing them) are kept, to keep the
    file small; a basket with none of them is dropped.

Uses only the standard library (the workbook is read as zipped XML).

    python data/prepare_online_retail.py "<path>/Online Retail.xlsx"
"""

import csv
import sys
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
TOP_N = 50
OUT = Path(__file__).resolve().parent / "online_retail_baskets.csv"


def shared_strings(z: zipfile.ZipFile) -> list[str]:
    strings = []
    for _, el in ET.iterparse(z.open("xl/sharedStrings.xml")):
        if el.tag == NS + "si":
            strings.append("".join(t.text or "" for t in el.iter(NS + "t")))
            el.clear()
    return strings


def rows(z: zipfile.ZipFile, strings: list[str]):
    """Yield (InvoiceNo, Description) for each data row of the first sheet (columns A and C)."""
    for _, el in ET.iterparse(z.open("xl/worksheets/sheet1.xml")):
        if el.tag != NS + "row":
            continue
        cells = {}
        for c in el.findall(NS + "c"):
            col = "".join(ch for ch in c.get("r") if ch.isalpha())
            v = c.find(NS + "v")
            if v is None:
                continue
            cells[col] = strings[int(v.text)] if c.get("t") == "s" else v.text
        el.clear()
        if "A" in cells and "C" in cells:
            yield cells["A"], cells["C"]


def main(path: str) -> None:
    with zipfile.ZipFile(path) as z:
        baskets: dict[str, set[str]] = {}
        for invoice, desc in rows(z, shared_strings(z)):
            if invoice == "InvoiceNo" or invoice.startswith("C"):
                continue
            desc = desc.strip().upper()
            if desc:
                baskets.setdefault(invoice, set()).add(desc)
    freq = Counter(i for b in baskets.values() for i in b)
    keep = {i for i, _ in freq.most_common(TOP_N)}
    kept = [sorted(b & keep) for _, b in sorted(baskets.items()) if b & keep]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(kept)
    print(f"{len(baskets)} invoices -> {len(kept)} baskets with >=1 of the top {TOP_N} items -> {OUT.name}")


if __name__ == "__main__":
    main(sys.argv[1])
