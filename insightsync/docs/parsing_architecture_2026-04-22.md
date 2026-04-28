# InsightSync Parsing Architecture Update

Date: 2026-04-22

## 1. Why this milestone now

The project assessment correctly identified the biggest gap in the current solution:

- the repo can ingest many sources
- the repo can normalize and serve records
- but the repo still does not truly parse and understand source content

This is especially critical for Hang Seng's target use case because:

- company reports are not just files, they are evidence-rich business documents
- external sources will not always be PDFs
- future sources may be API payloads, database exports, crawled HTML, XBRL, scanned reports, or mixed-layout documents

So the next step should not be "just parse PDFs". It should be:

- build one reusable parsing layer for multi-source content
- expose one normalized parsed output schema
- make current RAG and downstream intelligence immediately benefit from that layer

## 2. What changed in this milestone

This milestone adds a new shared package:

- `insightsync/parsing/`

It introduces:

- a standard parse contract: `ParseRequest`
- a normalized parse result: `ParsedDocument`
- reusable structures for:
  - sections
  - tables
  - extracted metrics
  - risk factors
  - business events
  - management discussion summaries
- a registry-driven parser router
- first parser implementations for:
  - JSON / API payloads
  - HTML / crawled pages
  - file-based documents
  - plain text

It also upgrades the existing backend flow:

- `insightsync/backend/services/rag_document_builder.py` no longer only stringifies `payload_json`
- RAG documents now consume parsed text plus structured extractions when available
- RAG metadata now records parsing summary and parse version

## 3. Functional difference vs before

Before this change:

- RAG mostly indexed titles, summaries, signal text, and raw payload key-value pairs
- a PDF path in payload was only evidence that a file existed
- HTML and JSON payloads were not parsed into sections or reusable structured fields
- there was no unified extraction contract across source types

After this change:

- JSON/API payloads can be parsed into narrative sections, tables, metrics, risks, business events, and management discussion candidates
- HTML/crawled pages can be parsed into sections and HTML tables with cleaner main text extraction
- file-based sources can go through a document parser entry point instead of being treated as opaque metadata
- RAG receives richer content built from parsed text, not just raw payload serialization
- parsing warnings are preserved, which gives us traceability instead of silently pretending parsing succeeded

This is the first real step from "source ingestion" toward "content understanding".

## 4. Architecture

### 4.1 Flow

`ParseRequest` -> parser registry -> source-specific parser -> `ParsedDocument` -> RAG / downstream signals / fusion / scoring

### 4.2 Standard output

`ParsedDocument` is the key contract. It includes:

- parser name
- source kind
- media type
- title / summary
- normalized plain text
- sections
- tables
- extracted metrics
- extracted risk factors
- extracted business events
- management discussion summary
- warnings
- metadata

This matters because later steps like:

- signal generation
- company-level fusion
- scoring
- banker recommendations

should not each re-parse raw source payloads independently.

### 4.3 Parser routing

Current routing is intentionally simple but extensible:

- `DocumentParser`
  - file-backed sources
  - first entry point for PDF / text / CSV / future office docs
- `HTMLParser`
  - crawled HTML or article pages
- `JSONParser`
  - API/database payloads
- `TextParser`
  - plain text fallback

This allows future source onboarding without changing downstream consumers.

## 5. Best-practice research and how it informed the design

The design intentionally follows a layered best-practice approach instead of relying on one parser for every file type.

### 5.1 Multi-format document parsing

Recommended primary reference:

- Docling official docs: <https://docling-project.github.io/docling/>

Why it matters:

- strong fit for mixed-layout enterprise documents
- designed for document conversion across multiple formats
- relevant for OCR, layout-aware extraction, and table-aware parsing

Design implication:

- the current architecture includes a document parser entry point with optional Docling backend integration
- Docling is treated as an advanced backend, not a mandatory dependency, so the repo remains runnable now

### 5.2 Fast native PDF extraction

Recommended primary reference:

- PyMuPDF docs: <https://pymupdf.readthedocs.io/en/latest/>

Why it matters:

- very practical for fast text extraction from born-digital PDFs
- supports page-level text extraction
- supports table detection in modern versions

Design implication:

- current `DocumentParser` uses PyMuPDF when available for PDF text and table extraction
- this gives immediate value for digital PDFs without waiting for a full OCR stack

### 5.3 OCR for scanned reports

Recommended primary reference:

- OCRmyPDF docs: <https://ocrmypdf.readthedocs.io/en/latest/>

Why it matters:

- scanned annual reports and image PDFs are common
- OCR should be a dedicated preprocessing step, not hidden inside brittle regex logic

Design implication:

- the parser now emits explicit warnings when a PDF has little extractable text
- this prepares the pipeline for an OCR branch instead of silently indexing empty content

### 5.4 HTML main-text extraction

Recommended primary reference:

- Trafilatura docs: <https://trafilatura.readthedocs.io/>

Why it matters:

