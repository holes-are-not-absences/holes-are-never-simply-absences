"""
holes are never simply absences · GDELT-gyűjtő

A GDELT 15 percenként kiad egy fájlt (GKG) az összes friss online hírről.
Ez a program letölti a még fel nem dolgozott fájlokat, és minden 15 perces
időszeletre megszámolja:
  - hány cikk volt összesen (total),
  - hány cikk címében vagy webcímében szerepelt az egyes kulcsszavak valamelyike.

Az eredmény a data/counts.csv fájlba kerül. Cikkszöveget, címet, linket nem ment,
csak számokat.

Használat:
  python collect.py                    # a legutóbbi feldolgozott óta minden új fájl
  python collect.py --backfill-days 14 # az elmúlt 14 nap feltöltése
"""
import argparse
import csv
import datetime as dt
import io
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "http://data.gdeltproject.org/gdeltv2/"
DATA = os.path.join("data", "counts.csv")
KEYWORDS = "keywords.txt"
STEP = dt.timedelta(minutes=15)
TITLE_RE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.S)
UA = {"User-Agent": "holes-are-never-simply-absences (MOME student research project)"}


def load_keywords():
    """[(témakör, kulcsszó), ...] a keywords.txt sorrendjében."""
    out, cat = [], "egyéb"
    with open(KEYWORDS, encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith("#"):
                continue
            if l.startswith("[") and l.endswith("]"):
                cat = l[1:-1].strip()
                continue
            out.append((cat, normalise(l).strip()))
    return out


def columns(kws):
    cats = list(dict.fromkeys(c for c, _ in kws))
    return ["_osszes"] + ["tema:" + c for c in cats] + [k for _, k in kws]


def matchers(kws):
    # szóhatárra illeszt, többes szám (-s, -es) is számít; így pl. a „trolling” nem talál a „patrolling”-ra
    return [re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?:s|es)?(?![a-z0-9])") for _, k in kws]


def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def latest_slot():
    txt = fetch(BASE + "lastupdate.txt", 60).decode("utf-8", "replace")
    for line in txt.splitlines():
        if line.strip().endswith(".gkg.csv.zip"):
            name = line.split()[-1].rsplit("/", 1)[-1]
            return dt.datetime.strptime(name[:14], "%Y%m%d%H%M%S")
    raise RuntimeError("A lastupdate.txt-ben nincs GKG-fájl.")


def slot_name(t):
    return t.strftime("%Y%m%d%H%M%S")


def normalise(s):
    return re.sub(r"[-_/+.%]+", " ", s.lower())


def count_slot(t, kws, res):
    """Egy 15 perces GKG-fájl feldolgozása. None, ha a fájl nem létezik."""
    url = BASE + slot_name(t) + ".gkg.csv.zip"
    try:
        raw = fetch(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    zf = zipfile.ZipFile(io.BytesIO(raw))
    data = zf.read(zf.namelist()[0]).decode("utf-8", "replace")
    cols = columns(kws)
    counts = dict.fromkeys(cols, 0)
    total = 0
    for line in data.split("\n"):
        f = line.split("\t")
        if len(f) < 27 or f[2] != "1":       # 1 = webes hírforrás
            continue
        total += 1
        m = TITLE_RE.search(f[26])
        text = " " + normalise(f[4]) + " " + (normalise(m.group(1)) if m else "") + " "
        cats = set()
        for (cat, kw), rx in zip(kws, res):
            if rx.search(text):
                counts[kw] += 1
                cats.add(cat)
        for c in cats:
            counts["tema:" + c] += 1
        if cats:
            counts["_osszes"] += 1
    return total, counts


def read_existing():
    rows = {}
    if os.path.exists(DATA):
        with open(DATA, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                rows[r["slot"]] = r
    return rows


def write_all(rows, cols_):
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    cols = ["slot", "total"] + cols_
    with open(DATA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for k in sorted(rows):
            w.writerow({c: rows[k].get(c, "") for c in cols})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill-days", type=float, default=0)
    ap.add_argument("--max-slots", type=int, default=4000)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    kws = load_keywords()
    cols = columns(kws)
    res = matchers(kws)
    rows = read_existing()
    end = latest_slot()
    if a.backfill_days > 0:
        start = end - dt.timedelta(days=a.backfill_days)
    elif rows:
        start = dt.datetime.strptime(max(rows), "%Y%m%d%H%M%S") + STEP
    else:
        start = end - dt.timedelta(hours=6)
    start = start.replace(minute=start.minute - start.minute % 15, second=0, microsecond=0)

    def needs(name):
        r = rows.get(name)
        if r is None:
            return True
        if r.get("total", "") == "":          # a GDELT-nél hiányzó fájl: nem próbáljuk újra
            return False
        return any(r.get(c, "") == "" for c in cols)   # új kulcsszó: újraszámolás

    todo = []
    t = start
    while t <= end:
        if needs(slot_name(t)):
            todo.append(t)
        t += STEP
    todo = todo[-a.max_slots:]
    print(f"kulcsszavak: {len(kws)} db, {len(cols) - len(kws) - 1} témakör")
    print(f"feldolgozandó időszeletek: {len(todo)} ({start} – {end} UTC)")

    done = missing = failed = 0
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(count_slot, t, kws, res): t for t in todo}
        for fu in as_completed(futs):
            t = futs[fu]
            try:
                res_ = fu.result()
            except Exception as e:                       # hálózati hiba: következő futáskor újrapróbálja
                failed += 1
                print(f"  hiba {slot_name(t)}: {e}", file=sys.stderr)
                continue
            if res_ is None:                              # a GDELT-nél nincs ilyen fájl: adathiány
                missing += 1
                rows[slot_name(t)] = {"slot": slot_name(t), "total": ""}
                continue
            total, counts = res_
            row = {"slot": slot_name(t), "total": str(total)}
            row.update({k: str(v) for k, v in counts.items()})
            rows[slot_name(t)] = row
            done += 1
            if done % 100 == 0 or done == len(todo):
                print(f"  {done}/{len(todo)}")
                write_all(rows, cols)
    write_all(rows, cols)
    print(f"kész: {done} feldolgozva, {missing} hiányzó fájl, {failed} hiba")


if __name__ == "__main__":
    main()
