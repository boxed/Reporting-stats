# Provenance for `annual_rocket_counts_seed.csv`

Year-by-year tally of rockets/mortars fired toward Israel, compiled from
publicly reported figures. This is the **finest granularity these free sources
actually publish** — annual. Nobody publishes a clean weekly count; weekly
resolution only comes from event-level datasets (UCDP GED, GTD, ACLED) or from
the operation-level episode spread in `rocket_episodes_seed.csv`.

## ⚠️ Read before using
- **Overwhelmingly Israeli-sourced.** Figures come from the Israel Security
  Agency (ISA/Shabak), the IDF, the Meir Amit / ITIC center, and the Jewish
  Virtual Library (which itself compiles ISA/IDF data). These are *launch*
  tallies by one party to the conflict — exactly the asymmetry this project
  exists to flag. Cross-check against UCDP/ACLED event counts before publishing.
- **Definitions shift between years/sources.** Some figures are rockets-only,
  others rockets+mortars (+Grad). Where a split was reported it is in the
  `rockets_approx` / `mortars_approx` columns; otherwise only `combined_approx`
  is filled. Do not treat the combined column as a single consistent definition.
- **Launches ≠ impacts.** Many projectiles fell short inside Gaza or were
  intercepted; these are fired counts, not landings or casualties.
- **2023 spans definitions.** ">12,000" is the Oct–Dec Gaza figure; the Oct 7
  opening barrage alone is reported between ~3,000 (IDF) and ~5,000 (Hamas claim).
- **2024 is deliberately blank.** Post-Oct-7 fire became multi-front (Hezbollah,
  Houthis, Iran's direct strikes). The widely-cited ~26,000 "since Oct 7" figure
  is an all-fronts total and is **not** comparable to the Gaza-origin series.

## Per-figure sources (compiled via web search; full pages were not fetchable
## from this network-restricted environment, so values are from search snippets
## of the pages below and should be verified against the primary page).
- **2001–2012 annual rockets:** [Jewish Virtual Library — Number of Rocket Attacks from Gaza 2001-2012](https://www.jewishvirtuallibrary.org/number-of-rocket-attacks-from-gaza-2001-2012);
  [JVL — Rocket & Mortar Attacks Against Israel by Year](https://www.jewishvirtuallibrary.org/rocket-mortar-attacks-against-israel-by-year)
- **2009 / 2010 ISA splits (569+289; 150+215):** Israel Security Agency annual
  summaries, via [Wikipedia — Palestinian rocket attacks on Israel](https://en.wikipedia.org/wiki/Palestinian_rocket_attacks_on_Israel)
- **2011 (~680):** ISA annual summary (rockets+mortars+Grad).
- **2013 (63 / 36 attacks), 2015–2017 (sporadic):** ITIC annual data via Wikipedia.
- **2014 Protective Edge (3,852 rockets + 712 mortars):** [UN OCHA 2014 key figures](https://www.ochaopt.org/content/key-figures-2014-hostilities); ISA.
- **2018 (~1,000):** [Jerusalem Post — IDF annual report: 1,000 rockets fired in 2018](https://www.jpost.com/arab-israeli-conflict/idf-1000-rockets-fired-at-southern-israel-from-gaza-over-the-past-year-575871)
- **2019 (~1,295):** [JNS — IDF data shows rocket attacks up in 2019](https://www.jns.org/idf-data-shows-rocket-attacks-up-terror-attacks-down-in-2019/)
- **2020 (176):** [Xinhua — Past year sees lowest number of rockets from Gaza (Israeli PM)](https://english.news.cn/20220607/d25999f3c27a48e582b003dbcb6ff03a/c.html)
- **2021 Guardian of the Walls (~4,360):** [ITIC — Operation Guardian of the Walls summary](https://www.terrorism-info.org.il/en/escalation-from-the-gaza-strip-operation-guardian-of-the-walls-summary/)
- **2022 Breaking Dawn (~1,100):** ITIC / IDF via Wikipedia.
- **2023 (>12,000 Oct–Dec; 9,500 by 9 Nov):** [Times of Israel — IDF: 9,500 rockets since Oct 7](https://www.timesofisrael.com/liveblog_entry/idf-9500-rockets-fired-at-israel-since-oct-7-including-3000-in-1st-hours-of-onslaught/);
  [Middle East Journal — Under Constant Fire](https://www.mideastjournal.org/post/how-many-rockets-fired-at-israel)
- **2024 all-fronts (~26,000 since Oct 7):** [Times of Israel — A year of war: 26,000 rockets fired at Israel](https://www.timesofisrael.com/a-year-of-war-idf-data-shows-726-troops-killed-over-26000-rockets-fired-at-israel/)

Last compiled: 2026-06-30 (via web search; pages not directly fetchable here).
