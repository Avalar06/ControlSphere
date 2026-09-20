# ControlSphere — Batch 2 Architecture Hardening Specification

**Document Identifier**: `PHASE26_BATCH2_ARCHITECTURE_HARDENED.md`
**Batch Identifier**: `BATCH-2-KRI-APPETITE`
**Module Name**: `KRI-APPETITE-GRC`
**Target Migration**: `0023_kri_and_risk_appetite_governance.py`
**Alembic Head Baseline**: `0022` (`0022_audit_fieldwork_and_sampling.py`)
**Git Baseline**: Commit `a3e9b4ab6926789479399e0e56df7138a7640c40` (main, clean, pushed)
**Security Model**: Production Enterprise RBAC (Exact 6 Platform Roles, Zero Role Inflation)
**Four-Eyes Model**: Hard Enforcement (`requested_by_id != approved_by_id`, `closer_id != acknowledged_by_id`, `closer_id != kri.owner_id`)
**Cryptographic Integrity**: SHA-256 Digest over Canonical Ingestion Payload
**Compliance Standards**: ISO 31000:2018 (Clause 6.4.3 *Risk Criteria & Appetite*), COSO ERM 2017 (*Governance and Culture / Strategy & Objective-Setting*), NIST CSF 2.0 (GV.RM-01, GV.RM-02 *Risk Appetite & Tolerance Definition*)
**Architecture Gate Status**: **GO — BATCH 2 READY FOR IMPLEMENTATION**

---

## 1. Executive Summary

Batch 2 (`KRI-APPETITE-GRC`) establishes the proactive, early-warning risk monitoring and risk tolerance governance layer of ControlSphere. In modern enterprise GRC platforms, managing organizational risk cannot depend exclusively on backward-looking lagging indicators such as post-mortem audit findings (Phase 4, Batch 1) or static, semi-annual qualitative risk matrix updates (Phase 5). Enterprises require:

