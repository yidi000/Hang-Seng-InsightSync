# InsightSync Scoring Governance And Evaluation

Date: 2026-05-11

## 1. Core Position

The current scoring layer should be treated as an explainable first-version scorecard, not as a statistically validated credit or sales model.

That is acceptable for a prototype only if every score is:

- evidence-linked
- decomposed into named features
- constrained by linkage strength
- calibrated against labeled cases over time
- reviewed separately from GenAI prose output

The practical goal is not to remove judgment on day one. The goal is to make judgment explicit, testable, and replaceable.

## 2. How To Reduce Subjectivity

### Step 1: Separate Evidence From Judgment

Keep these layers separate:

- raw source item
- extracted fact
- trigger signal
- company linkage
- decision feature
- score
- recommendation text

No final recommendation should be generated directly from raw text without passing through these layers.

### Step 2: Use A Controlled Linkage Taxonomy

Every external signal must declare why it applies to a company:

- `direct_company_link`: company is named or uniquely identified
- `industry_link`: applies through sector exposure
- `region_link`: applies through geography
- `cross_border_exposure_link`: applies through overseas, trade, FX, or corridor exposure
- `macro_context_link`: background only

Scientific rule:

- strong direct evidence can drive company-level scoring
- medium contextual evidence can support a hypothesis
- weak macro evidence can explain context but should not create high priority on its own

### Step 3: Make Features Measurable

Each score input needs a feature contract:

- feature name
- business meaning
- allowed evidence types
- allowed linkage types
- calculation formula
- cap
- expected direction
- example positive and negative cases

Example:

`cross_border_operating_exposure`

- meaning: evidence of cross-border operations, trade flow, overseas expansion, or treasury exposure
- allowed evidence: company filings, business events, announcements, trade-related market signals
- preferred linkage: `direct_company_link` or `cross_border_exposure_link`
- direction: higher means stronger cross-border product relevance
- guardrail: `macro_context_link` alone cannot score this feature

### Step 4: Score Confidence Separately

Do not hide evidence quality inside the opportunity score.

Maintain a separate `evidence_confidence_score` based on:

- direct evidence ratio
- strong linkage ratio
- structured extraction coverage
- source diversity
- freshness
- parser quality warnings

This prevents a company with attractive but weakly linked context from being over-ranked.

## 3. Calibration Roadmap

### Phase 0: Rule Audit

Current state.

Use expert-defined rules, but document every feature and expose score breakdowns.

Required artifacts:

- feature dictionary
- linkage taxonomy
- score breakdown in API output
- deterministic unit tests

Current API contract:

- prospect responses expose `score_breakdown.scorecard_version`
- `score_breakdown.calibration_status` is currently `expert_defined_unvalidated_v0`
- `score_breakdown.llm_score_assignment` is `not_used_for_final_score`
- `score_breakdown.score_inputs` repeats the final score inputs used for the prospect ranking
- `score_breakdown.linkage_quality` reports direct evidence ratio, scoreable evidence ratio, context-only count, and linkage-type counts
- `score_breakdown.governance_flags` surfaces cases where confidence, linkage, opportunity, or risk logic needs review

### Phase 1: Expert-Labeled Case Set

Create a small labeled set of 50-100 company cases.

Labels should include:

- priority: high / medium / monitor
- opportunity lens: acquisition / financing / cross-border / risk-review
- evidence quality: strong / medium / weak
- product fit: relevant / uncertain / not relevant
- linkage correctness: correct / too strong / too weak / wrong

Use at least two reviewers when possible. Track reviewer disagreement instead of hiding it.

Useful metrics:

- agreement rate
- Cohen's kappa or simple pairwise agreement
- false high-priority rate
- missed high-priority rate
- linkage overreach rate

### Phase 2: Weight And Threshold Tuning

Tune weights against the labeled set.

Use simple and defensible methods first:

- grid search over feature weights
- pairwise ranking loss
- precision at top K
- recall of high-priority cases
- ablation by feature group

Recommended targets:

- high priority should have high precision
- monitor should have low false-negative risk only if evidence coverage is good
- macro-only cases should rarely enter high priority
- risk-heavy cases should route to review rather than aggressive outreach

### Phase 3: Outcome Calibration

If real downstream outcomes become available, calibrate against business results:

- RM accepted / rejected recommendation
- meeting booked
- product discussion started
- financing opportunity opened
- account opened
- risk event observed
- manual override reason

At this stage the scorecard can be compared with statistical models, but the model should still preserve explainable feature outputs.

## 4. GenAI Role In Scoring

GenAI should not directly output the final score.

Allowed GenAI roles:

- extract structured facts from reports and news
- suggest linkage rationale with citations
- summarize why a feature may apply
- review whether a linkage or product hypothesis is too aggressive
- generate RM-ready explanations after the score is computed

Disallowed GenAI roles:

- assign final priority score without feature evidence
- silently override linkage type
- create product recommendations without cited supporting facts
- treat broad market news as company-specific evidence without rationale

## 5. Evaluation Assets In This Repository

Current multilingual parsing evaluation set:

- `insightsync/data/evaluation/multilingual_parsing_cases.json`

Current identity/linkage evaluation set:

- `insightsync/data/evaluation/company_identity_linkage_cases.json`

Current tests:

- `insightsync/backend/tests/test_multilingual_parsing_eval.py`
- `insightsync/data/tests/test_company_identity_linkage_eval.py`

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ENABLE_LLM_GENERATION=false python -m pytest insightsync/backend/tests/test_multilingual_parsing_eval.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest insightsync/data/tests/test_company_identity_linkage_eval.py -q
```

Current coverage:

- English report-style management discussion
- simplified Chinese report-style management discussion
- traditional Chinese report-style management discussion
- Cantonese-style traditional Chinese market update
- metric extraction
- risk extraction
- business event extraction
- management discussion detection
- English display-name identity matching
- simplified Chinese and traditional Chinese alias identity matching
- numeric stock-code boundary matching
- ambiguous alias and generic-company negative cases

This is a starting point, not a full benchmark.

## 6. Recommended Next Evaluation Set

Add cases in this order:

1. HKEX annual report excerpts in English and traditional Chinese
2. CNINFO/SZSE announcements in simplified Chinese
3. Hong Kong Government and InvestHK news in English/traditional Chinese/simplified Chinese
4. Cantonese-style business summaries or RM notes
5. negative cases where no company-level opportunity should be inferred
6. macro-only cases that must remain weak context
7. ambiguous aliases and subsidiaries for company linkage tests

Each case should include expected:

- extracted metrics
- risk categories
- business event types
- company linkage type
- whether the evidence is scoreable
- expected opportunity lens
- expected priority band

## 7. Practical Answer To "Is This Too Subjective?"

Yes, the first version is partly subjective because weights and feature definitions start from expert judgment.

The defensible approach is:

1. make the subjective assumptions explicit
2. prevent weak context from dominating strong direct evidence
3. expose feature-level score breakdowns
4. measure extraction/linkage quality with labeled cases
5. tune weights and thresholds against reviewer labels and later business outcomes
6. keep GenAI out of final score assignment

That makes the system scientific enough for an early prototype and gives a clear path toward empirical validation.
