# 0003. HTTP data layer, no Selenium

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

The original CLI scraped the Academic Calendar with Selenium + headless Chrome and
fragile CSS/XPath selectors. Shared cPanel hosting cannot reliably run Chrome/chromedriver,
and DOM-selector scraping is brittle. Investigation found:

- The **Timetable Builder** exposes an undocumented JSON API
  (`https://api.easi.utoronto.ca/ttb`) returning catalog + live schedule + enrolment.
- The **Academic Calendar** is server-rendered Drupal HTML reachable with GET params.

Both are consumable with plain HTTP — verified live (see the smoke test and TTB reference).

## Decision

Build the data layer on **`requests`/`urllib`** (JSON for TTB) and **BeautifulSoup**
(Calendar HTML). **No Selenium, no browser automation.**

## Consequences

- Runs on cPanel with no browser; faster and far more reliable.
- Depends on an undocumented API that could change — mitigated by the smoke test and by
  isolating all TTB knowledge in one client module.
- Must handle API quirks (404 = empty results; prereq text is HTML).
- Reversing (re-adding Selenium) is explicitly disallowed unless hosting changes.
