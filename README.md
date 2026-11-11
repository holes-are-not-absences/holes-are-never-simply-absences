# holes are never simply absences · GDELT

A világ angol nyelvű online híreit figyeli 15 percenként, és szövésmintát rajzol belőlük.
Egy sor = egy nap, egy cella = 15 perc. Sötét a cella, ha abban a negyedórában legalább egy hír
címében vagy webcímében szerepelt a kulcsszó. Ha nem, a cella lyuk.

- `collect.py`: a gyűjtő program. Letölti a GDELT nyers fájljait, és csak számokat ment.
- `keywords.txt`: a figyelt kulcsszavak témakörökbe rendezve: `[Témakör]` sor, alatta soronként egy kulcsszó. Új kulcsszó után futtasd a gyűjtőt visszatöltéssel (pl. `28`), és a múltra is kiszámolja.
- `data/counts.csv`: az összegyűlt adat. Ezt a gyűjtő automatikusan frissíti.
- `index.html`: a weboldal, ami a szövetet rajzolja.
- `.github/workflows/collect.yml`: az ütemező, ami óránként lefuttatja a gyűjtőt.

## Beállítás (egyszer kell megcsinálni, kb. 15 perc)

1. **Fiók.** Regisztrálj a github.com-on (ingyenes).
2. **Új tároló.** Jobb felül **+ → New repository**. A neve legyen `holes`, és állítsd **Public**-ra
   (az ingyenes GitHub Pages ehhez kell; az adat csak számokból áll). Kattints a **Create repository** gombra.
3. **Fájlok feltöltése.** A tároló oldalán: **uploading an existing file** (vagy **Add file → Upload files**).
   Húzd be: `index.html`, `collect.py`, `keywords.txt`, `README.md`, és a `data` mappát.
   Lent kattints a **Commit changes** gombra.
4. **Az ütemező fájl.** A `.github` mappa rejtett, ezért kézzel kell létrehozni:
   **Add file → Create new file**. A fájlnévhez írd be pontosan: `.github/workflows/collect.yml`
   (a perjelekből mappák lesznek). Másold be a `collect.yml` tartalmát, majd **Commit changes**.
5. **Írási jog.** **Settings → Actions → General**, legalul a **Workflow permissions** résznél
   jelöld be: **Read and write permissions**, majd **Save**.
6. **Első futtatás és múlt feltöltése.** Fent az **Actions** fül → bal oldalt **GDELT gyűjtés** →
   jobb oldalt **Run workflow**. A mezőbe írd be: `14` (az elmúlt 14 nap feltöltése), és indítsd el.
   Ez kb. 30–60 percig fut. Ha végzett, a `data/counts.csv` megtelik. Utána óránként magától fut tovább.
   Ha több múlt kell, futtasd újra nagyobb számmal (pl. `28`).
7. **Weboldal.** **Settings → Pages**. A *Source* legyen **Deploy from a branch**, a *Branch* **main**, a mappa **/ (root)**.
   **Save**. Pár perc múlva itt lesz: `https://<felhasználóneved>.github.io/holes/`

## Ha valami nem megy

- Az **Actions** fülön minden futásnál látszik, mi történt. A piros X hibát jelent: kattints rá, és a napló végén ott a hiba oka.
- A weboldal a letöltött fájlból megnyitva nem működik, csak a GitHub Pages címén.
- A GitHub az ütemezett futásokat néha késve indítja. A gyűjtő ezt pótolja: mindig az utolsó feldolgozott negyedórától folytatja.

## Módszertan (a naplóhoz)

- Forrás: GDELT Project, GKG 2.1, 15 perces nyers fájlok (http://data.gdeltproject.org/gdeltv2/).
  A fő GKG-folyam angol nyelvű online híreket tartalmaz.
- Egy cikk akkor számít, ha a kulcsszó a címében vagy a webcímében szerepel, önálló szóként (többes számmal együtt), kis- és nagybetűtől függetlenül. A témakör-oszlop azokat a cikkeket számolja, amelyekben a témakör legalább egy kulcsszava szerepel.
  A cikk teljes szövegét a GDELT nem adja ki, ezért ez alsó becslés.
- A „nincs adat” cellák ott vannak, ahol a GDELT-nél hiányzik a 15 perces fájl. Ezek nem csendek,
  hanem adathiányok, és a szöveten másképp jelennek meg.
- Cím, link vagy szöveg nem kerül mentésre, csak darabszámok.