1. **Dynamic Key Risk Indicators (KRIs)**: Measurable, observable, leading operational metrics that detect shifts in risk exposure before material loss events occur.
2. **Enterprise Risk Appetite & Tolerance Framework**: Board-ratified appetite policies defining acceptable risk bands across risk categories, bound to financial loss ceilings (Phase 12 FAIR/Monte Carlo ALE and VaR-95 limits).
3. **Deterministic Multi-Directional Threshold Evaluation**: Server-authoritative comparison of numerical observations against directional thresholds (`LOWER_IS_BETTER`, `HIGHER_IS_BETTER`, `WITHIN_RANGE`) with unambiguous boundary semantics.
4. **Governed Breach Lifecycle with Four-Eyes Segregation of Duties**: A tamper-evident state machine (`DETECTED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `ESCALATED` $\rightarrow$ `RECOVERED` $\rightarrow$ `CLOSED`) preventing unverified breach dismissal or self-approval.
5. **Deterministic Escalation Routing**: Clean architectural separation between control failures (escalated directly to Phase 4 `Finding` records) and broader operational exposures (tracked via linked Phase 5 `Risk` treatment plans), with zero duplicate domain engines.
6. **Executive & Continuous Assurance Telemetry**: Seamless feeding of active breach posture and appetite compliance metrics into Phase 20 Executive Snapshots and Phase 23 Continuous Assurance drift monitoring.

This hardened architecture specification establishes the definitive, mathematically verified, tamper-resistant contract for Batch 2.

---

## 2. Repository Ground Truth & Verified Baseline

All specifications, data contracts, and implementation sequences in this document are derived directly from the verified repository state:

| Attribute | Verified Ground Truth | Verification Source |
| :--- | :--- | :--- |
| **Repository Remote** | `https://github.com/Avalar06/ControlSphere.git` | `git remote -v` |
| **Active Branch** | `main` (synchronized with `origin/main`) | `git status` |
| **Git HEAD Commit** | `a3e9b4ab6926789479399e0e56df7138a7640c40` | `git rev-parse HEAD` |
| **Commit Message** | `feat(batch1): implement audit fieldwork governance` | `git log -1 --oneline` |
| **Working Tree** | Clean (Zero uncommitted code changes, zero unstaged files) | `git status --short` |
| **Alembic Revision Head** | `0022` (`0022_audit_fieldwork_and_sampling.py`) | `alembic heads` |
| **Backend Test Baseline** | **999 / 999 Passing Tests (100% Pass Rate)** | `pytest backend/tests/ -q` |
| **Platform Roles** | Exactly 6: `ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER` | `backend/app/core/permissions.py` |
| **Next Target Migration** | `0023_kri_and_risk_appetite_governance.py` (Revises: `0022`) | Alembic migration sequence |

---

## 3. Authority Hierarchy

To eliminate domain ambiguity and prevent competing definitions of risk tolerance, ControlSphere enforces an explicit, five-tier hierarchical authority model:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: STRATEGIC / ORGANIZATIONAL APPETITE (Batch 2 Authority)            │
│ Model: RiskAppetiteStatement (Table: risk_appetite_statements)              │
│ Scope: Board-approved maximum risk band per RiskCategoryEnum (LOW/MOD/HIGH) │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ governs
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: QUANTITATIVE FINANCIAL APPETITE (Phase 12 Authority)               │
│ Model: FinancialRiskAppetite (Table: financial_risk_appetites)              │
│ Scope: Board-approved dollar limits (ALE limit, VaR-95 limit)                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ constrains
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 3: INDIVIDUAL OPERATIONAL RISK TARGET (Phase 5 Authority)             │
│ Model: Risk (Table: risks)                                                  │
│ Scope: Target risk band (LOW/MOD/HIGH), Status: WITHIN/NEAR_LIMIT/ABOVE     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ monitored by
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 4: OPERATIONAL METRIC TOLERANCE (Batch 2 Authority)                   │
│ Models: KeyRiskIndicator, KriThreshold (Tables: key_risk_indicators, etc.)  │
│ Scope: Directional leading metrics, Amber (Warning) & Red (Critical) limits │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ breaches trigger
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 5: GOVERNED BREACH & REMEDIATION ROUTING (Batch 2 / Phase 4/11)       │
│ Model: KriBreachRecord (Table: kri_breach_records)                          │
│ Scope: State machine, Four-Eyes closure, Escalates to Finding OR Risk Plan  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Explicit Hierarchy Precedence Rules:
1. **Level 1 (Strategic Policy)** defines the organization's overarching risk posture per category (`RiskCategoryEnum`). It governs what residual risk band the board deems acceptable for that domain.
2. **Level 2 (Financial Limit)** operates as the quantitative financial loss pillar of the strategic appetite, governing maximum annualized exposure across simulated scenarios.
3. **Level 3 (Operational Risk)** applies the strategic policy to individual registered risks, where `Risk.target_risk_band` must not be set looser than the Category appetite without formal risk acceptance justification.
4. **Level 4 (KRI Metrics)** translates operational risk monitoring into observable numerical thresholds.
5. **Level 5 (Breach State)** governs tolerance violations and routes action without creating secondary risk or finding entities.

---

## 4. Risk Authority (Phase 5 Inspection & Boundaries)

- **Authoritative Entity**: `Risk` in [`backend/app/models/risk.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/risk.py).
- **Service Orchestrator**: `RiskService` in [`backend/app/services/risk_service.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/services/risk_service.py).
- **Core Scoring Engine**: [`backend/app/core/risk_engine.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/core/risk_engine.py).
  - Inherent Score: $\text{Impact} \in [1, 5] \times \text{Likelihood} \in [1, 5] = \text{Score} \in [1, 25]$.
  - Bands: `LOW` (1–4), `MODERATE` (5–9), `HIGH` (10–16), `CRITICAL` (17–25).
  - Appetite Status: `calculate_appetite_status(score, target_band)` $\rightarrow$ `WITHIN_APPETITE`, `NEAR_LIMIT`, `ABOVE_APPETITE`.
- **Pre-existing Lineage**: `RiskControlLink` (to `organization_controls`), `RiskFindingLink` (to `findings`).
- **Formal Acceptance**: `risk_acceptance_justification`, `risk_accepted_at`, `risk_accepted_by_id`, `risk_acceptance_expiry`.

### Architectural Boundary:
- Batch 2 **DOES NOT** create a `Risk2` or duplicate risk matrix calculation.
- KRIs link to `Risk` records via `KriRiskLink` (many-to-many with correlation metadata).
- KRI breaches dynamically update the linked `Risk`'s operational monitoring context, but do not overwrite the inherent/residual impact and likelihood assessment without an explicit analyst review.

---

## 5. QuantRisk Authority (Phase 12 Inspection & Boundaries)

- **Authoritative Entities**: [`backend/app/models/quant_risk.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/quant_risk.py):
  - `QuantitativeRiskScenario`: Loss model implementing Threat Event Frequency (TEF), Threat Capability (TCAP), Control Strength (CS), Vulnerability Factor ($V = \text{TCAP} \times (1 - \text{CS})$), Primary Loss (PL), Secondary Loss (SL), Single Loss Expectancy (SLE), Annualized Loss Expectancy (ALE), and parametric/empirical VaR-95/VaR-99.
  - `QuantitativeSimulationRun`: Monte Carlo simulation engine executing 100–50,000 trials.
  - `FinancialRiskAppetite`: Board-approved financial boundaries (`ale_limit`, `var_95_limit`, `version`, `status` [DRAFT, APPROVED, SUPERSEDED]) with Four-Eyes rule (`requested_by_id != approved_by_id`).
- **Service Orchestrator**: `QuantumGrcService` in [`backend/app/services/quantum_grc_service.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/services/quantum_grc_service.py).

### Architectural Boundary:
- Batch 2 **DOES NOT** duplicate OpenFAIR calculations, Beta-PERT parameters, or Monte Carlo routines.
- Quantitative financial outputs (e.g. simulated `annualized_loss_expectancy`, `var_95_empirical`, `loss_event_frequency`) can be ingested as `KriObservation` records for financial-category KRIs.
- Ingestion preserves strict provenance: `source_type="QUANTRISK_SIMULATION"`, `source_id=simulation_run.id`.

---

## 6. KRI Authority

ControlSphere strictly delineates the responsibilities of the KRI subsystem into four discrete architectural layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. DEFINITION LAYER: KeyRiskIndicator (Table: key_risk_indicators)          │
│ Owns: Metadata, code, unit, frequency, directionality, owner, category      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ generates
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. TELEMETRY LAYER: KriObservation (Table: kri_observations)                │
│ Owns: Immutable time-series value, timestamp, source provenance, SHA-256    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ evaluated by
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. EVALUATION LAYER: KriEvaluationService (Domain Service)                  │
│ Owns: Server-authoritative comparison of value against KriThreshold         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ triggers
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. GOVERNANCE LAYER: KriBreachRecord (Table: kri_breach_records)            │
│ Owns: Governed breach lifecycle, SoD closure, escalation to Finding / Risk  │
└─────────────────────────────────────────────────────────────────────────────┘
```

`KeyRiskIndicator` is never overloaded with observation history, transient calculation results, or breach resolution states.

---

## 7. Appetite Authority

### Explicit Answers to Architectural Decisions:
- **A. Is `RiskAppetiteStatement` a new authoritative policy layer?**
  **Yes**. It establishes the organization-wide risk posture by codifying board-approved qualitative appetite bands (`LOW`, `MODERATE`, `HIGH`) for each `RiskCategoryEnum`, along with governance metadata (board ratification date, review cadence, Four-Eyes approvals).
- **B. Is it merely a normalized layer over existing Risk fields?**
  **No**. `Risk.target_risk_band` represents the target for an individual specific operational risk. `RiskAppetiteStatement` provides the enterprise governance policy against which individual risk targets are calibrated.
- **C. Should existing Risk fields be extended instead?**
  **No**. Modifying `risks` table to hold enterprise appetite statements would violate 3NF and confuse entity boundaries.
- **D. How does `FinancialRiskAppetite` relate to `RiskAppetiteStatement`?**
  `FinancialRiskAppetite` remains the sole authority on dollar-denominated loss boundaries (`ale_limit`, `var_95_limit`). `RiskAppetiteStatement` references `financial_risk_appetite_id` as an optional foreign key, unifying qualitative and quantitative risk appetite under a single board briefing package.
- **E. Can multiple appetite authorities coexist?**
  **Yes, hierarchically**. Enterprise policy governs category band limits $\rightarrow$ Phase 12 governs dollar ceilings $\rightarrow$ Phase 5 governs individual risk targets.

---

## 8. Threshold Authority & Boundary Mathematics

Every KRI possesses an active `KriThreshold` defining two operational boundary tiers:
- **Amber Tier (Warning)**: Early warning indicator that risk is trending towards tolerance limits.
- **Red Tier (Critical / Breach)**: Risk tolerance exceeded; automatically instantiates or updates a `KriBreachRecord`.

### Directional Mathematical Evaluation Rules:

#### 1. `LOWER_IS_BETTER` (e.g. Unpatched CVEs, Employee Phish Click Rate, Production Incidents)
- **Normal (Green)**: $v \le T_{\text{warn}}$
- **Warning (Amber)**: $T_{\text{warn}} < v \le T_{\text{crit}}$
- **Critical / Breach (Red)**: $v > T_{\text{crit}}$
*Constraint*: $T_{\text{warn}} < T_{\text{crit}}$

#### 2. `HIGHER_IS_BETTER` (e.g. Backup Success Rate, SLA Compliance %, MFA Coverage %)
- **Normal (Green)**: $v \ge T_{\text{warn}}$
- **Warning (Amber)**: $T_{\text{crit}} \le v < T_{\text{warn}}$
- **Critical / Breach (Red)**: $v < T_{\text{crit}}$
*Constraint*: $T_{\text{crit}} < T_{\text{warn}}$

#### 3. `WITHIN_RANGE` (e.g. Target Server CPU Utilization 40%–80%, Inventory Buffers)
- Parameterized by $[T_{\text{warn\_min}}, T_{\text{warn\_max}}]$ and $[T_{\text{crit\_min}}, T_{\text{crit\_max}}]$.
- **Normal (Green)**: $T_{\text{warn\_min}} \le v \le T_{\text{warn\_max}}$
- **Warning (Amber)**: $v \in [T_{\text{crit\_min}}, T_{\text{warn\_min}}) \cup (T_{\text{warn\_max}}, T_{\text{crit\_max}}]$
- **Critical / Breach (Red)**: $v < T_{\text{crit\_min}}$ OR $v > T_{\text{crit\_max}}$
*Constraint*: $T_{\text{crit\_min}} < T_{\text{warn\_min}} < T_{\text{warn\_max}} < T_{\text{crit\_max}}$

### Strict Boundary Equality Semantics:
Equality (`v == T`) is evaluated deterministically as shown in the equations above. At exact boundary points, the system favors the safer state (e.g., in `LOWER_IS_BETTER`, hitting exactly $T_{\text{warn}}$ remains Normal/Green; hitting exactly $T_{\text{crit}}$ is Warning/Amber; only strictly exceeding $T_{\text{crit}}$ triggers a Critical Breach).

---

## 9. Observation Authority

- `KriObservation` models time-series telemetry data.
- **Append-Only Contract**: Observations are strictly immutable. No `UPDATE` or `DELETE` endpoints exist.
- **Cryptographic Provenance**: Every observation records `data_hash_sha256`, computed as:
  $$\text{SHA-256}\left(\text{canonical\_json}(\{kri\_id, value, unit, observed\_at, source\_type, source\_id\})\right)$$
- **Server Timestamps**:
  - `observed_at`: The historical or current instant the metric was measured in the source system.
  - `created_at`: The exact server UTC instant the record was ingested into ControlSphere.
  - Client timestamps where $\text{observed\_at} > \text{now} + 60\text{s}$ (clock skew tolerance) are rejected with `HTTP 422 Unprocessable Content`.

---

## 10. Breach Authority

A `KriBreachRecord` represents a **governed metric state event**, not a duplicate Finding or Risk:
1. **Breach Creation**: Instantiated automatically by `KriEvaluationService` when a newly ingested observation evaluates to `CRITICAL` under the active threshold.
2. **Breach Hysteresis (Anti-Duplication)**:
   - While a KRI has an **active** breach (`status` $\in \{\text{DETECTED}, \text{ACKNOWLEDGED}, \text{ESCALATED}\}$), subsequent observations that also evaluate to `CRITICAL` **DO NOT** create new breach records.
   - Instead, the active breach's `latest_observation_id`, `peak_value`, and `last_evaluated_at` fields are updated atomically.
3. **Recovery vs. Closure**:
   - If a new observation evaluates to `NORMAL` or `WARNING`, the active breach transitions to `RECOVERED`.
   - `RECOVERED` indicates numerical recovery only. The breach remains open for formal governance review until an authorized manager executes Four-Eyes `CLOSED` sign-off.

---

## 11. Provenance Contract

Every `KriObservation` must specify its origin via `source_type`:

| Source Type (`KriSourceTypeEnum`) | `source_id` Reference | Description |
| :--- | :--- | :--- |
| `MANUAL_ENTRY` | `users.id` | Operational analyst manual entry via UI modal. |
| `RISK_REVALUATION` | `risks.id` | Ingested following a formal Phase 5 risk assessment review. |
| `QUANTRISK_SIMULATION` | `quantitative_simulation_runs.id` | FAIR/Monte Carlo simulation run outputs. |
| `CCM_HEALTH_CHECK` | `control_health_snapshots.id` | Automated control testing pass/fail percentages from Phase 7. |
| `EVIDENCE_PIPELINE` | `evidence_items.id` | Ingested via automated integration collection from Phase 22. |
| `COMPLIANCE_DRIFT` | `compliance_drift_records.id` | Phase 23 continuous assurance drift magnitude. |
| `INTEGRATION_SYNC` | `integration_connections.id` | External telemetry connector sync (e.g. Jira, CrowdStrike, AWS). |

---

## 12. Time-Series Contract

- **All Timestamps**: Stored in PostgreSQL as `DateTime(timezone=True)` in UTC.
- **Reporting Intervals (`KriFrequencyEnum`)**: `HOURLY`, `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`.
- **Stale Data Auto-Detection**:
  - Let $\Delta t_{\text{cadence}}$ be the nominal duration of the KRI's frequency (e.g. 24h for `DAILY`).
  - Stale threshold: $\tau_{\text{stale}} = 1.5 \times \Delta t_{\text{cadence}}$.
  - If $\text{now} - \text{latest\_observed\_at} > \tau_{\text{stale}}$, the KRI's operational status is flagged as `STALE_DATA`.
  - A stale KRI retains its last evaluated breach state but displays a visual warning in executive dashboards.
- **Latest Observation Query**: Optimized via composite B-tree index `ix_kri_obs_kri_observed (kri_id, observed_at DESC)`.

---

## 13. Data Quality Contract

| Condition | Ingestion Behavior | System Action |
| :--- | :--- | :--- |
| **Missing Observation** | Allowed; does NOT coerce to 0. | If interval exceeded, transitions KRI to `STALE_DATA`. |
| **Null Value in Payload** | `HTTP 422 Unprocessable Content`. | Payload validation error. Metric value must be a valid float. |
| **Duplicate Ingestion** | De-duplicated via idempotency key. | Returns existing observation record without double-counting. |
| **Future Timestamp** | `observed_at > now + 60s` $\rightarrow$ `HTTP 422`. | Rejected; prevents forward-dated tampering. |
| **Unit Mismatch** | Validated against `kri.unit_of_measure`. | Ingestion requires unit matching KRI registry definition. |
| **NaN / Infinity** | `HTTP 422 Unprocessable Content`. | Non-finite floating point numbers strictly rejected. |

---

## 14. Risk / KRI Relationship

- **Relationship Model**: Many-to-Many via association table `kri_risk_links`.
- **Fields**: `organization_id`, `kri_id`, `risk_id`, `correlation_weight`, `notes`, `created_by_id`, `created_at`.
- **Correlation Weight Semantics**:
  - Float bounded within $[-1.0, +1.0]$.
  - $+1.0$: Direct positive correlation (KRI increase indicates increased risk exposure).
  - $-1.0$: Inverse correlation (KRI decrease indicates increased risk exposure).
  - **Hard Rule**: Correlation weight is **governed metadata** utilized for risk prioritization, dashboard sorting, and executive impact analysis. It **DOES NOT** arbitrarily alter the Phase 5 $I \times L$ risk scoring engine.

---

## 15. QuantRisk / KRI Relationship

- Quantitative metrics calculated by `QuantumGrcService` (Phase 12) feed into the KRI ecosystem without recalculation:
  - Financial KRIs (e.g. "Simulated Annualized Cyber Loss Expectancy") ingest `annualized_loss_expectancy` from completed `QuantitativeSimulationRun` records.
  - Thresholds on such KRIs are calibrated against `FinancialRiskAppetite.ale_limit`.
  - The KRI engine acts as an operational monitoring watchtower over FAIR simulation outputs.

---

## 16. Breach → Finding / Remediation Contract

Escalation of a KRI breach must follow deterministic architectural routing:

```
                                  ┌──────────────────────────────┐
                                  │       KRI Breach Event       │
                                  │      (Table: breaches)       │
                                  └──────────────┬───────────────┘
                                                 │
                                Is Breach caused by a Control Gap?
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                       YES                                                NO
                        ▼                                                 ▼
        ┌───────────────────────────────┐                 ┌───────────────────────────────┐
        │  Escalate to Phase 4 Finding  │                 │ Track via Phase 5 Risk Plan   │
        │      (Table: findings)        │                 │   (risks.treatment_plan)      │
        └──────────────┬────────────────┘                 └───────────────────────────────┘
                       │
             spawns via Phase 11
                       ▼
        ┌───────────────────────────────┐
        │ Phase 11 RemediationPlan      │
        │   (remediation_plans)         │
        └───────────────────────────────┘
```

### Deterministic Rules:
1. **Control-Related Breach**: If the analyst establishes that the breach is driven by a control failure, they escalate via `POST /api/v1/kri/breaches/{id}/escalate-finding`. This creates an authoritative Phase 4 `Finding` (requiring `organization_control_id`), records `KriBreachRecord.escalated_finding_id`, and transitions breach status to `ESCALATED`.
2. **Non-Control Operational Exposure**: If the breach represents macro-operational drift without a control gap, the breach links to the associated `Risk` treatment plan (`Risk.treatment_plan`). It **DOES NOT** pollute the control findings register.
3. **Prohibited Pattern**: Never create `KriFinding`, `KriAction`, or duplicate remediation tables.

---

## 17. Breach State Machine

```
   ┌─────────────┐
   │  DETECTED   │◀────────────────────────────────────────┐
   └──────┬──────┘                                         │
          │ acknowledge()                                  │
          ▼                                                │
   ┌─────────────┐                                         │
   │ACKNOWLEDGED │                                         │
   └──────┬──────┘                                         │ re-breached
          │                                                │
          ├──────────────────────────┐                     │
          │ escalate_finding()       │ observation normal  │
          ▼                          ▼                     │
   ┌─────────────┐            ┌─────────────┐              │
   │  ESCALATED  │            │  RECOVERED  │──────────────┘
   └──────┬──────┘            └──────┬──────┘
          │ observation normal       │ close() [Four-Eyes]
          ▼                          ▼
   ┌─────────────┐            ┌─────────────┐
   │  RECOVERED  │───────────▶│   CLOSED    │
   └─────────────┘            └─────────────┘
```

### State Transition Authority Matrix:

| Current State | Target State | Trigger / Action | Authorized Roles | Four-Eyes Check |
| :--- | :--- | :--- | :--- | :--- |
| `[NONE]` | `DETECTED` | Observation exceeds critical threshold | Automated Engine | None (System) |
| `DETECTED` | `ACKNOWLEDGED` | Analyst acknowledges breach receipt | `ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST` | None |
| `ACKNOWLEDGED` | `ESCALATED` | Formal escalation to Phase 4 Finding | `ADMIN`, `MANAGER`, `GRC_ANALYST` | None |
| `DETECTED` / `ACKNOWLEDGED` / `ESCALATED` | `RECOVERED` | Observation returns within normal/warning limits | Automated Engine | None (System) |
| `RECOVERED` | `CLOSED` | Formal sign-off and closure | `ADMIN`, `MANAGER` | `closer_id != acknowledged_by_id` AND `closer_id != kri.owner_id` |

---

## 18. Risk Appetite Versioning

- `RiskAppetiteStatement` records immutable, approved versions.
- **Workflow**: `DRAFT` $\rightarrow$ `APPROVED` $\rightarrow$ `SUPERSEDED`.
- **Four-Eyes Approval**: Approving a draft statement requires `requested_by_id != approved_by_id`.
- **Superseding**: When a new statement version is approved, the existing active statement for that organization is atomically updated to `SUPERSEDED` with `superseded_at = now()`.
- **Audit Preservation**: Historical risk appetite statements are never deleted or modified in-place.

---

## 19. Threshold Versioning

- Every `KriThreshold` maintains an `is_active` flag, `version`, and `effective_from` timestamp.
- When an analyst updates a KRI's threshold:
  1. The existing active threshold is updated to `is_active = False` with `effective_to = now()`.
  2. A new threshold record is created with `version = previous.version + 1`, `is_active = True`, and `effective_from = now()`.
  3. Historical observations retain their original evaluation context. Historical breaches record the threshold value in effect at the moment the breach occurred.

---

## 20. Observation Immutability & Auditability

- Observations are strictly **append-only**.
- If telemetry was ingested in error, correction is accomplished by:
  1. Ingesting a new observation with `source_type="MANUAL_ENTRY"` and explicit explanatory notes.
  2. The system evaluates the latest observation based on `observed_at DESC, created_at DESC`.
  3. Historical observation rows remain permanently intact in `kri_observations` for audit trail non-repudiation.

---

## 21. Four-Eyes Governance Rules

ControlSphere enforces Segregation of Duties (SoD) server-side via authenticated session context:

1. **Appetite Statement Approval**:
   ```python
   if statement.requested_by_id == current_user.id:
       raise HTTPException(
           status_code=400,
           detail="Four-Eyes Violation: Approver must be distinct from requester."
       )
   ```
2. **Breach Closure**:
   ```python
   if breach.acknowledged_by_id == current_user.id:
       raise HTTPException(
           status_code=400,
           detail="Four-Eyes Violation: Breach closer must be distinct from acknowledging analyst."
       )
   if kri.owner_id == current_user.id:
       raise HTTPException(
           status_code=400,
           detail="Four-Eyes Violation: KRI owner cannot self-close breaches for their own metric."
       )
   ```

---

## 22. Role-Based Access Control (RBAC)

ControlSphere strictly enforces the exact 6 platform roles with zero role inflation:

| Permission | Permission String | `ADMIN` | `MANAGER` | `GRC_ANALYST` | `SECURITY_ANALYST` | `AUDITOR` | `VIEWER` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `APPETITE_READ` | `appetite:read` | Yes | Yes | Yes | Yes | Yes | Yes |
| `APPETITE_MANAGE` | `appetite:manage` | Yes | Yes | Yes | No | No | No |
| `APPETITE_APPROVE` | `appetite:approve` | Yes | Yes | No | No | No | No |
| `KRI_READ` | `kri:read` | Yes | Yes | Yes | Yes | Yes | Yes |
| `KRI_MANAGE` | `kri:manage` | Yes | Yes | Yes | Yes | No | No |
| `KRI_OBSERVE` | `kri:observe` | Yes | Yes | Yes | Yes | No | No |
| `KRI_BREACH_ACTION`| `kri:breach_action`| Yes | Yes | Yes | Yes | No | No |
| `KRI_BREACH_CLOSE` | `kri:breach_close` | Yes | Yes | No | No | No | No |

---

## 23. Tenant Isolation & Anti-Enumeration

- **Tenant Isolation**: Every Batch 2 table includes `organization_id NOT NULL` with `ForeignKey("organizations.id", ondelete="CASCADE")`.
- **JWT Context Injection**: `organization_id` is extracted strictly from the verified JWT access token. Client payloads attempting to inject or override `organization_id` are ignored.
- **Anti-IDOR / Anti-Enumeration Semantics**: Any attempt to access, link, or mutate a resource belonging to another organization yields `HTTP 404 Not Found` (never `403 Forbidden` or `500 Server Error`).

---

## 24. Concurrency & Idempotency Controls

1. **Observation Idempotency**:
   - Ingestion payloads support an optional `idempotency_key` (String(64)).
   - If provided, duplicate submissions within 24 hours return the existing observation record (`HTTP 200`) without creating duplicate rows or re-evaluating thresholds.
2. **Breach Evaluation Locking**:
   - During observation ingestion, active breach lookup executes within a PostgreSQL row-level lock (`SELECT ... FOR UPDATE`) on the KRI record, preventing race conditions during concurrent telemetry spikes.
3. **Optimistic Locking**:
   - `RiskAppetiteStatement` and `KriThreshold` utilize version numbers to detect and reject concurrent conflicting updates (`HTTP 409 Conflict`).

---

## 25. Notification Integration

ControlSphere avoids creating duplicate notification silos:
- When a `KriBreachRecord` is detected or escalated, the event is emitted via the authoritative audit logging service: `AuditService.log(...)`.
- The existing alert infrastructure (used in Phase 7 and Phase 23) consumes these audit events to generate in-app notification badges for assigned KRI owners and managers without a separate `KriNotification` table.

---

## 26. Executive GRC Integration (Phase 20)

- Batch 2 telemetry feeds directly into Phase 20 Executive Snapshots (`ExecutiveSnapshot`):
  - `active_kri_breaches_count`: Total active breaches (`DETECTED`, `ACKNOWLEDGED`, `ESCALATED`).
  - `appetite_alignment_ratio`: Percentage of registered risks currently `WITHIN_APPETITE`.
  - `stale_kri_count`: Count of KRIs exceeding sampling frequency tolerance.
- Telemetry is incorporated into `ExecutiveSnapshot.source_manifest` and factored into `ExecutiveSnapshot.overall_posture_score` without requiring database schema alterations in `executive_snapshots`.

---

## 27. Continuous Assurance Integration (Phase 23)

- KRI breach metrics provide real-time operational inputs to Phase 23 Continuous Assurance (`ContinuousComplianceProfile`):
  - KRI breach events contribute to `ComplianceDriftRecord` drift assessments under vector `CCM_HEALTH_DEGRADATION`.
  - **Loop Prevention**: Continuous Assurance monitors KRI status unidirectionally; KRI evaluation never cyclically invokes continuous assurance recalculations.

---

## 28. Concrete Domain Model & Schema Specifications

The schema additions for Batch 2 are encapsulated in `backend/alembic/versions/0023_kri_and_risk_appetite_governance.py`:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         risk_appetite_statements                                      │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ statement_code             │ String(64)                 │ False     │ IX (e.g. "APP-2026-001")         │
│ title                      │ String(255)                │ False     │                                  │
│ executive_summary          │ Text                       │ False     │ Board policy overview            │
│ version                    │ Integer                    │ False     │ default: 1                       │
│ status                     │ Enum(AppetiteStatementStat)│ False     │ DRAFT, APPROVED, SUPERSEDED, IX  │
│ category_appetites         │ JSON                       │ False     │ Dict mapping category to band    │
│ financial_risk_appetite_id │ Integer                    │ True      │ FK(financial_risk_appetites.id)  │
│ requested_by_id            │ Integer                    │ False     │ FK(users.id, RESTRICT), IX       │
│ approved_by_id             │ Integer                    │ True      │ FK(users.id, SET NULL), IX       │
│ approved_at                │ DateTime(timezone=True)    │ True      │                                  │
│ effective_from             │ Date                       │ False     │ IX                               │
│ review_cadence_months      │ Integer                    │ False     │ default: 12                      │
│ created_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
│ updated_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           key_risk_indicators                                          │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ kri_code                   │ String(64)                 │ False     │ IX (e.g. "KRI-SEC-001")          │
│ title                      │ String(255)                │ False     │ IX                               │
│ description                │ Text                       │ False     │                                  │
│ risk_category              │ Enum(RiskCategoryEnum)     │ False     │ IX                               │
│ unit_of_measure            │ String(32)                 │ False     │ e.g. "PERCENTAGE", "COUNT", "USD"│
│ frequency                  │ Enum(KriFrequencyEnum)     │ False     │ HOURLY, DAILY, WEEKLY, etc., IX  │
│ direction                  │ Enum(KriDirectionEnum)     │ False     │ LOWER_IS_BETTER, etc., IX        │
│ status                     │ Enum(KriStatusEnum)        │ False     │ ACTIVE, INACTIVE, STALE_DATA, IX │
│ owner_id                   │ Integer                    │ True      │ FK(users.id, SET NULL), IX       │
│ latest_value               │ Float                      │ True      │ Denormalized latest cache        │
│ latest_observed_at         │ DateTime(timezone=True)    │ True      │ Denormalized latest timestamp, IX│
│ latest_evaluation_status   │ Enum(KriEvaluationStatus)  │ False     │ NORMAL, WARNING, CRITICAL, IX    │
│ created_by_id              │ Integer                    │ False     │ FK(users.id, RESTRICT)           │
│ created_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
│ updated_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              kri_thresholds                                            │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ kri_id                     │ Integer                    │ False     │ FK(key_risk_indicators.id, CASC) │
│ version                    │ Integer                    │ False     │ default: 1                       │
│ is_active                  │ Boolean                    │ False     │ default: True, IX                │
│ warning_threshold          │ Float                      │ False     │ Amber limit                      │
│ critical_threshold         │ Float                      │ False     │ Red limit                        │
│ range_min_warning          │ Float                      │ True      │ Used when direction=WITHIN_RANGE │
│ range_max_warning          │ Float                      │ True      │ Used when direction=WITHIN_RANGE │
│ range_min_critical         │ Float                      │ True      │ Used when direction=WITHIN_RANGE │
│ range_max_critical         │ Float                      │ True      │ Used when direction=WITHIN_RANGE │
│ effective_from             │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
│ effective_to               │ DateTime(timezone=True)    │ True      │                                  │
│ created_by_id              │ Integer                    │ False     │ FK(users.id, RESTRICT)           │
│ created_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                             kri_observations                                           │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ kri_id                     │ Integer                    │ False     │ FK(key_risk_indicators.id, CASC) │
│ observed_value             │ Float                      │ False     │ Numerical measurement            │
│ unit                       │ String(32)                 │ False     │ Measurement unit                 │
│ observed_at                │ DateTime(timezone=True)    │ False     │ IX (historical observation time) │
│ source_type                │ Enum(KriSourceTypeEnum)    │ False     │ IX                               │
│ source_identifier          │ String(128)                │ True      │ External or internal entity ID   │
│ notes                      │ Text                       │ True      │ Context notes                    │
│ idempotency_key            │ String(64)                 │ True      │ IX (deduplication)               │
│ data_hash_sha256           │ String(64)                 │ False     │ Cryptographic tamper detection   │
│ created_by_id              │ Integer                    │ True      │ FK(users.id, SET NULL)           │
│ created_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            kri_breach_records                                          │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ kri_id                     │ Integer                    │ False     │ FK(key_risk_indicators.id, CASC) │
│ breach_code                │ String(64)                 │ False     │ IX (e.g. "BRC-2026-001")         │
│ threshold_id               │ Integer                    │ False     │ FK(kri_thresholds.id, RESTRICT)  │
│ trigger_observation_id     │ Integer                    │ False     │ FK(kri_observations.id, RESTRICT)│
│ latest_observation_id      │ Integer                    │ False     │ FK(kri_observations.id, RESTRICT)│
│ status                     │ Enum(BreachStatusEnum)     │ False     │ DETECTED, ACK, ESC, REC, CLOSED  │
│ breach_value               │ Float                      │ False     │ Initial triggering value         │
│ peak_value                 │ Float                      │ False     │ Maximum severity value           │
│ detected_at                │ DateTime(timezone=True)    │ False     │ IX                               │
│ acknowledged_at            │ DateTime(timezone=True)    │ True      │                                  │
│ acknowledged_by_id         │ Integer                    │ True      │ FK(users.id, SET NULL)           │
│ escalated_at               │ DateTime(timezone=True)    │ True      │                                  │
│ escalated_finding_id       │ Integer                    │ True      │ FK(findings.id, SET NULL), IX    │
│ recovered_at               │ DateTime(timezone=True)    │ True      │                                  │
│ closed_at                  │ DateTime(timezone=True)    │ True      │                                  │
│ closed_by_id               │ Integer                    │ True      │ FK(users.id, SET NULL)           │
│ closure_notes              │ Text                       │ True      │ Four-Eyes justification          │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              kri_risk_links                                            │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ kri_id                     │ Integer                    │ False     │ FK(key_risk_indicators.id, CASC) │
│ risk_id                    │ Integer                    │ False     │ FK(risks.id, CASCADE), IX        │
│ correlation_weight         │ Float                      │ False     │ default: 1.0 (range: -1.0 to 1.0)│
│ notes                      │ Text                       │ True      │ Rationalization notes            │
│ created_by_id              │ Integer                    │ True      │ FK(users.id, SET NULL)           │
│ created_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘
```

---

## 29. API Contract

All endpoints are registered under `/api/v1/kri` and enforce JWT authentication, strict tenant scoping, and exact RBAC permissions:

| Method | Endpoint Path | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/kri/appetite-statements` | `APPETITE_READ` | List tenant risk appetite statements. |
| `POST`| `/api/v1/kri/appetite-statements` | `APPETITE_MANAGE` | Create draft appetite statement. |
| `POST`| `/api/v1/kri/appetite-statements/{id}/approve` | `APPETITE_APPROVE` | Four-Eyes approval of statement. |
| `GET` | `/api/v1/kri/indicators` | `KRI_READ` | List KRIs with latest evaluation status. |
| `POST`| `/api/v1/kri/indicators` | `KRI_MANAGE` | Register new KRI with initial threshold. |
| `GET` | `/api/v1/kri/indicators/{id}` | `KRI_READ` | Get KRI details, thresholds, and risk links. |
| `PUT` | `/api/v1/kri/indicators/{id}` | `KRI_MANAGE` | Update KRI registry metadata. |
| `POST`| `/api/v1/kri/indicators/{id}/thresholds` | `KRI_MANAGE` | Version and activate new threshold. |
| `POST`| `/api/v1/kri/indicators/{id}/observations` | `KRI_OBSERVE` | Ingest time-series observation & evaluate. |
| `GET` | `/api/v1/kri/indicators/{id}/observations` | `KRI_READ` | Query historical observations. |
| `POST`| `/api/v1/kri/indicators/{id}/link-risk` | `KRI_MANAGE` | Link KRI to Phase 5 Risk record. |
| `GET` | `/api/v1/kri/breaches` | `KRI_READ` | List breaches with status filtering. |
| `POST`| `/api/v1/kri/breaches/{id}/acknowledge` | `KRI_BREACH_ACTION` | Acknowledge active breach. |
| `POST`| `/api/v1/kri/breaches/{id}/escalate-finding` | `KRI_BREACH_ACTION` | Escalate breach to Phase 4 Finding. |
| `POST`| `/api/v1/kri/breaches/{id}/close` | `KRI_BREACH_CLOSE` | Four-Eyes closure with sign-off notes. |
| `GET` | `/api/v1/kri/telemetry/overview` | `KRI_READ` | Executive high-level exposure overview. |

---

## 30. Frontend Contract

- **UI Integration Architecture**:
  - Integrated into the existing Risk Management workspace (`frontend/src/pages/RiskPage.tsx`) as tabbed interfaces:
    - Tab 1: **Risk Register** (Existing Phase 5 view)
    - Tab 2: **Risk Appetite Statements** (Governance policy, category matrix, board approval status)
    - Tab 3: **KRI Monitoring Lab** (Active KRIs, time-series Sparklines, status badges [Green/Amber/Red/Stale])
    - Tab 4: **Breach Command Center** (Active breach queue, acknowledgment modal, Four-Eyes closure dialog)
- **Zero Client-Side Calculation**:
  - All breach states, threshold comparisons, and appetite statuses are computed server-side and presented via read-only DTO fields.
- **Frontend Service Client**: Encapsulated in `frontend/src/lib/kriService.ts`.

---

## 31. Adversarial Security Matrix

The following 30 concrete attack vectors must be explicitly verified in the Batch 2 test suite:

| Vector ID | Attack Name | Attacker Action / Payload | Enforced Platform Defense |
| :--- | :--- | :--- | :--- |
| `SEC-B2-01` | **Cross-Tenant Appetite Read** | Tenant B user requests `/api/v1/kri/appetite-statements/{tenantA_id}` | `HTTP 404 Not Found` (Anti-enumeration). |
| `SEC-B2-02` | **Cross-Tenant Observation Ingestion** | Tenant B analyst posts observation to Tenant A's KRI | `HTTP 404 Not Found`. |
| `SEC-B2-03` | **JWT Org ID Tampering** | Attacker injects `organization_id=999` in request body | Server uses verified token claims; body value ignored. |
| `SEC-B2-04` | **Appetite Self-Approval (SoD)** | Requester attempts to approve their own draft statement | `HTTP 400 Bad Request` ("Four-Eyes Violation"). |
| `SEC-B2-05` | **Breach Self-Closure (SoD)** | Analyst who acknowledged breach attempts to close it | `HTTP 400 Bad Request` ("Four-Eyes Violation"). |
| `SEC-B2-06` | **KRI Owner Self-Closure (SoD)** | KRI owner attempts to close breach on their own metric | `HTTP 400 Bad Request` ("Four-Eyes Violation"). |
| `SEC-B2-07` | **Forward-Dated Observation** | Client posts observation with `observed_at = now + 7 days` | `HTTP 422 Unprocessable Content`. |
| `SEC-B2-08` | **Observation In-Place Mutation** | Client sends `PUT` or `PATCH` to `/kri/observations/{id}` | `HTTP 405 Method Not Allowed` (Append-only). |
| `SEC-B2-09` | **Observation Deletion** | Client sends `DELETE` to `/kri/observations/{id}` | `HTTP 405 Method Not Allowed` (Append-only). |
| `SEC-B2-10` | **Replayed Ingestion Flood** | Client replays identical payload with same `idempotency_key` | Returns existing record without duplicate evaluation. |
| `SEC-B2-11` | **Illegal State Transition (Direct Close)** | Client calls close on a breach currently in `DETECTED` | `HTTP 400 Bad Request` (Invalid state transition). |
| `SEC-B2-12` | **Cross-Tenant Risk Linkage** | Client attempts to link Tenant A KRI to Tenant B Risk | `HTTP 404 Not Found` on referenced Risk. |
| `SEC-B2-13` | **Duplicate Finding Escalation** | Client calls escalate-finding twice on the same breach | `HTTP 409 Conflict` (Already escalated). |
| `SEC-B2-14` | **Escalation Without Control** | Client escalates breach to Finding without valid control ID | `HTTP 422 Unprocessable Content`. |
| `SEC-B2-15` | **Negative Threshold Inversion** | Client sets $T_{\text{warn}} > T_{\text{crit}}$ for `LOWER_IS_BETTER` | `HTTP 422 Unprocessable Content` (Validation error). |
| `SEC-B2-16` | **Viewer Role Breach Acknowledgement**| User with `VIEWER` role calls breach acknowledge | `HTTP 403 Forbidden` (Insufficient permissions). |
| `SEC-B2-17` | **Auditor Role Threshold Tampering** | User with `AUDITOR` role attempts to alter threshold | `HTTP 403 Forbidden` (Read-only for auditors). |
| `SEC-B2-18` | **NaN Observation Value** | Client posts `{"observed_value": "NaN"}` | `HTTP 422 Unprocessable Content`. |
| `SEC-B2-19` | **Infinity Observation Value** | Client posts `{"observed_value": "Infinity"}` | `HTTP 422 Unprocessable Content`. |
| `SEC-B2-20` | **Unit Mismatch Injection** | Client posts value in `GB` to a KRI defined in `PERCENTAGE` | `HTTP 422 Unprocessable Content`. |
| `SEC-B2-21` | **Correlation Weight Out-of-Bounds** | Client links Risk with correlation weight = 2.5 | `HTTP 422 Unprocessable Content` (Bounded $[-1.0, 1.0]$). |
| `SEC-B2-22` | **Concurrent Telemetry Race Condition**| Two parallel threads ingest critical values simultaneously | Row lock on KRI guarantees exactly one active breach. |
| `SEC-B2-23` | **Stale Data Masking** | System evaluated after observation interval breached | KRI status transitions automatically to `STALE_DATA`. |
| `SEC-B2-24` | **Provenance Hash Forgery** | Attacker directly injects custom SHA-256 in payload | Server derives hash internally; client input ignored. |
| `SEC-B2-25` | **Appetite Re-Approval** | Client attempts to approve an already `APPROVED` statement| `HTTP 400 Bad Request`. |
| `SEC-B2-26` | **Cross-Tenant Breach Query** | Tenant A attempts to fetch `/kri/breaches/{tenantB_breach_id}`| `HTTP 404 Not Found`. |
| `SEC-B2-27` | **Orphaned Breach Closure** | Attempt to close breach without required closure notes | `HTTP 422 Unprocessable Content`. |
| `SEC-B2-28` | **Inactive KRI Observation** | Client posts observation to KRI with `status=INACTIVE` | `HTTP 400 Bad Request` ("KRI is inactive"). |
| `SEC-B2-29` | **Cross-Tenant Financial Appetite Link**| Tenant A statement references Tenant B `FinancialRiskAppetite` | `HTTP 404 Not Found`. |
| `SEC-B2-30` | **Historical Invalidation Tampering** | Client attempts to falsify historical breach value | Immutable DB records; changes rejected. |

---

## 32. Migration Design

- **Migration File**: `backend/alembic/versions/0023_kri_and_risk_appetite_governance.py`
- **Revision ID**: `0023`
- **Revises**: `0022`
- **Atomic Operations**:
  1. Create `risk_appetite_statements` with indexes and foreign keys.
  2. Create `key_risk_indicators` with composite indexes on `(organization_id, kri_code)`.
  3. Create `kri_thresholds` with indexes on `(kri_id, is_active)`.
  4. Create `kri_observations` with composite index on `(kri_id, observed_at DESC)`.
  5. Create `kri_breach_records` with index on `(kri_id, status)`.
  6. Create `kri_risk_links` with unique constraint on `(kri_id, risk_id)`.
- **Clean Downgrade**: Drops tables in exact reverse dependency order (`kri_risk_links`, `kri_breach_records`, `kri_observations`, `kri_thresholds`, `key_risk_indicators`, `risk_appetite_statements`).

---

## 33. Concrete Implementation Sequence

The implementation of Batch 2 will proceed in an 8-stage vertical execution sequence:

```
Stage 1: Alembic Migration & Database Models
         ├── Create backend/alembic/versions/0023_kri_and_risk_appetite_governance.py
         ├── Author backend/app/models/kri.py (All 6 domain entities & enums)
         └── Execute alembic upgrade head and verify clean schema

Stage 2: RBAC & Permission Additions
         ├── Extend backend/app/core/permissions.py with 8 Batch 2 permissions
         └── Map permissions to exact 6 platform roles

Stage 3: Pydantic Schemas & DTOs
         └── Author backend/app/schemas/kri.py (Request, Response, Filter schemas)

Stage 4: Domain Calculation & Orchestration Services
         ├── Author backend/app/services/kri_evaluation_service.py (Evaluation engine)
         ├── Author backend/app/services/kri_service.py (CRUD, lifecycle, SoD)
         └── Integrate telemetry into Executive GRC & Continuous Assurance helpers

Stage 5: FastAPI REST API Endpoints
         ├── Author backend/app/api/v1/endpoints/kri.py
         └── Register router in backend/app/api/v1/api.py

Stage 6: Comprehensive Security & Functional Tests
         ├── Author backend/tests/test_kri_domain.py
         ├── Author backend/tests/test_kri_api.py (Implementing all 30 SEC-B2 vectors)
         └── Execute pytest and verify 100% pass rate

Stage 7: Frontend Integration
         ├── Author frontend/src/lib/kriService.ts
         ├── Author frontend/src/types/kri.ts
         ├── Integrate KRI & Appetite tabs into frontend/src/pages/RiskPage.tsx
         └── Verify frontend production build (npm run build)

Stage 8: Full Platform Regression & Git Checkpoint
         ├── Run full 999+ backend regression test suite
         ├── Run git status, git diff --check
         └── Perform Phase 26 Git checkpoint
```

---

## 34. Batch Boundary & Productivity Analysis

### Evaluation of Grouping vs. Splitting:
- **High Entity Coupling**: A KRI cannot exist without thresholds; observations cannot exist without KRIs; breaches cannot evaluate without observations and thresholds; and risk appetite statements provide the governing tolerance limits for KRIs.
- **Unified User Surface**: In the UI, analysts manage risks, appetites, KRIs, and breaches within a unified workspace. Splitting into multiple phases would create broken intermediate workflows.
- **Zero Migration Churn**: Delivering Batch 2 under a single migration `0023` prevents repeated alterations to shared tables.
- **Productivity Multiplier**: Delivers the entire proactive risk management layer in a single high-velocity implementation pass.

---

## 35. Future Batch Compatibility

Batch 2 strictly aligns with subsequent platform batches:
- **Batch 3 (`DATA-GOVERNANCE-GRC`)**: Batch 2 does not create data asset catalogs or classification engines; data risk KRIs will monitor data governance assets in Batch 3.
- **Batch 4 (`OBLIGATION-TRUST-GRC`)**: Batch 2 does not create customer compliance trust portals or customer-facing attestation packages.
- **Batch 5 (`ADVANCED-ASSURANCE-GRC`)**: Automated test scripts and continuous verification pipelines in Batch 5 will feed directly into `KriObservation` via `source_type="CCM_HEALTH_CHECK"`.

---

## 36. Risks and Architectural Mitigations

| Risk Identified | Impact | Architectural Mitigation Strategy |
| :--- | :---: | :--- |
| **Telemetry Volume Bloat** | High | Append-only `kri_observations` uses indexed timestamps; queries limit historical windows; table partitioning supported by design. |
| **Alert Fatigue from Flapping Metrics**| Medium | Built-in breach hysteresis: active breach persists until formal recovery; subsequent critical observations update the active breach rather than spawning new records. |
| **Silent Stale Telemetry** | High | Automated `STALE_DATA` detection when elapsed time exceeds $1.5 \times \text{frequency}$; displayed prominently in executive posture dashboards. |
| **Four-Eyes Bypass via Self-Approval** | Critical| Server-side hard validation comparing `actor_id` against `requested_by_id`, `acknowledged_by_id`, and `kri.owner_id`. |
| **Cross-Tenant IDOR Telemetry Injection**| Critical| Strict JWT-derived tenant scoping; missing or foreign IDs return `HTTP 404 Not Found`. |

---

## 37. Final Architecture Gate

### Gate Verification Checklist:
- [x] **Repository Ground Truth Confirmed**: Git HEAD `a3e9b4a`, Alembic head `0022`, 999/999 passing tests, clean working tree.
- [x] **Five-Tier Authority Hierarchy Formalized**: Strategic Statement $\rightarrow$ Financial Limit $\rightarrow$ Risk Target $\rightarrow$ KRI Threshold $\rightarrow$ Governed Breach.
- [x] **Zero Duplicate Engines**: Reuses Phase 5 `Risk`, Phase 12 `QuantitativeRiskScenario` & `FinancialRiskAppetite`, Phase 4 `Finding`, and Phase 11 `RemediationPlan`.
- [x] **Deterministic Boundary Mathematics Defined**: `LOWER_IS_BETTER`, `HIGHER_IS_BETTER`, and `WITHIN_RANGE` formulas specified with exact boundary equality.
- [x] **Append-Only Observation Integrity Formulated**: Cryptographic SHA-256 digest over canonical ingestion payload; future timestamps rejected.
- [x] **Governed Breach Lifecycle & Hysteresis Established**: `DETECTED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `ESCALATED` $\rightarrow$ `RECOVERED` $\rightarrow$ `CLOSED` with anti-flapping hysteresis.
- [x] **Four-Eyes Segregation of Duties Enforced**: Non-self-approval on statements and closures.
- [x] **Exact 6 Platform Roles Preserved**: Zero role inflation; 8 granular permissions mapped.
- [x] **30-Vector Adversarial Security Matrix Specified**: `SEC-B2-01` through `SEC-B2-30`.
- [x] **Single Atomic Migration Verified**: `0023_kri_and_risk_appetite_governance.py`.
- [x] **Single Integrated Batch Boundary Validated**: `BATCH-2-KRI-APPETITE`.

---

# **GO — BATCH 2 READY FOR IMPLEMENTATION**
