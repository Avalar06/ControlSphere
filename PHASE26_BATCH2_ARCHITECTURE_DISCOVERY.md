# ControlSphere — Batch 2 Architecture Discovery Specification

**Document Identifier**: `PHASE26_BATCH2_ARCHITECTURE_DISCOVERY.md`
**Batch Identifier**: `BATCH-2-KRI-APPETITE`
**Module Name**: `KRI-APPETITE-GRC`
**Target Migration**: `0023_kri_and_risk_appetite_governance.py`
**Current Migration Head**: `0022` (`0022_audit_fieldwork_and_sampling.py`)
**Git Baseline**: Commit `a3e9b4ab6926789479399e0e56df7138a7640c40` (main, clean, pushed)
**Security Model**: Production Enterprise RBAC (Exact 6 Platform Roles, Zero Role Inflation)
**Four-Eyes Model**: Hard Enforcement (`requester != approver`, `breach_owner != closer`)
**Compliance Standards**: ISO 31000:2018 (Risk Management), COSO ERM 2017, NIST CSF 2.0 (GV.RM-01, GV.RM-02 Risk Appetite & Tolerance)
**Discovery Gate Status**: **ARCHITECTURE DISCOVERY COMPLETE**

---

## 1. Executive Summary

Batch 2 (`KRI-APPETITE-GRC`) establishes the proactive early-warning and risk tolerance governance layer of ControlSphere. In enterprise GRC ecosystems, managing risk cannot rely solely on lagging indicators such as post-mortem audit findings (Phase 4/Batch 1) or static semi-annual risk matrix reviews (Phase 5). Organizations require:
1. **Dynamic Key Risk Indicators (KRIs)**: Observable, leading metrics measuring changes in risk exposure before material loss events occur.
2. **Enterprise Risk Appetite & Tolerance Framework**: Board-approved appetite statements and operational tolerance bands synthesizing Phase 5 qualitative ratings (1–25 heatmap scores) with Phase 12 financial quantification limits (ALE/VaR-95).
3. **Automated & Governed Breach Detection**: Server-authoritative comparison of time-series observations against directional warning/critical thresholds.
4. **Governed Breach Lifecycle & Four-Eyes Signoff**: Non-repudiable state machine (`DETECTED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `ESCALATED` $\rightarrow$ `RECOVERED` $\rightarrow$ `CLOSED`) preventing unverified breach dismissal.
5. **Executive & Continuous GRC Telemetry**: High-level exposure telemetry feeding Phase 20 Executive Dossiers and Phase 23 Continuous Assurance drift monitoring.

This discovery specification establishes the authoritative, tamper-resistant architectural foundation for Batch 2 while rigorously preserving the integrity of existing domain authorities (Risk in Phase 5, QuantRisk in Phase 12, Finding in Phase 4, and Evidence in Phase 3).

---

## 2. Repository Ground Truth & Verified Baseline

All discovery findings are derived directly from the authoritative repository state inspected on the local file system and remote tracking branch:

| Attribute | Verified Ground Truth | Verification Source |
| :--- | :--- | :--- |
| **Repository Remote** | `https://github.com/Avalar06/ControlSphere.git` | `git remote -v` |
| **Active Branch** | `main` (synchronized with `origin/main`) | `git status` |
| **Git HEAD Commit** | `a3e9b4ab6926789479399e0e56df7138a7640c40` | `git rev-parse HEAD` |
| **Commit Message** | `feat(batch1): implement audit fieldwork governance` | `git log -1 --oneline` |
| **Working Tree** | Clean (Zero uncommitted code changes, zero unstaged files) | `git status --short` |
| **Alembic Revision Head** | `0022` (`0022_audit_fieldwork_and_sampling.py`) | `alembic heads` |
| **Backend Test Baseline** | **999 / 999 Passing Tests (100% Pass Rate)** | `pytest tests/ -q` |
| **Platform Roles** | Exactly 6: `ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER` | `backend/app/core/permissions.py` |
| **Next Target Migration** | `0023_kri_and_risk_appetite_governance.py` (Revises: `0022`) | Alembic migration sequence |

---

## 3. Current Risk Authority (Phase 5 Inspection)

The authoritative Risk management engine is implemented in Phase 5:
- **Authoritative Entity**: `Risk` in [`backend/app/models/risk.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/risk.py).
- **Service Orchestrator**: `RiskService` in [`backend/app/services/risk_service.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/services/risk_service.py).
- **Mathematical Scoring Engine**: [`backend/app/core/risk_engine.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/core/risk_engine.py).
  - Inherent Risk: $\text{Impact} \in [1, 5] \times \text{Likelihood} \in [1, 5] = \text{Score} \in [1, 25]$.
  - Bands: `LOW` (1–4), `MODERATE` (5–9), `HIGH` (10–16), `CRITICAL` (17–25).
  - Residual Risk: $\text{Residual Impact} \in [1, 5] \times \text{Residual Likelihood} \in [1, 5] = \text{Residual Score} \in [1, 25]$.
  - Appetite Status: Calculated by `calculate_appetite_status(score, target_band)` returning `WITHIN_APPETITE`, `NEAR_LIMIT`, or `ABOVE_APPETITE`.
- **Lifecycle & Governance**:
  - `status`: `IDENTIFIED`, `ASSESSED`, `TREATMENT_PLANNED`, `MITIGATING`, `MONITORING`, `ACCEPTED`, `CLOSED`.
  - `treatment_strategy`: `MITIGATE`, `TRANSFER`, `AVOID`, `ACCEPT`, `NOT_SPECIFIED`.
  - Upstream/Downstream Lineage: `RiskControlLink` (to `organization_controls`), `RiskFindingLink` (to Phase 4 `findings`).
  - Formal Risk Acceptance: `risk_acceptance_justification`, `risk_accepted_at`, `risk_accepted_by_id`, `risk_acceptance_expiry`.

### Non-Negotiable Boundary:
Batch 2 **MUST NOT** create a `Risk2` or duplicate risk matrix calculation. KRIs will link directly to existing `Risk` records and provide real-time objective indicators that dynamically inform the risk's monitoring and appetite status.

---

## 4. Current QuantRisk Authority (Phase 12 Inspection)

The authoritative quantitative cyber risk quantification engine is implemented in Phase 12:
- **Authoritative Entities**: [`backend/app/models/quant_risk.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/quant_risk.py):
  - `QuantitativeRiskScenario`: Loss model implementing Beta-PERT Threat Event Frequency (TEF), Threat Capability (TCAP), Control Strength (CS), Vulnerability Factor ($V = \text{TCAP} \times (1 - \text{CS})$), Primary Loss (PL), Secondary Loss (SL), Single Loss Expectancy (SLE), Annualized Loss Expectancy (ALE), and parametric/empirical VaR-95/VaR-99.
  - `QuantitativeSimulationRun`: Empirical Monte Carlo simulation engine executing 100–50,000 trials with pseudo-random seed recording and percentile derivation.
  - `RosiAnalysis`: Return on Security Investment calculator linking scenarios to Phase 11 `RemediationPlan`.
  - `FinancialRiskAppetite`: Board-approved financial boundaries (`ale_limit`, `var_95_limit`, `version`, `status` [DRAFT, APPROVED, SUPERSEDED]) with Four-Eyes rule (`requested_by_id != approved_by_id`).
- **Service Orchestrator**: `QuantumGrcService` in [`backend/app/services/quantum_grc_service.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/services/quantum_grc_service.py).
- **Portfolio Aggregation**: `get_portfolio_overview` evaluates `portfolio_ale` and `portfolio_var_95` against approved `FinancialRiskAppetite`, setting `AppetiteBreachStateEnum` (`WITHIN_APPETITE`, `EXCEEDS_ALE`, `EXCEEDS_VAR`, `EXCEEDS_BOTH`).

### Non-Negotiable Boundary:
Batch 2 **MUST NOT** duplicate FAIR calculations or Monte Carlo simulation routines. Instead:
- QuantRisk scenario metrics (ALE, VaR-95, LEF) serve as **telemetry sources** for KRIs.
- `FinancialRiskAppetite` acts as the financial component of the broader enterprise Risk Appetite framework.

---

## 5. Existing Telemetry & Metric Architecture

ControlSphere already possesses domain-specific telemetry mechanisms across several phases:
1. **Phase 7 Continuous Control Monitoring**: `ControlHealthSnapshot` logs point-in-time scores (0–100) based on evidence freshness, assessment currency, and finding penalties. `ComplianceDriftAlert` tracks SLA failures.
2. **Phase 20 Executive GRC**: `ExecutiveSnapshot` aggregates tenant-wide inherent risk index, residual risk index, ALE exposure, audit readiness index, and compliance scores.
3. **Phase 22 Universal Integration Engine**: `EvidenceCollectionJob` and `EvidenceCollectionRun` ingest external data payloads, computing SHA-256 payload hashes, record counts, and provenance manifests.
4. **Phase 23 Continuous Assurance**: `ContinuousComplianceProfile` and `ComplianceDriftRecord` track multi-vector compliance drift across 5 vectors.
5. **Phase 1 Audit Logging**: `AuditService.log(...)` records immutable tenant audit logs with actor identity, action, resource type, IP address, and JSON details.

**Finding**: There is no generic, decoupled metric registry for operational risk indicators. Batch 2 provides this dedicated KRI registry without replicating Phase 22 connectors or Phase 7 control health scoring.

---

## 6. KRI Domain Definition

In ControlSphere, a Key Risk Indicator (KRI) represents a quantifiable operational, technical, or business measurement tracked over time to indicate the probability or impact of a risk event.

To prevent table overloading, Batch 2 decomposes KRI into four clean, normalized entities:

```
┌─────────────────────────────────┐
│       RiskAppetiteStatement     │  (Strategic tolerance policy per risk domain)
└────────────────┬────────────────┘
                 │ governs
                 ▼
┌─────────────────────────────────┐
│        KeyRiskIndicator         │  (Immutable metric definition & metadata)
└────────┬───────────────┬────────┘
         │ monitors      │ defines
         ▼               ▼
┌─────────────────┐  ┌─────────────────┐
│   KriRiskLink   │  │   KriThreshold  │  (Amber warning & Red critical limits)
└─────────────────┘  └────────┬────────┘
                              │ evaluates against
                              ▼
┌─────────────────────────────────┐
│          KriObservation         │  (Time-series measurement reading)
└────────────────┬────────────────┘
                 │ triggers (if breached)
                 ▼
┌─────────────────────────────────┐
│         KriBreachRecord         │  (Governed breach lifecycle event)
└─────────────────────────────────┘
```

### Core KRI Definition Attributes:
- `kri_code`: Unique identifier per tenant (e.g. `KRI-CYBER-001`).
- `name`: Human-readable label (e.g. "Unpatched Critical Vulnerabilities Older Than 30 Days").
- `description`: Operational intent and rationale.
- `risk_category`: Enum aligned with Phase 5 `RiskCategoryEnum` (`CYBERSECURITY`, `COMPLIANCE`, `OPERATIONAL`, `FINANCIAL`, `THIRD_PARTY`, etc.).
- `unit_of_measure`: Unit label (e.g. `COUNT`, `PERCENTAGE`, `CURRENCY_USD`, `DAYS`, `RATIO`).
- `directionality`: Enum governing threshold comparison:
  - `LOWER_IS_BETTER`: Breach occurs when metric rises above threshold (e.g. vulnerability count, downtime).
  - `HIGHER_IS_BETTER`: Breach occurs when metric falls below threshold (e.g. patch rate %, training completion %).
  - `WITHIN_RANGE`: Breach occurs when metric falls outside an acceptable interval.
- `measurement_frequency`: Expected observation cadence (`HOURLY`, `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`).
- `data_source_type`: Provenance classification (`AUTOMATED_INTEGRATION`, `INTERNAL_CALCULATED`, `MANUAL_ENTRY`, `API_INGESTION`).
- `calculation_expression`: Optional server-evaluated formula or query descriptor.
- `is_active`: Operational status flag.

---

## 7. Risk Appetite Domain Definition

Risk appetite is the aggregate amount and type of risk an organization is willing to pursue or retain in pursuit of its strategic objectives. Risk tolerance is the tactical boundary of acceptable variation around an appetite target.

### Unified Appetite Architecture:
1. **Qualitative Appetite (Phase 5 Alignment)**: Target risk bands (`LOW`, `MODERATE`, `HIGH`) configured per risk category.
2. **Quantitative Appetite (Phase 12 Alignment)**: Financial exposure ceilings (`ale_limit`, `var_95_limit`) formally approved by board leadership.
3. **Operational Tolerance (Batch 2 Addition)**: Exact threshold limits configured on individual KRIs that represent real-time boundary violations.

```
┌───────────────────────────────────────────────────────────────┐
│                   ENTERPRISE RISK APPETITE                    │
│                                                               │
│   Strategic Boundary: Max Acceptable Category Risk Band       │
│   Financial Boundary: Max Tenant Portfolio ALE & VaR-95       │
│   Operational Boundary: Metric Tolerance Bands (Warning/Red)   │
└───────────────────────────────────────────────────────────────┘
```

---

## 8. Threshold Architecture

Thresholds define the deterministic mathematical boundaries evaluated upon observation ingestion.

### Authoritative Directional Comparison Formulas:

#### A. `LOWER_IS_BETTER` (e.g., Unpatched CVEs, Failed Logins, Vendor Risk Score):
$$\text{Status} = \begin{cases}
\text{NORMAL} & \text{if } V < T_{\text{warning}} \\
\text{WARNING} & \text{if } T_{\text{warning}} \le V < T_{\text{critical}} \\
\text{CRITICAL} & \text{if } V \ge T_{\text{critical}}
\end{cases}$$

#### B. `HIGHER_IS_BETTER` (e.g., Backup Success %, Control Effectiveness %, SLA Compliance %):
$$\text{Status} = \begin{cases}
\text{NORMAL} & \text{if } V > T_{\text{warning}} \\
\text{WARNING} & \text{if } T_{\text{critical}} < V \le T_{\text{warning}} \\
\text{CRITICAL} & \text{if } V \le T_{\text{critical}}
\end{cases}$$

#### C. `WITHIN_RANGE` (e.g., Server Utilization %, Capital Adequacy Ratio):
$$\text{Status} = \begin{cases}
\text{NORMAL} & \text{if } T_{\text{min\_normal}} \le V \le T_{\text{max\_normal}} \\
\text{WARNING} & \text{if } (T_{\text{min\_warning}} \le V < T_{\text{min\_normal}}) \lor (T_{\text{max\_normal}} < V \le T_{\text{max\_warning}}) \\
\text{CRITICAL} & \text{if } V < T_{\text{min\_warning}} \lor V > T_{\text{max\_warning}}
\end{cases}$$

### Strict Invariant:
All threshold mathematics are computed **exclusively on the backend** by deterministic service methods. Clients can never supply pre-calculated breach states.

---

## 9. Observation Architecture

An observation is an immutable point-in-time measurement record:
- `id`: Primary key.
- `organization_id`: Mandatory tenant identifier.
- `kri_id`: Foreign key to `key_risk_indicators.id`.
- `observed_at`: Exact timestamp when the metric measurement occurred in the source environment (UTC).
- `ingested_at`: Server timestamp when ControlSphere recorded the reading (UTC).
- `metric_value`: Normalized 64-bit IEEE floating-point value.
- `source_type`: `MANUAL_ENTRY`, `API_INGESTION`, `INTEGRATION_CONNECTOR`, or `INTERNAL_CALCULATED`.
- `source_identifier`: Identifier of provider, sensor, or authenticated user.
- `quality_status`: `VALID`, `STALE`, `SUSPECT`, or `OUT_OF_BOUNDS`.
- `provenance_hash_sha256`: Cryptographic digest:
  $$\text{SHA-256}(\text{org\_id} \mathbin{\Vert} \text{kri\_id} \mathbin{\Vert} \text{observed\_at} \mathbin{\Vert} \text{metric\_value} \mathbin{\Vert} \text{source\_id})$$
- `evaluated_status`: `NORMAL`, `WARNING`, `CRITICAL`.
- `raw_payload_json`: Optional raw metadata for audit inspection.

Observations are **append-only**. Updating or deleting historical observations is prohibited to maintain complete evidentiary integrity for regulatory auditors.

---

## 10. Breach Architecture

A breach is an authoritative governance event generated when a KRI observation violates the critical tolerance threshold:
- **Entity**: `KriBreachRecord`.
- **Relationship**: Links to `key_risk_indicators`, `kri_observations`, and the specific breached threshold.
- **De-duplication / Hysteresis**:
  - If a KRI is already in an open `DETECTED`, `ACKNOWLEDGED`, or `ESCALATED` breach state, subsequent critical observations attach to the existing active breach record rather than generating a flood of duplicate breach records.
  - A new breach record is only created if the prior breach was formally `RECOVERED` or `CLOSED`.

### Breach Lifecycle State Machine:

```
                  ┌──────────────┐
                  │   DETECTED   │
                  └──────┬───────┘
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
     ┌──────────────┐        ┌──────────────┐
     │ ACKNOWLEDGED │        │  ESCALATED   │ ──► Creates Phase 4 Finding
     └───────┬──────┘        └───────┬──────┘     or Phase 11 RemediationPlan
             │                       │
             └───────────┬───────────┘
                         ▼
                  ┌──────────────┐
                  │  RECOVERED   │ (Metric returns within tolerance)
                  └──────┬───────┘
                         │
                         ▼  (Four-Eyes verification)
                  ┌──────────────┐
                  │    CLOSED    │
                  └──────────────┘
```

---

## 11. KRI $\rightarrow$ Risk Relationship

The relationship between KRIs and Risks is **Many-to-Many**:
- A single KRI (e.g. "Downtime Hours of Core Database") can impact multiple risks (e.g. "Risk of Business Interruption", "Risk of Customer SLA Penalty").
- A single Risk (e.g. "Risk of Unauthorized Data Exfiltration") can be tracked by multiple KRIs (e.g. "DLP Egress Volume", "Failed IAM Authentications", "Unpatched High-Severity CVEs").

### Junction Table: `kri_risk_links`
- `organization_id`: Foreign key with `CASCADE`.
- `kri_id`: Foreign key to `key_risk_indicators.id`.
- `risk_id`: Foreign key to `risks.id`.
- `correlation_weight`: Float value in $[0.0, 1.0]$ representing impact weight.
- `notes`: Justification for linkage.
- Unique Constraint: `(kri_id, risk_id)`.

### Optional Control Linkage: `kri_control_links`
- Allows KRIs measuring technical control effectiveness to link directly to Phase 2 `organization_controls`.

---

## 12. QuantRisk $\rightarrow$ KRI Relationship

QuantRisk outputs seamlessly feed the KRI engine without duplicate modeling:

```
┌──────────────────────────────────────────────┐
│           Phase 12 QuantRisk Engine          │
│                                              │
│  - QuantitativeRiskScenario.ale              │
│  - QuantitativeRiskScenario.var_95           │
│  - FinancialRiskAppetite.ale_limit           │
│  - QuantumGrcService.get_portfolio_overview  │
└──────────────────────┬───────────────────────┘
                       │ automated periodic observation sync
                       ▼
┌──────────────────────────────────────────────┐
│             Batch 2 KRI Registry             │
│                                              │
│  KRI: "Enterprise Cyber ALE Exposure ($)"    │
│  KRI: "Portfolio Value at Risk 95th ($)"     │
│  Value Source: INTERNAL_CALCULATED (Phase 12)│
└──────────────────────────────────────────────┘
```

The KRI engine treats QuantRisk as a first-class upstream calculation provider. When portfolio ALE exceeds the approved `FinancialRiskAppetite.ale_limit`, an automated `KriBreachRecord` is logged against the financial KRI.

---

## 13. Data Quality Controls

Data quality rules prevent false positives and corrupted risk reports:
1. **Missing Data**: If no observation is received within $1.5 \times \text{measurement\_frequency}$, the KRI state is marked `STALE_DATA` and flagged with a warning indicator. Missing data is **never silently coerced to 0.0**.
2. **Out-of-Bounds Validation**: Each KRI defines `min_allowable_value` and `max_allowable_value` (e.g., percentage metrics are constrained to $[0.0, 100.0]$). Ingestion outside this range is rejected with `HTTP 422 Unprocessable Content`.
3. **Idempotency & Duplicate Rejection**: Ingestion requests with identical `(kri_id, observed_at, metric_value)` are detected using `provenance_hash_sha256` and de-duplicated idempotently.
4. **Timezone Standardization**: All observations require ISO-8601 UTC timestamps. Offset-naive timestamps are rejected.

---

## 14. Time-Series Semantics

1. **Temporal Ordering**: Observations are indexed and queried strictly by `observed_at DESC, id DESC`.
2. **Current Value Resolution**: The active metric reading is deterministically resolved as the latest valid observation where $\text{observed\_at} \le \text{current\_utc\_time}$.
3. **Aggregation Windows**: Rolling trend calculations support standard windows:
   - `LAST_7_DAYS`, `LAST_30_DAYS`, `LAST_90_DAYS`, `YEAR_TO_DATE`.
   - Aggregation functions: `CURRENT`, `AVERAGE`, `MIN`, `MAX`, `PERCENT_CHANGE`.
   - All aggregation math is executed server-side via SQL aggregate functions.

---

## 15. Executive GRC Integration (Phase 20)

Batch 2 directly enhances Phase 20 Executive GRC:
- **`executive_snapshots` Telemetry Extension**:
  - `active_kri_breaches_count`: Total active red breaches across the organization.
  - `kri_warning_count`: Total active amber warning KRIs.
  - `appetite_utilization_index`: Normalized percentage $[0.0, 100.0]$ measuring aggregate exposure against tolerance ceilings.
- **`executive_dossiers` Inclusion**:
  - KRI summary cards and breach incident tables automatically embed into generated board reporting packages.

---

## 16. Continuous Assurance Integration (Phase 23)

Batch 2 integrates bidirectionally with Phase 23 Continuous Assurance:
- **Drift Vector Contribution**: A critical KRI breach can automatically register a `ComplianceDriftRecord` under a new drift vector `RISK_APPETITE_BREACH`.
- **Continuous Assurance Score Penalty**: The overall assurance score in `continuous_assurance_snapshots` incorporates active KRI breach counts as a weighted penalty, ensuring board metrics immediately reflect real-time operational risk spikes.

---

## 17. Notification & Audit Log Integration

- **Alerting Model**: ControlSphere does not use a separate messaging broker. When a KRI transitions into `WARNING` or `CRITICAL`, alerting occurs via:
  1. High-priority audit logging via `AuditService.log(...)` with action `kri.breach_detected` or `kri.warning_triggered`.
  2. In-app badge alerts in the UI navigation and executive telemetry views.
  3. Integration webhook dispatch if Phase 22 connectors are configured.
- **Non-Repudiation Audit Trail**:
  All KRI actions (`create`, `update_threshold`, `ingest_observation`, `acknowledge_breach`, `escalate_breach`, `close_breach`) generate structured `AuditLog` records containing tenant ID, actor email, IP address, and payload diffs.

---

## 18. Four-Eyes Governance Model

Four-Eyes segregation of duties is enforced at critical risk management boundaries:
1. **Appetite Statement Approval**:
   - `requested_by_id != approved_by_id`.
   - The user proposing an appetite statement or modifying threshold limits cannot approve their own proposal.
2. **Breach Closure & Dismissal**:
   - `breach.acknowledged_by_id != closer_id` or `kri.owner_id != closer_id`.
   - An analyst who caused or owns a breached metric cannot unilaterally close or dismiss the breach record without independent verification by an `ADMIN` or `MANAGER`.

---

## 19. RBAC Matrix (Exact 6 Roles Only)

ControlSphere preserves its **exact 6 platform roles** with zero role inflation:

### New Fine-Grained Permissions in `app/core/permissions.py`:
- `Permission.KRI_READ = "kri:read"`
- `Permission.KRI_MANAGE = "kri:manage"`
- `Permission.KRI_INGEST = "kri:ingest"`
- `Permission.KRI_APPETITE_MANAGE = "kri:appetite_manage"`
- `Permission.KRI_APPETITE_APPROVE = "kri:appetite_approve"`
- `Permission.KRI_BREACH_ACKNOWLEDGE = "kri:breach_acknowledge"`
- `Permission.KRI_BREACH_CLOSE = "kri:breach_close"`

### Role Mapping:

| Permission | ADMIN | MANAGER | GRC_ANALYST | SECURITY_ANALYST | AUDITOR | VIEWER |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `kri:read` | Yes | Yes | Yes | Yes | Yes | Yes |
| `kri:manage` | Yes | Yes | Yes | Yes | No | No |
| `kri:ingest` | Yes | Yes | Yes | Yes | No | No |
| `kri:appetite_manage` | Yes | Yes | Yes | No | No | No |
| `kri:appetite_approve` | Yes | Yes | No | No | No | No |
| `kri:breach_acknowledge` | Yes | Yes | Yes | Yes | No | No |
| `kri:breach_close` | Yes | Yes | No | No | No | No |

---

## 20. Multi-Tenancy & Anti-IDOR Boundary

1. **Mandatory Tenant Ownership**: Every Batch 2 table (`risk_appetite_statements`, `key_risk_indicators`, `kri_thresholds`, `kri_observations`, `kri_breach_records`, `kri_risk_links`) declares:
   ```python
   organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
   ```
2. **Server-Derived Context**:
   `organization_id` is never accepted from request bodies or client URL parameters. It is bound strictly from the authenticated JWT session (`current_user.organization_id`).
3. **Anti-Enumeration 404 Invariant**:
   All cross-tenant queries return `HTTP 404 Not Found` rather than `HTTP 403 Forbidden` to prevent tenant ID and metric enumeration.

---

## 21. Concurrency & Idempotency Controls

- **Observation Ingestion**: Protected by unique constraint on `(organization_id, kri_id, observed_at, metric_value)` using `provenance_hash_sha256`. Concurrent duplicate requests resolve idempotently without double-counting.
- **Breach Generation Race Condition**: Handled via `.with_for_update()` row-level locking on the parent `KeyRiskIndicator` during observation evaluation.
- **Threshold Modification Race Condition**: When an administrator updates thresholds, active breach evaluation runs in an atomic database transaction to prevent reading inconsistent partial threshold states.

---

## 22. Candidate Data Model

### Table 1: `risk_appetite_statements`
- `id`: Integer PK.
- `organization_id`: Integer FK (`organizations.id`, `CASCADE`).
- `category`: Enum (`RiskCategoryEnum`).
- `statement_code`: String(64) indexed (e.g. `APPETITE-CYBER-2026`).
- `title`: String(255).
- `appetite_statement`: Text.
- `target_band`: String(20) (`LOW`, `MODERATE`, `HIGH`).
- `status`: String(50) (`DRAFT`, `APPROVED`, `SUPERSEDED`).
- `version`: Integer default 1.
- `requested_by_id`: Integer FK (`users.id`).
- `approved_by_id`: Integer FK (`users.id`, nullable).
- `approved_at`: DateTime(timezone=True).
- `created_at`, `updated_at`: DateTime(timezone=True).
- Unique: `(organization_id, statement_code)`.

### Table 2: `key_risk_indicators`
- `id`: Integer PK.
- `organization_id`: Integer FK (`organizations.id`, `CASCADE`).
- `appetite_statement_id`: Integer FK (`risk_appetite_statements.id`, `SET NULL`, nullable).
- `kri_code`: String(64) indexed (e.g. `KRI-IAM-001`).
- `name`: String(255).
- `description`: Text.
- `risk_category`: Enum (`RiskCategoryEnum`).
- `unit_of_measure`: String(50).
- `directionality`: String(30) (`LOWER_IS_BETTER`, `HIGHER_IS_BETTER`, `WITHIN_RANGE`).
- `measurement_frequency`: String(30) (`DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`).
- `data_source_type`: String(50) (`MANUAL_ENTRY`, `API_INGESTION`, `INTEGRATION_CONNECTOR`, `INTERNAL_CALCULATED`).
- `min_allowable_value`: Float nullable.
- `max_allowable_value`: Float nullable.
- `current_value`: Float nullable.
- `current_status`: String(30) default `NORMAL` (`NORMAL`, `WARNING`, `CRITICAL`, `STALE_DATA`).
- `last_observed_at`: DateTime(timezone=True) nullable.
- `owner_id`: Integer FK (`users.id`, `SET NULL`, nullable).
- `is_active`: Boolean default True.
- `created_by_id`: Integer FK (`users.id`).
- `created_at`, `updated_at`: DateTime(timezone=True).
- Unique: `(organization_id, kri_code)`.

### Table 3: `kri_thresholds`
- `id`: Integer PK.
- `organization_id`: Integer FK (`organizations.id`, `CASCADE`).
- `kri_id`: Integer FK (`key_risk_indicators.id`, `CASCADE`).
- `warning_threshold`: Float nullable (Amber boundary).
- `critical_threshold`: Float nullable (Red boundary).
- `range_min_normal`: Float nullable (for `WITHIN_RANGE`).
- `range_max_normal`: Float nullable (for `WITHIN_RANGE`).
- `effective_date`: Date.
- `version`: Integer default 1.
- `created_by_id`: Integer FK (`users.id`).
- `created_at`, `updated_at`: DateTime(timezone=True).
- Unique: `(kri_id, version)`.

### Table 4: `kri_observations`
- `id`: Integer PK.
- `organization_id`: Integer FK (`organizations.id`, `CASCADE`).
- `kri_id`: Integer FK (`key_risk_indicators.id`, `CASCADE`).
- `observed_at`: DateTime(timezone=True) indexed.
- `ingested_at`: DateTime(timezone=True).
- `metric_value`: Float.
- `source_type`: String(50).
- `source_identifier`: String(255).
- `quality_status`: String(30) default `VALID`.
- `provenance_hash_sha256`: String(64) indexed.
- `evaluated_status`: String(30) (`NORMAL`, `WARNING`, `CRITICAL`).
- `raw_payload_json`: Text nullable.
- `ingested_by_id`: Integer FK (`users.id`, `SET NULL`, nullable).
- `created_at`: DateTime(timezone=True).
- Unique: `(organization_id, kri_id, observed_at, metric_value)`.

### Table 5: `kri_breach_records`
- `id`: Integer PK.
- `organization_id`: Integer FK (`organizations.id`, `CASCADE`).
- `kri_id`: Integer FK (`key_risk_indicators.id`, `CASCADE`).
- `observation_id`: Integer FK (`kri_observations.id`, `CASCADE`).
- `breach_code`: String(64) indexed (e.g. `BREACH-2026-001`).
- `status`: String(50) default `DETECTED` (`DETECTED`, `ACKNOWLEDGED`, `ESCALATED`, `RECOVERED`, `CLOSED`).
- `breach_value`: Float.
- `threshold_value`: Float.
- `detected_at`: DateTime(timezone=True).
- `acknowledged_at`: DateTime(timezone=True) nullable.
- `acknowledged_by_id`: Integer FK (`users.id`, `SET NULL`, nullable).
- `acknowledgement_notes`: Text nullable.
- `escalated_at`: DateTime(timezone=True) nullable.
- `escalated_finding_id`: Integer FK (`findings.id`, `SET NULL`, nullable).
- `recovered_at`: DateTime(timezone=True) nullable.
- `closed_at`: DateTime(timezone=True) nullable.
- `closed_by_id`: Integer FK (`users.id`, `SET NULL`, nullable).
- `closure_notes`: Text nullable.
- `created_at`, `updated_at`: DateTime(timezone=True).
- Unique: `(organization_id, breach_code)`.

### Table 6: `kri_risk_links`
- `id`: Integer PK.
- `organization_id`: Integer FK (`organizations.id`, `CASCADE`).
- `kri_id`: Integer FK (`key_risk_indicators.id`, `CASCADE`).
- `risk_id`: Integer FK (`risks.id`, `CASCADE`).
- `correlation_weight`: Float default 1.0.
- `created_at`: DateTime(timezone=True).
- Unique: `(kri_id, risk_id)`.

---

## 23. Candidate API Architecture

All endpoints mounted under `/api/v1/kri`:

### 1. Risk Appetite Statements
- `POST /api/v1/kri/appetites`: Create draft appetite statement (`KRI_APPETITE_MANAGE`).
- `GET /api/v1/kri/appetites`: List appetite statements (`KRI_READ`).
- `GET /api/v1/kri/appetites/{id}`: Get appetite statement details (`KRI_READ`).
- `POST /api/v1/kri/appetites/{id}/approve`: Four-Eyes approval (`KRI_APPETITE_APPROVE`).

### 2. KRI Registry
- `POST /api/v1/kri/indicators`: Define new KRI (`KRI_MANAGE`).
- `GET /api/v1/kri/indicators`: List KRIs with multi-criteria filtering (`KRI_READ`).
- `GET /api/v1/kri/indicators/{id}`: Retrieve KRI details and latest metrics (`KRI_READ`).
- `PUT /api/v1/kri/indicators/{id}`: Update KRI configuration (`KRI_MANAGE`).
- `POST /api/v1/kri/indicators/{id}/thresholds`: Update threshold limits (`KRI_MANAGE`).
- `POST /api/v1/kri/indicators/{id}/links/risks`: Link KRI to Phase 5 Risk (`KRI_MANAGE`).
- `DELETE /api/v1/kri/indicators/{id}/links/risks/{risk_id}`: Unlink KRI from Risk (`KRI_MANAGE`).

### 3. Telemetry Ingestion & Observations
- `POST /api/v1/kri/indicators/{id}/observations`: Ingest metric reading (`KRI_INGEST`).
- `GET /api/v1/kri/indicators/{id}/observations`: List time-series observations (`KRI_READ`).
- `GET /api/v1/kri/indicators/{id}/trend`: Retrieve aggregated trend time-series (`KRI_READ`).

### 4. Breach Management
- `GET /api/v1/kri/breaches`: List active and historical breaches (`KRI_READ`).
- `GET /api/v1/kri/breaches/{id}`: Retrieve breach record details (`KRI_READ`).
- `POST /api/v1/kri/breaches/{id}/acknowledge`: Formal breach acknowledgment (`KRI_BREACH_ACKNOWLEDGE`).
- `POST /api/v1/kri/breaches/{id}/escalate`: Escalate breach to Phase 4 `Finding` (`KRI_BREACH_ACKNOWLEDGE`).
- `POST /api/v1/kri/breaches/{id}/close`: Four-Eyes breach closure (`KRI_BREACH_CLOSE`).

### 5. Portfolio & Executive Overview
- `GET /api/v1/kri/overview`: Summary stats for dashboards and board reporting (`KRI_READ`).

---

## 24. Candidate Frontend Architecture

1. **Dedicated Workspace (`/kri`)**:
   - `frontend/src/pages/KriManagementPage.tsx`: Primary operational dashboard with tabs:
     - `Dashboard`: Portfolio health, active breaches, appetite utilization heatmap.
     - `Indicators Register`: Searchable table with status badges (`NORMAL`, `WARNING`, `CRITICAL`, `STALE`), category chips, and sparklines.
     - `Breach Inbox`: Actionable triage queue for open breaches.
     - `Appetite Statements`: Board-level policy statements and Four-Eyes approval modal.
2. **KRI Detail & Trend Modal**:
   - `frontend/src/components/kri/KriDetailModal.tsx`: Time-series chart (SVG / Recharts / Victory), threshold horizontal lines, observation history, and linked risk cards.
3. **Cross-Module Deep Integration**:
   - `RiskDetailPage.tsx`: Embedded "Monitored KRIs" card showing leading indicators for that risk.
   - `QuantRiskPage.tsx`: Embedded KRI sync status for financial exposure indicators.
   - `ExecutiveDashboardPage.tsx`: KRI breach widget and appetite utilization gauge.

---

## 25. Anti-Duplication Matrix

| Proposed Capability | Relationship to Existing Engine | Architectural Decision | Rationale |
| :--- | :--- | :--- | :--- |
| **Risk Register** | Phase 5 `Risk` & `RiskService` | **REUSE / EXTEND** | Zero `Risk2`. KRIs link to existing risks via `kri_risk_links`. |
| **Quant Risk Modeling** | Phase 12 `QuantitativeRiskScenario` & `QuantumGrcService` | **REUSE / CONSUME** | Zero duplicate FAIR/Monte Carlo logic. ALE/VaR are ingested as KRI observations. |
| **Finding Engine** | Phase 4 `Finding` & `FindingService` | **REUSE / EXTEND** | Zero duplicate finding tables. KRI breach escalation creates authoritative Phase 4 `Finding`. |
| **Audit Logging** | Phase 1 `AuditLog` & `AuditService` | **REUSE** | All KRI governance actions use standard `AuditService.log()`. |
| **Connectors & Integrations**| Phase 22 `IntegrationConnection` | **REUSE** | No duplicate connector framework. External telemetry flows through Phase 22 jobs. |
| **Control Health Scoring** | Phase 7 `ControlHealthSnapshot` | **REUSE / CONSUME** | Control health scores feed KRIs as operational metrics without re-calculating health. |
| **Remediation Plans** | Phase 11 `RemediationPlan` | **REUSE** | KRI breaches link to existing remediation plans. |
| **Executive Dossiers** | Phase 20 `ExecutiveSnapshot` | **EXTEND** | KRI breach counts and appetite indexes feed executive snapshots. |

---

## 26. Security Threat Model (Adversarial Matrix Preview)

A preliminary 20-vector security matrix is defined for Batch 2:

1. **SEC-B2-01 (Cross-Tenant KRI Query)**: Org B queries Org A KRI $\rightarrow$ `HTTP 404 Not Found`.
2. **SEC-B2-02 (Cross-Tenant Observation Ingestion)**: Org B attempts to submit observation to Org A KRI $\rightarrow$ `HTTP 404 Not Found`.
3. **SEC-B2-03 (Four-Eyes Appetite Self-Approval)**: Requester attempts to approve own appetite statement $\rightarrow$ `HTTP 400 Bad Request`.
4. **SEC-B2-04 (Four-Eyes Breach Self-Closure)**: KRI owner attempts to close own critical breach without manager signoff $\rightarrow$ `HTTP 400 Bad Request`.
5. **SEC-B2-05 (Client Calculation Injection)**: Client attempts to supply pre-computed breach status $\rightarrow$ Ignored, computed server-authoritative.
6. **SEC-B2-06 (Out-of-Bounds Metric Rejection)**: Client posts negative percentage value $\rightarrow$ `HTTP 422 Unprocessable Content`.
7. **SEC-B2-07 (Duplicate Ingestion Idempotency)**: Identical telemetry payload replayed $\rightarrow$ De-duplicated, zero state corruption.
8. **SEC-B2-08 (Future Observation Timestamp Rejection)**: Client posts observation timestamp in the future $\rightarrow$ `HTTP 422 Unprocessable Content`.
9. **SEC-B2-09 (Client Org ID Tampering)**: Injected `organization_id=999` in payload $\rightarrow$ Overridden by JWT session context.
10. **SEC-B2-10 (Unauthorized Breach Modification by Viewer)**: `VIEWER` role calls breach acknowledge $\rightarrow$ `HTTP 403 Forbidden`.
11. **SEC-B2-11 (Stale Data Auto-Detection)**: Observation overdue beyond frequency $\rightarrow$ Status transitions to `STALE_DATA`.
12. **SEC-B2-12 (Threshold Race Condition Safety)**: Concurrent observation evaluation during threshold update $\rightarrow$ Handled atomically.
13. **SEC-B2-13 (Authoritative Finding Link Integrity)**: Escalate breach creates verified Phase 4 `Finding` and links FK.
14. **SEC-B2-14 (Duplicate Finding Escalation Prevention)**: Repeated escalation on same breach $\rightarrow$ `HTTP 409 Conflict`.
15. **SEC-B2-15 (Cross-Tenant Risk Linkage Injection)**: Org A KRI attempts link to Org B Risk $\rightarrow$ `HTTP 404 Not Found`.
16. **SEC-B2-16 (Illegal Breach State Machine Transition)**: Transition directly from `DETECTED` to `CLOSED` $\rightarrow$ `HTTP 400 Bad Request`.
17. **SEC-B2-17 (Provenance Hash Tamper Detection)**: Modified observation row detected via mismatch with SHA-256 hash.
18. **SEC-B2-18 (QuantRisk Financial Appetite Desync)**: Inconsistent appetite limits rejected with validation error.
19. **SEC-B2-19 (Non-Existent KRI Ingestion)**: Post to invalid KRI ID $\rightarrow$ `HTTP 404 Not Found`.
20. **SEC-B2-20 (Observation Immutability Enforcement)**: Attempt to update or delete past observation $\rightarrow$ Endpoint non-existent (`HTTP 405 Method Not Allowed`).

---

## 27. Migration Boundary

- **Migration ID**: `0023_kri_and_risk_appetite_governance.py`
- **Revises**: `0022`
- **Tables Created**:
  1. `risk_appetite_statements`
  2. `key_risk_indicators`
  3. `kri_thresholds`
  4. `kri_observations`
  5. `kri_breach_records`
  6. `kri_risk_links`
- **Indexes**: Explicit B-tree indexes on `(organization_id, kri_code)`, `(kri_id, observed_at)`, `(organization_id, breach_code)`, and foreign keys.
- **Foreign Keys**: Enforced cascade deletes for tenant isolation; `SET NULL` on user references to preserve audit history upon user deactivation.
- **Downgrade Safety**: Clean table drops in strict reverse dependency order.

---

## 28. Batch Boundary Analysis

### Evaluation of Options:

#### Option 1: One Integrated Batch (`BATCH-2-KRI-APPETITE`)
- **Scope**: KRI Registry + Appetite Statements + Thresholds + Observations + Breach Lifecycle + Risk/QuantRisk Integrations.
- **Coupling**: Highly coupled domain. A KRI without thresholds cannot evaluate; an observation without a KRI has no context; a breach without a KRI has no lineage.
- **Migration**: A single atomic migration `0023`.
- **Productivity**: Enables a unified vertical slice with one staging inspection and single Git checkpoint.
- **Verdict**: **STRONGLY RECOMMENDED**.

#### Option 2: Two Batches (2A: KRI Registry & Ingestion, 2B: Appetite & Breaches)
- **Defects**: In 2A, KRIs would have no thresholds or breach evaluation, creating dead-end UI and incomplete user journeys. Requires two separate database migrations and double the checkpoint overhead.
- **Verdict**: REJECTED.

#### Option 3: Three Batches (2A: KRI, 2B: Ingestion, 2C: Breaches)
- **Defects**: Hyper-fragmentation with excessive overhead.
- **Verdict**: REJECTED.

### Boundary Decision:
**KEEP AS ONE INTEGRATED BATCH: `BATCH-2-KRI-APPETITE`**.

---

## 29. Future Batch Compatibility

Batch 2 strictly respects the upcoming platform roadmap:
- **Batch 3 (`DATA-GOVERNANCE-GRC`)**: Batch 2 does not create generic data catalog or classification engines.
- **Batch 4 (`OBLIGATION-TRUST-GRC`)**: Batch 2 does not create customer trust portals or compliance attestations.
- **Batch 5 (`ADVANCED-ASSURANCE-GRC`)**: Batch 2 leaves automated control testing scripts and continuous audit workflows intact.

---

## 30. Productivity & Execution Model

Following the proven Batch 1 development model:
1. **Architecture Discovery**: Complete (this document).
2. **Batch Hardening**: Produce `PHASE26_BATCH2_ARCHITECTURE_HARDENED.md` specifying exact schemas, endpoint signatures, and mathematical formulas.
3. **Implementation**: Atomic vertical slice (backend schemas, services, models, migration 0023, frontend components, and tests).
4. **Adversarial Security**: 20-vector security test suite verifying anti-IDOR, SoD, and threshold determinism.
5. **Full Platform Regression**: 100% pass across all existing 999 tests + Batch 2 tests.
6. **Frontend Production Build**: Clean `tsc -b && vite build` (exit code 0).
7. **Single Git Checkpoint**: Stage, commit, and push.

---

## 31. Risks and Unknowns

| Risk / Unknown | Impact | Architectural Mitigation |
| :--- | :--- | :--- |
| High observation ingestion volume | DB table bloat in `kri_observations` | Clean indexing on `(kri_id, observed_at)`; optional partitioning in future if needed. |
| Inconsistent metric units across sources | Invalid comparison against thresholds | Mandatory `unit_of_measure` declaration with strict validation rules. |
| Stale telemetry masking risk deterioration | Blindness to increasing operational risk | Automated `STALE_DATA` status flagging if observation interval is breached. |
| Alert fatigue from frequent threshold oscillations | Operational noise | Breach de-duplication: active breach persists until formal recovery or closure. |

---

## 32. Final Architecture Gate

### Gate Verification Checklist:
- [x] Risk authority clearly identified (Phase 5 `Risk`, zero `Risk2`).
- [x] QuantRisk authority clearly identified (Phase 12 `QuantitativeRiskScenario` & `FinancialRiskAppetite`, zero duplicate calculations).
- [x] KRI domain definition clean and non-overloaded.
- [x] Risk appetite and tolerance hierarchy mathematically defined.
- [x] Directional threshold evaluation formulas authoritative and server-side.
- [x] Observation time-series semantics immutable and append-only.
- [x] Breach lifecycle state machine and Four-Eyes boundaries established.
- [x] No duplicate finding or evidence engines required.
- [x] Multi-tenant isolation and anti-enumeration 404 model preserved.
- [x] Exact 6 platform roles preserved with zero role inflation.
- [x] Single migration boundary (`0023_kri_and_risk_appetite_governance.py`) confirmed.
- [x] Integrated single-batch scope justified and selected.

---

## 33. Final Verdict

**GO — BATCH 2 READY FOR HARDENING**
