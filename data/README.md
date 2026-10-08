# Data

## sample_transactions.csv (synthetic)

300 synthetic baskets over 12 items, one basket per row, ragged. Item labels are neutral
(`item_1` ... `item_12`, numbered by decreasing frequency) so the file does not read as real retail
data. It exists to run the package offline in seconds; it is not evidence about any real domain.
Earlier releases (up to v1.0.1) used supermarket-style names for the same baskets; the structure and
every count are unchanged (`item_1` was "mineral water", `item_2` "eggs", `item_3` "chocolate",
`item_4` "spaghetti", `item_5` "french fries").

## online_retail_baskets.csv (real, public)

A subset derived from the UCI Machine Learning Repository dataset **Online Retail**.

- Citation: Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository.
  https://doi.org/10.24432/C5BW33
- License: Creative Commons Attribution 4.0 International (CC BY 4.0), as stated on the dataset
  page (https://archive.ics.uci.edu/dataset/352/online+retail), which permits redistribution of
  derived data with attribution. This file is such a derivative and carries the same license.
- Derivation: `prepare_online_retail.py` (run it on the original `Online Retail.xlsx` to reproduce
  the file). One basket per invoice, cancellations (invoice numbers starting with "C") removed,
  item = upper-cased product description, only the 50 most frequent items kept.

The original workbook (541,909 rows) is not stored in this repository.