- crawled pages often contain heavy boilerplate
- article extraction quality is materially better when using a main-content extractor instead of raw `BeautifulSoup.get_text()`

Design implication:

- `HTMLParser` tries Trafilatura when available
- if unavailable, it falls back to a deterministic BeautifulSoup cleaner

### 5.5 Structured financial facts

Recommended primary reference:

- Arelle docs: <https://arelle.readthedocs.io/>

Why it matters:

- when XBRL or structured filings are available, regex extraction from prose should not be the only path
- reported financial facts should come from machine-readable facts whenever possible

Design implication:

- the new parsing architecture leaves a clear slot for an XBRL parser
- XBRL should become the preferred source for high-confidence financial facts in later phases

### 5.6 Schema validation

Recommended primary reference:

- Pydantic docs: <https://docs.pydantic.dev/latest/>

Why it matters:

- parsing pipelines degrade quickly if outputs are not strongly validated
- downstream fusion becomes fragile when each parser emits slightly different shapes

Design implication:

- even though this milestone uses dataclass-based normalized models for lightweight adoption, the contract is explicit
- a future phase should promote critical parse outputs and event schemas to Pydantic validation at persistence boundaries

## 6. Current extraction quality: honest assessment

This milestone improves architecture and immediate utility, but it does not magically solve semantic accuracy.

Current structured extraction for:

- metrics
- risk factors
- business events
- management discussion summaries

is still mostly deterministic and heuristic.

That means:

- it is more reusable than ad-hoc payload keyword scans
- it is more testable than hiding logic inside prompts
- but it is not yet the final accuracy ceiling

So the honest answer is:

- yes, parts of signal association and information fusion are still rule/keyword driven today
- yes, that can become subjective or brittle if left as the final solution
- no, this milestone does not claim that heuristics are enough

What this milestone does is create the correct foundation so we can improve accuracy in a controlled way:

- parse once
- normalize once
- validate once
- then evolve extraction quality on top of a stable contract

## 7. Why this architecture is better than source-specific scripts

Without a shared parsing layer, the project would keep drifting into:

- one-off parsing code inside each connector
- duplicated logic for section splitting and table handling
- inconsistent outputs across PDF, JSON, and HTML
- no shared quality checks

With the new layer:

- source onboarding becomes cheaper
- structured outputs become reusable
- RAG quality improves immediately
- later LLM extraction can consume normalized sections and tables instead of raw blobs

## 8. Known limitations in the current implementation

This is an important milestone, but not the final parsing solution.

Current limitations:

- advanced PDF parsing depends on optional libraries being installed
- OCR is not yet wired into an end-to-end preprocessing workflow
- XBRL parsing is not yet implemented
- management discussion summarization is heuristic, not LLM-assisted
- financial metric extraction is still regex/table heuristic, not statement-aware
- HTML extraction still needs site-specific tuning for some sources
- parsed results are currently used by RAG immediately, but not yet persisted as first-class backend tables

## 9. Recommended next steps

Priority 1:

- persist parsed artifacts as first-class data objects
- add parse status, parser backend, parse timestamp, warning count, and quality flags

Priority 2:

- add production-grade PDF stack
- PyMuPDF for born-digital PDFs
- OCRmyPDF + Tesseract for scanned PDFs
- Docling for mixed-layout, Office docs, and richer table/layout extraction

Priority 3:

- add XBRL ingestion path using Arelle
- treat XBRL as high-confidence financial facts

Priority 4:

- replace heuristic management discussion and event extraction with hybrid extraction
- rules for deterministic anchors
- LLM or structured model extraction for ambiguity resolution
- evidence spans kept for auditability

Priority 5:

- add evaluation datasets for:
  - section segmentation quality
  - table extraction quality
  - metric extraction precision / recall
  - risk factor precision
  - business event extraction precision

Priority 6:

- connect parsed outputs into:
  - company-level intelligence fusion
  - prospect scoring
  - banker action recommendation

## 10. Files added or changed in this milestone

- `insightsync/parsing/__init__.py`
- `insightsync/parsing/models.py`
- `insightsync/parsing/base.py`
- `insightsync/parsing/utils.py`
- `insightsync/parsing/structured.py`
- `insightsync/parsing/registry.py`
- `insightsync/parsing/parsers/__init__.py`
- `insightsync/parsing/parsers/text_parser.py`
- `insightsync/parsing/parsers/json_parser.py`
- `insightsync/parsing/parsers/html_parser.py`
- `insightsync/parsing/parsers/document_parser.py`
- `insightsync/backend/services/rag_document_builder.py`
- `insightsync/backend/tests/test_parsing.py`

## 11. Bottom line

This milestone does not finish company-report intelligence.

It does something more important first:

- it creates the reusable parsing substrate that every later intelligence feature depends on

That is the correct next step because:

- without it, report understanding would remain shallow
- without it, source expansion would keep increasing code duplication
- without it, later signal generation and fusion would remain overly subjective and hard to test

So this is not the final intelligence layer.

It is the foundation that makes the final intelligence layer buildable.
