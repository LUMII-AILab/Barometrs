from bs4 import BeautifulSoup
import csv

CATEGORIES = ["DISKRIM", "LAMUV", "NETAISN", "AICIN", "DARB", "PERS", "ASOC", "MILIT", "NOSOD", "EMOC", "NODEV"]

# HTML source: https://barometrs.app.ailab.lv/?section=keywords
INPUT = "input.txt"
OUTPUT = "output.csv"

print("Parsing HTML (this may take a moment)...")
with open(INPUT, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

table = soup.find("table", id="data_table")
rows = table.find("tbody").find_all("tr")

written = 0
with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["rank", "word", "paradigm", "frequency", "weight"] + CATEGORIES)

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 16:
            continue

        rank_text = cells[0].get_text(strip=True).rstrip(".")
        if not rank_text.isdigit():
            continue

        rank = int(rank_text)
        word_tag = cells[1].find("a")
        if not word_tag:
            continue
        word = word_tag.get_text(strip=True)
        paradigm = cells[2].get_text(strip=True)
        frequency = int(cells[3].get_text(strip=True).replace("\xa0", "").replace(",", ""))
        weight = float(cells[4].get_text(strip=True).replace(",", "."))

        cat_flags = [1 if cells[5 + i].find("img") else 0 for i in range(11)]
        writer.writerow([rank, word, paradigm, frequency, weight] + cat_flags)
        written += 1

print(f"Done — {written} rows written to {OUTPUT}")
