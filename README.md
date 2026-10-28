# Netflix Global Content Performance Strategy

An audited visual story separating peak reach, repeated chart appearances, and country breadth. Author: Violetta Kalinicheva.

## Question and decision

How do these dimensions differ among charting films and TV seasons in a fixed historical Top 10 window? A content analytics team can use the analysis to structure a review shortlist without interpreting popularity as profitability, subscriber retention, or artistic quality. The default workflow downloads two current official weekly files and keeps only weeks ending July 4, 2021–April 14, 2024. It does not require an unavailable archived workbook.

## Verified results

The complete notebook was executed from a new kernel on October 28, 2026. [validation.json](validation.json) records source hashes, audits, and actual results.

- The bounded data contain **5,840 Global rows and 272,260 country rows**, with 146 weeks and 94 countries overall. Weekly country coverage varies from 93 to 94. Current downloaded files contain additional later weeks, which are explicitly excluded.
- View-count comparisons use only **44 common weeks**, June 18, 2023–April 14, 2024, and **741 separate title-season units**. Mean observed Global Top 10 weeks are **1.98, 2.22, 2.54, and 2.97** for English films, non-English films, English TV, and non-English TV. Medians are 1, 2, 2, and 2, respectively.
- Current official Global downloads omit the older staggered-launch fields. Schedule effects cannot be separated in the public-download run, so the code reports that information as unavailable rather than assuming every title launched simultaneously.
- **Damsel** has the highest weekly view peak, **50.8 million**. Eleven of the 12 highest peak entries are films.
- **ONE PIECE: Season 1** appears in **93 countries**, with 543 country-week appearances in the common window. Countries count equally, regardless of population.

## Methods and repairs

The release preserves show title plus season. It counts distinct observed chart weeks once per title-season instead of averaging repeatedly stored cumulative counters or combining seasons by show title. An unsupported `maximum views × cumulative weeks` score from the earlier analysis is removed. Global and country lists remain separate because their grains and populations differ. The earlier historical 91-day list is an optional appendix, not required or used for a headline in the public-download run; a current all-time list cannot recreate a historical ranking.

The audit flags six ambiguous historical country rows labeled *The Mummy* at different ranks; none occurs in the selected window. It retains them in the source audit and excludes ambiguous title-week labels from title-identified country summaries. No exact rows are duplicated. The code does not invent views for 4,080 hours-only rows. Seventy-two views-era runtime values are zero and are treated as unavailable for independent hours/runtime checks; published Netflix view counts are retained unchanged.

## Data and acquisition

The [official Netflix Top 10 weekly workbooks](https://www.netflix.com/tudum/top10/) were downloaded on October 28, 2026:

- Download [all-weeks-global.xlsx](https://www.netflix.com/tudum/top10/data/all-weeks-global.xlsx) and save as `all-weeks-global-netflix.xlsx`. Observed SHA-256: `7daf75f505d72218e26427ddaa6c2570ef89a50fd39b6a182107625af247e714`.
- Download [all-weeks-countries.xlsx](https://www.netflix.com/tudum/top10/data/all-weeks-countries.xlsx) and save as `all-weeks-countries-netflix.xlsx`. Observed SHA-256: `b12f6127d92bec1beb941c06e0f1522f62114198fc6e62cbe99553366db938df`.

After the explicit July 4, 2021–April 14, 2024 filter, their row counts and core numerical results match the earlier supplied snapshot. The full downloaded files contain 11,080 Global and 515,920 country rows; later weeks are excluded. The publisher revised some show/season labels; the current labels are retained. Live workbooks may change: the downloader validates Excel containers, while analysis assertions check the bounded historical rows and numerical claims rather than requiring an unchanged whole-file hash. The earlier `most-popular-netflix.xlsx` 91-day snapshot is optional, not downloaded or required for this release; a current all-time file cannot replace it. The [official methodology](https://about.netflix.com/en/news/top-10-things-about-netflix-top-10), updated June 20, 2023, explains views, runtimes, and separate seasons. No dataset-specific redistribution permission was established from the publisher's pages and [linked terms](https://help.netflix.com/legal/termsofuse); this release contains code and aggregate analysis, not raw workbooks.

## Reproduce

Python 3.12.14 was used. From this folder:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --download
```

`--download` retrieves the two official weekly files to ignored `data/`, validates each Excel container, and preserves existing files. To use files already obtained from the publisher, set `PROJECT_DATA_DIR` to their containing directory. `run.py` clears saved outputs, starts a new kernel with the selected Python interpreter, executes every cell, and updates hashes and observed results. `python analysis.py` runs calculations without charts. Assertions compare the bounded row counts and core metrics against this release; a later revision that changes a claim stops with a message to review the narrative. The currently downloadable files were tested successfully, not merely linked.

## Files and appropriate use

[netflix_content_strategy.ipynb](netflix_content_strategy.ipynb) contains the visual story and embedded figures. [analysis.py](analysis.py) contains portable transformations and assertions. `requirements.txt` pins the full tested Python environment.

Chart appearances are censored by window boundaries and limited to Top 10 entries, not the full catalog. Availability, promotion, release schedules, and selection affect category comparisons. Equal weekly chart slots mean higher average persistence also implies fewer distinct entrants. Country breadth lacks audience denominators. Views are rounded hours/runtime equivalents, not unique viewers. Names may not distinguish remakes. No causal language effect, subscriber-retention estimate, or spending recommendation is supported. Use these columns alongside costs, rights, availability, and subscriber outcomes before investment decisions. These are historical 2024-ending results, not current 2026 rankings, although the source files were retrieved in 2026.

Original code and writing are licensed under [MIT](LICENSE). Netflix data and marks retain their own terms.
