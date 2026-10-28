"""Separate reach, repeated Top 10 appearances, and country breadth at season grain."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import platform
import urllib.request
import io
import zipfile
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FILES = ["all-weeks-global-netflix.xlsx", "all-weeks-countries-netflix.xlsx", "most-popular-netflix.xlsx"]
SNAPSHOT_END = pd.Timestamp("2024-04-14")
COLORS = {"Films (English)":"#176b87", "Films (Non-English)":"#84a9b7",
          "TV (English)":"#ba4d25", "TV (Non-English)":"#d59e83"}
KEY = ["category", "show_title", "season_key"]


def download_inputs():
    """Download two publisher-provided workbooks locally; never redistribute them."""
    data_dir = Path(os.environ.get("PROJECT_DATA_DIR", ROOT / "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    for remote,local in [("all-weeks-global.xlsx", FILES[0]), ("all-weeks-countries.xlsx",FILES[1])]:
        destination=data_dir/local
        if destination.exists():
            print(f"Preserving existing {local}; no overwrite.")
            continue
        payload=b""
        for attempt in range(3):
            request=urllib.request.Request("https://www.netflix.com/tudum/top10/data/"+remote,
                                            headers={"Cache-Control":"no-cache"})
            with urllib.request.urlopen(request,timeout=90) as response:
                chunks=[];size=0
                while chunk:=response.read(1_048_576):
                    size+=len(chunk)
                    if size>40_000_000: raise ValueError("Unexpected download size.")
                    chunks.append(chunk)
                payload=b"".join(chunks)
            if zipfile.is_zipfile(io.BytesIO(payload)): break
        else:
            raise ValueError("The publisher did not return a complete Excel workbook after 3 attempts.")
        destination.write_bytes(payload)
        print(f"Downloaded {local}; analysis will retain only weeks through 2024-04-14.")


def load_and_audit():
    data_dir = Path(os.environ.get("PROJECT_DATA_DIR", ROOT / "data"))
    tables, hashes, audit = [], {}, {}
    for file in FILES:
        source = data_dir / file
        if file==FILES[2] and not source.exists():
            tables.append(pd.DataFrame(columns=["category","rank","show_title","season_title","display_title","hours_viewed_first_91_days","runtime","views_first_91_days"]))
            continue
        hashes[file] = hashlib.sha256(source.read_bytes()).hexdigest()
        if file==FILES[2]:
            assert hashes[file]=="9c1f586a13efee4ff07d1723d80084c30920d2fc735c810990a3c23e7a9e780c", "The optional 91-day appendix is not the historical source; omit it for the two-file core."
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Workbook contains no default style")
            raw = pd.read_excel(source, engine="openpyxl")
        assert not raw.duplicated().any(), f"Exact duplicates: {file}"
        clean = raw.copy()
        # The live weekly downloads grow; the portfolio question retains its
        # historical time boundary rather than silently changing the period.
        if "week" in clean:
            clean=clean.loc[pd.to_datetime(clean.week).between("2021-07-04",SNAPSHOT_END)].copy()
        # I keep seasons separate; a missing season belongs to a film/single unit,
        # not to another season of a show sharing the same title.
        clean["season_key"] = clean.season_title.fillna("")
        clean["display_title"] = np.where(clean.season_key.eq(""), clean.show_title, clean.season_key)
        if "week" in clean:
            clean["week"] = pd.to_datetime(clean.week, errors="raise")
            title_week_key = ["week", *KEY] + (["country_iso2"] if "country_iso2" in clean else [])
            clean["ambiguous_title_week"] = clean.duplicated(title_week_key, keep=False)
            if "country_iso2" not in clean:
                assert not clean.ambiguous_title_week.any()
            assert clean.weekly_rank.between(1, 10).all()
            assert clean.week.dt.dayofweek.eq(6).all(), "Weeks must end on Sunday."
        audit[file] = {"downloaded_rows":len(raw),"rows_after_time_boundary":len(clean), "columns":len(raw.columns),
                       "exact_duplicates":0, "season_missing_rows_after_time_boundary":int(clean.season_title.isna().sum())}
        tables.append(clean)
    global_data, countries, popular = tables
    assert not global_data.duplicated(["week","category","weekly_rank"]).any()
    assert global_data.groupby(["week","category"]).size().eq(10).all()
    assert not countries.duplicated(["country_iso2","week","category","weekly_rank"]).any()
    assert countries.groupby(["country_iso2","week","category"]).size().le(10).all()
    assert global_data.weekly_hours_viewed.ge(0).all()
    assert global_data.weekly_views.dropna().gt(0).all()
    if len(popular):
        assert popular.views_first_91_days.gt(0).all()
        assert popular.groupby("category").size().eq(10).all()
        assert not popular.duplicated(["category","rank"]).any()
    schedule_flags_available = "is_staggered_launch" in global_data.columns
    if not schedule_flags_available:
        global_data["is_staggered_launch"]=False
    view_start = global_data.loc[global_data.weekly_views.notna(),"week"].min()
    post = global_data.loc[global_data.week.ge(view_start)]
    assert post.weekly_views.notna().all(), "Do not silently mix hours-only and views periods."
    assert post.runtime.ge(0).all()
    # Netflix rounds the reported fields. I report the discrepancy rather than
    # replace published views or recreate unique audience counts. Zero runtimes
    # cannot support the division and stay in the audit, not this diagnostic.
    positive_runtime = post.loc[post.runtime.gt(0)]
    ratio_error = ((positive_runtime.weekly_hours_viewed / positive_runtime.runtime) / positive_runtime.weekly_views - 1).abs()
    metadata = {"source_sha256":hashes, "audit":audit,
                "global_rows":len(global_data), "country_rows":len(countries),
                "most_popular_rows":len(popular), "countries":countries.country_iso2.nunique(),
                "schedule_flags_available":schedule_flags_available,
                "optional_91day_appendix_available":bool(len(popular)),
                "weeks":global_data.week.nunique(), "first_week":str(global_data.week.min().date()),
                "last_week":str(global_data.week.max().date()), "views_first_week":str(view_start.date()),
                "views_period_rows":len(post), "views_period_weeks":post.week.nunique(),
                "views_period_zero_runtime_rows":int(post.runtime.eq(0).sum()),
                "hours_only_rows":int(global_data.weekly_views.isna().sum()),
                "runtime_views_rounding_max_relative_difference_pct":float(100*ratio_error.max()),
                "global_title_season_units":global_data[KEY].drop_duplicates().shape[0],
                "ambiguous_country_title_week_rows":int(countries.ambiguous_title_week.sum()),
                "views_period_ambiguous_country_title_week_rows":int(countries.loc[countries.week.ge(view_start),"ambiguous_title_week"].sum())}
    return global_data, countries, popular, metadata


def summarize(global_data, countries, popular, metadata):
    start = pd.Timestamp(metadata["views_first_week"])
    post = global_data.loc[global_data.week.ge(start)].copy()
    # I count distinct observed weeks per title-season. Averaging the repeated
    # cumulative counter over title-week rows overweights persistent titles.
    units = post.groupby(KEY, dropna=False).agg(
        observed_weeks=("week","nunique"), peak_weekly_views=("weekly_views","max"),
        display_title=("display_title","first"), first_observed=("week","min"),
        last_observed=("week","max"), any_staggered_launch=("is_staggered_launch","max")).reset_index()
    category_summary = units.groupby("category").agg(
        title_season_units=("observed_weeks","size"),
        median_observed_weeks=("observed_weeks","median"),
        mean_observed_weeks=("observed_weeks","mean"),
        median_peak_weekly_views=("peak_weekly_views","median"))
    peaks = units.sort_values("peak_weekly_views",ascending=False).head(12)
    country_units = countries.loc[countries.week.ge(start) & ~countries.ambiguous_title_week].groupby(KEY).agg(
        countries=("country_iso2","nunique"), country_week_appearances=("week","size"),
        observed_weeks=("week","nunique"),display_title=("display_title","first")).reset_index()
    breadth = country_units.sort_values(["countries","country_week_appearances"],ascending=False).head(12)
    # Same country-week-category grain, but no join to global counts: global and
    # country categories and populations differ, and country rankings lack views.
    coverage = countries.groupby("week").agg(countries=("country_iso2","nunique"), rows=("week","size"))
    most_popular = popular.sort_values("views_first_91_days",ascending=False).head(10)
    full_persistence = global_data.groupby(KEY).week.nunique().sort_values(ascending=False)
    metrics = {**metadata, "category_summary":category_summary.reset_index().to_dict("records"),
               "category_summary_excluding_staggered_launch_units":units.loc[~units.any_staggered_launch].groupby("category").agg(title_season_units=("observed_weeks","size"),mean_observed_weeks=("observed_weeks","mean")).reset_index().to_dict("records") if metadata['schedule_flags_available'] else [],
               "views_period_title_season_units":len(units),
               "peak_title":peaks.iloc[0].display_title,
               "peak_weekly_views":int(peaks.iloc[0].peak_weekly_views),
               "top_12_peak_films":int(peaks.category.str.startswith("Films").sum()),
               "country_week_coverage_min_countries":int(coverage.countries.min()),
               "country_week_coverage_max_countries":int(coverage.countries.max()),
               "top_country_breadth":breadth.iloc[0][["display_title","countries","country_week_appearances"]].to_dict(),
               "most_popular_91day_title":most_popular.iloc[0].display_title if len(most_popular) else None,
               "most_popular_91day_views":int(most_popular.iloc[0].views_first_91_days) if len(most_popular) else None,
               "full_period_max_observed_weeks":int(full_persistence.iloc[0]),
               "full_period_max_unit":{"category":full_persistence.index[0][0],"show_title":full_persistence.index[0][1],"season":full_persistence.index[0][2]}}
    return units,category_summary,peaks,breadth,most_popular,coverage,metrics


def style():
    plt.rcParams.update({"font.size":11,"figure.dpi":120,"axes.spines.top":False,
                         "axes.spines.right":False,"axes.titleweight":"bold"})


def plot_persistence(category_summary):
    style(); data=category_summary.sort_values("mean_observed_weeks")
    fig,ax=plt.subplots(figsize=(10,4.5))
    labels=[f"{i}\n(n={int(r.title_season_units)})" for i,r in data.iterrows()]
    bars=ax.barh(labels,data.mean_observed_weeks,color=[COLORS[i] for i in data.index])
    ax.bar_label(bars,fmt="%.2f",padding=5)
    ax.set(xlim=(0,data.mean_observed_weeks.max()*1.2),xlabel="Mean distinct weeks observed in the Global Top 10",
           title="Persistence differs when each title-season gets one vote")
    fig.text(.01,.01,"Common views-era window: 2023-06-18–2024-04-14. Observed chart appearances are not subscriber retention.",fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1));return fig


def plot_peaks(peaks):
    style();data=peaks.iloc[::-1];fig,ax=plt.subplots(figsize=(11,7))
    bars=ax.barh(data.display_title.str.replace(" — ","\n",regex=False),data.peak_weekly_views/1e6,color=[COLORS[i] for i in data.category])
    ax.bar_label(bars,fmt="%.1f",padding=4,fontsize=9)
    ax.set(xlim=(0,data.peak_weekly_views.max()/1e6*1.2),xlabel="Highest reported weekly views (millions)",
           title="Damsel leads this snapshot's weekly-view peaks")
    fig.text(.01,.01,"2023-06-18–2024-04-14. Views = hours / runtime, not unique viewers. Seasons remain separate.",fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1));return fig


def plot_breadth(breadth):
    style();data=breadth.iloc[::-1];fig,ax=plt.subplots(figsize=(11,7))
    bars=ax.barh(data.display_title.str.replace(" — ","\n",regex=False),data.countries,color="#176b87")
    ax.bar_label(bars,fmt="%.0f",padding=4,fontsize=9)
    ax.set(xlim=(0,105),xlabel="Distinct countries with at least one Top 10 appearance",
           title="Country breadth measures distribution, not audience size")
    fig.text(.01,.01,"2023-06-18–2024-04-14. Ties ordered by country-week appearances; no country view counts are published in this file.",fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1));return fig


def plot_tradeoff(units):
    style();fig,ax=plt.subplots(figsize=(10,5))
    for cat,color in COLORS.items():
        d=units[units.category.eq(cat)]
        ax.scatter(d.observed_weeks,d.peak_weekly_views/1e6,label=cat,color=color,alpha=.55,s=28)
    ax.set(xlabel="Distinct observed Global Top 10 weeks",ylabel="Peak reported weekly views (millions)",
           title="Peak reach and repeated chart appearances are different dimensions")
    ax.legend(fontsize=9)
    fig.text(.01,.01,"One mark per title-season, common 44-week views era. Selection and boundary censoring preclude causal or retention claims.",fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1));return fig


def save_validation(metrics):
    # I stop if a publisher revision changes the release's core claims, rather
    # than silently publish old interpretations beside new measurements.
    expected={"global_rows":5840,"country_rows":272260,"weeks":146,
              "views_period_weeks":44,"views_period_title_season_units":741,
              "peak_weekly_views":50800000,"top_12_peak_films":11}
    for key,value in expected.items():
        assert metrics[key]==value, f"Source revision changed {key}; review the narrative before release."
    expected_means=[440/222,440/198,440/173,440/148]
    assert np.allclose([r['mean_observed_weeks'] for r in metrics['category_summary']],expected_means)
    data={"status":"analysis_executed","validated_on":"2026-10-28","python":platform.python_version(),
          "packages":{p:importlib.metadata.version(p) for p in ["pandas","numpy","matplotlib","openpyxl","nbformat","nbclient","ipykernel"]},
          "sources_retrieved_on":"2026-10-28",
          "sources":["https://www.netflix.com/tudum/top10/", "https://about.netflix.com/en/news/top-10-things-about-netflix-top-10"],
          "metrics":metrics}
    (ROOT/"validation.json").write_text(json.dumps(data,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    g,c,p,m=load_and_audit(); *_,metrics=summarize(g,c,p,m);save_validation(metrics)
    print(json.dumps(metrics,indent=2))
