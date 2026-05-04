# Dongfang / Eastmoney Integration Note

Date: 2026-05-05

## 1. What the Dongfang CSV actually is

The CSV is not a manually curated dataset.
It is a snapshot exported from Eastmoney / 东方财富 market rankings.

In the original notebook, the CSV is produced by directly calling:

- `akshare.stock_hsgt_hold_stock_em(...)`

and then saving the returned table as CSV.

So the complete flow should be understood as:

- fetch live ranking data from Eastmoney via AKShare
- save raw CSV snapshot
- ingest CSV into InsightSync normalized schema
- derive company records and trigger signals

## 2. Problem found in the previous implementation

The first Dongfang integration added only the downstream import layer:

- import existing CSV
- normalize into `intelligence_records`
- generate `trigger_signals`
- create `companies`

That was useful for quickly consuming notebook output, but it was not a complete source implementation because:

- the project itself could not fetch Dongfang data
- ingestion depended on the user already having CSV files
- the pipeline was not end-to-end reproducible

## 3. Current design after this update

Dongfang now has two operating modes.

### 3.1 Import mode

Use this when CSV files already exist.

Collector:

- `DongfangCSVCollector`

CLI example:

```bash
python -m insightsync.data --sources dongfang --dongfang-csv-paths "C:\data\北向资金持股排行.csv,C:\data\沪股通持股排行.csv" --dongfang-snapshot-date 2026-05-01 --once
```

### 3.2 Fetch mode

Use this when the pipeline should fetch the rankings itself.

Collector:

- `DongfangAKShareCollector`

Internal fetch mechanism:

- call `akshare.stock_hsgt_hold_stock_em(...)`
- save raw CSV into `insightsync/data/storage/raw/dongfang_eastmoney/`
- reuse the same normalization and signal-generation logic as import mode

CLI example:

```bash
python -m insightsync.data --sources dongfang --dongfang-fetch --once
```

Optional explicit market selection:

```bash
python -m insightsync.data --sources dongfang --dongfang-fetch --dongfang-fetch-markets northbound,shanghai_connect,shenzhen_connect --once
```

Run southbound separately:

```bash
python -m insightsync.data --sources dongfang --dongfang-fetch --dongfang-fetch-markets southbound --once
```

## 4. Field mapping currently implemented

The current implementation maps the following Dongfang fields:

- `序号` -> `rank`
- `代码` -> `company_id`
- `名称` -> `company_name`
- `今日收盘价` -> `close_price`
- `今日涨跌幅` -> `price_change_pct`
- `今日持股-股数` -> `holding_shares`
- `今日持股-市值` -> `holding_value`
- `今日持股-占流通股比` -> `holding_float_ratio_pct`
- `今日持股-占总股本比` -> `holding_total_ratio_pct`
- `今日增持估计-股数` -> `increase_shares`
- `今日增持估计-市值` -> `increase_value`
- `今日增持估计-市值增幅` -> `increase_value_pct`
- `今日增持估计-占流通股比` -> `increase_float_ratio_pct`
- `今日增持估计-占总股本比` -> `increase_total_ratio_pct`
- `所属板块` -> `sector`
- `日期` -> `event_time`

## 5. Business usage currently covered

### 5.1 Prospect List support

The current ingestion can already support a first-pass prospect list by preserving:

- company identifiers
- sector
- capital-flow intensity
- holding depth
- ranking position

### 5.2 Trigger Signal support

The current implementation emits these candidate signals:

- `ranking`
- `estimated_increase_value`
- `holding_float_ratio_pct`
- `price_and_flow_resonance`
- `increase_float_ratio_pct`
- `sector_capital_presence`

These are suitable as first-stage candidate signals, not final business judgments.

## 6. What is still missing

Even after adding fetch mode, Dongfang integration is still not fully mature.

The following pieces are still missing:

- multi-day trend construction
- consecutive increase detection
- sector-level co-movement detection
- integration into `company latest-state`
- integration into `prospect scoring`
- product recommendation mapping

So the current status should be described as:

- end-to-end source ingestion is available
- company/prospect intelligence usage is partially enabled
- scoring and banker-facing action logic still need follow-up work

## 7. Recommended next steps

The correct next sequence is:

1. run real Dongfang fetch or import ingestion
2. inspect the actual SQLite output
3. sync to backend if needed
4. calibrate Dongfang-specific latest-state logic
5. add Dongfang features into prospect scoring

## 8. Current status of real run

At the time of this note:

- fetch mode code has been added
- import mode code has been added
- local unit tests cover import-mode normalization
- a real Dongfang ingestion run still depends on either:
  - working external network access for AKShare fetch, or
  - available real CSV snapshot files on disk

This means the source is now implemented, but the real run result still needs to be executed and validated in the current machine environment.
