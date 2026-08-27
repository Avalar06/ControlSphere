# CONTROLSPHERE — PHASE 12 ARCHITECTURAL SPECIFICATION & MATHEMATICAL FREEZE
## QUANTUM-GRC: ENTERPRISE CYBER RISK QUANTIFICATION, LOSS MODELING & RETURN ON SECURITY INVESTMENT (ROSI)

---

### Authoritative Document Metadata
- **Document Version**: `1.0.0-STAGE0-FROZEN`
- **Specification Status**: `APPROVED & MATHEMATICALLY FROZEN`
- **Release Baseline**: Commit `ff869f6` (Phase 11 Release Frozen)
- **Database Target**: Alembic Migration `0012_cyber_risk_quantification.py` (`0011` $\rightarrow$ `0012`)
- **System Codename**: `QUANTUM-GRC`

---

## 1. EXECUTIVE CONTEXT & SYSTEM LINEAGE

ControlSphere currently provides end-to-end GRC management across proactive controls, continuous telemetry, vendor risk, reactive security breaches, and closed-loop corrective actions:

```
[Phase 1: Foundation (Multi-Tenancy, Users, Roles, JWT, AuditLog)]
        ↓
[Phase 2: Governance (Frameworks, Controls Library, Policies)]
        ↓
[Phase 3: Assurance (Evidence Repository, Cryptographic Hashes, Verification)]
        ↓
[Phase 4: Assessment (Control Assessments, Deficiencies, Findings)]
        ↓
[Phase 5: Qualitative Risk (5x5 Matrix, Risk Appetite, Exceptions)]
        ↓
[Phase 6: Independent Audit (Audit Engagements, Scope, PBC Procedures)]
        ↓
[Phase 7: Continuous Monitoring (CCM Health Scores 0–100, Drift Alerts, Snapshots)]
        ↓
[Phase 8: Rationalization (Harmonization, Common Controls, Posture Snapshots)]
        ↓
[Phase 9: TPRM (Vendors, Vendor Tiers, Residual Risk, Four-Eyes Approval)]
        ↓
[Phase 10: Reactive Security (Incidents, Breach Timeline, Regulatory Disclosures)]
        ↓
[Phase 11: Governed Remediation (ROC-V, CAPA Tasks, Re-Tests, SLA/REI/TTR)]
        ↓
══════════════════════════════════════════════════════════════════════════════
[Phase 12: QUANTUM-GRC (Quantitative Financial Loss Modeling, VaR & ROSI)]
```

### Coexistence Architecture
Phase 12 is a **quantitative financial-risk layer** that operates in tandem with Phase 5 qualitative risk management.

ControlSphere contains an enterprise qualitative risk register ($1-25$ Likelihood $\times$ Impact matrices, Inherent/Residual risk scores, Risk Appetite bands, and Risk Exceptions).

Phase 12 introduces **Loss Event Frequency (LEF)**, **Single Loss Expectancy (SLE)**, **Annualized Loss Expectancy (ALE)**, and **Monte Carlo Value at Risk ($\text{VaR}$)** calculations without mutating or corrupting Phase 5 qualitative data structures.

---

## 2. STANDARD TAXONOMY & NOMENCLATURE

ControlSphere utilizes a **FAIR-inspired quantitative cyber-risk model** incorporating standardized concepts from the Factor Analysis of Information Risk (FAIR) taxonomy and ISO/IEC 27005 quantitative guidelines.

> [!IMPORTANT]
> ControlSphere does not claim Open FAIR™ certification or compliance. The platform provides a deterministic, server-authoritative implementation of loss event frequency decomposition, Beta-PERT loss distributions, empirical percentile simulations, and capital allocation mathematics tailored for enterprise GRC automation.

---

## 3. NUMERICAL INVARIANTS & ROUNDING POLICY

All quantitative financial calculations in Phase 12 adhere to strict mathematical domain constraints:

| Value Domain | Data Type | Permissible Range | Precision & Rounding Policy |
|:---|:---|:---|:---|
| **Financial Losses & Currencies** | USD (`Float` / `Numeric(18,2)`) | $[0.00, \infty)$ | Intermediate calculations retain double precision (64-bit IEEE 754 float); final persisted outputs rounded to **2 decimal places** (`round(val, 2)`). |
| **Probabilities & Factors** | Normalized Float | $[0.0000, 1.0000]$ | Retain double precision; clamped strictly to $[0.0, 1.0]$. |
| **Percentages** | Normalized Float | $[0.00\%, 100.00\%]$ | Persisted outputs rounded to **2 decimal places**. |
| **Event Frequencies** | Frequency (`Float`) | $[0.00, \infty)$ events/year | Retain double precision; non-negative. |
| **Percentiles ($P_{10} \dots P_{99}$)** | Currency USD | $[0.00, \infty)$ | Rounded to **2 decimal places**. |
| **Simulation Trials ($N$)** | Integer | $[100, 50,000]$ | Default: $10,000$ iterations. Server bounded. |

### Strict Numerical Guarantees
- **No `NaN` or `Infinity`**: Any calculation encountering division by zero, invalid roots, or non-finite float results raises a `QuantCalculationError` and returns `HTTP 422 Unprocessable Entity`.
- **Non-Negativity Invariant**: Financial losses, loss event frequencies, and risk exposures can never evaluate to negative values ($\ge 0.00$).
- **No Premature Intermediate Rounding**: All mathematical equations preserve complete floating-point precision throughout calculation pipelines until final response serialization.

---

## 4. DETERMINISTIC MATHEMATICAL FORMULATION

### A. Beta-PERT Distribution Modeling
Three-point estimations ($\text{Min} = a$, $\text{Mode} = m$, $\text{Max} = b$) for Threat Event Frequency ($\text{TEF}$), Primary Loss ($\text{PL}$), and Secondary Loss ($\text{SL}$) are evaluated using the standard Beta-PERT formulation:

$$\mu_{\text{PERT}}(a, m, b) = \frac{a + 4m + b}{6}$$

$$\sigma^2_{\text{PERT}}(a, m, b) = \frac{(b - a)^2}{36}$$

$$\sigma_{\text{PERT}}(a, m, b) = \frac{b - a}{6}$$

#### Invariants & Range Validation:
$$0 \le a \le m \le b$$
- If $a = m = b$, the distribution collapses to a deterministic constant ($\mu = a$, $\sigma = 0$).
- If $a > m$ or $m > b$, the payload is rejected with `HTTP 422 Unprocessable Entity`.

---

### B. Control Strength ($\text{CS}$) Engine & Finding Penalty Versioning
Control Strength ($\text{CS}$) represents the resistance capability of mitigating controls against threat capabilities.

#### 1. Base Control Strength ($\text{CS}_{\text{base}}$)
- When linked to an `OrganizationControl` with an active Phase 7 Continuous Control Monitoring (CCM) Health Score ($S_{\text{CCM}} \in [0.0, 100.0]$):
  $$\text{CS}_{\text{base}} = \frac{S_{\text{CCM}}}{100.0}$$
- When linked to an `OrganizationControl` without active CCM telemetry, $\text{CS}_{\text{base}}$ defaults to the baseline control status:
  - `IMPLEMENTED` $\rightarrow 0.70$
  - `PARTIALLY_IMPLEMENTED` $\rightarrow 0.40$
  - `PLANNED` $\rightarrow 0.10$
  - `NOT_APPLICABLE` $\rightarrow 0.00$
- When unlinked to a specific control, $\text{CS}_{\text{base}}$ is derived from the user-configured scenario baseline.

#### 2. Severity-Weighted Active Finding Deductions
Active Phase 4 findings linked to the control degrade its resistance strength.

```
Rule Version: PENALTY_RULE_2026_1
Active Finding Statuses: OPEN, IN_REMEDIATION, PENDING_VALIDATION
Inactive Finding Statuses (Zero Penalty): RESOLVED, ACCEPTED_RISK, CLOSED
```

| Finding Severity (`FindingSeverityEnum`) | Penalty Weight ($w_i$) |
|:---|:---:|
| `CRITICAL` | $0.25$ |
| `HIGH` | $0.15$ |
| `MEDIUM` | $0.08$ |
| `LOW` | $0.03$ |
| `INFORMATIONAL` | $0.00$ |

#### 3. Total Stacking Penalty & Final Control Strength ($\text{CS}$)
$$\text{Penalty}_{\text{total}} = \min\left(1.0, \sum_{i \in \text{ActiveFindings}} w_i\right)$$

$$\text{CS} = \text{clamp}\left(\text{CS}_{\text{base}} \times (1.0 - \text{Penalty}_{\text{total}}), 0.0, 1.0\right)$$

---

### C. Vulnerability Factor ($\text{VULN}$)
Given Threat Capability ($\text{TCAP} \in [0.0, 1.0]$) and Control Strength ($\text{CS} \in [0.0, 1.0]$):

$$\text{VULN} = \text{clamp}\left(\text{TCAP} \times (1.0 - \text{CS}), 0.0, 1.0\right)$$

- If $\text{CS} = 1.0$ ($100\%$ effective control), $\text{VULN} = 0.0$.
- If $\text{CS} = 0.0$ ($0\%$ effective control), $\text{VULN} = \text{TCAP}$.

---

### D. Loss Event Frequency ($\text{LEF}$)
Given Threat Event Frequency parameters ($\text{TEF}_{\min}, \text{TEF}_{\text{mode}}, \text{TEF}_{\max}$):

$$\text{TEF}_{\text{mean}} = \frac{\text{TEF}_{\min} + 4 \times \text{TEF}_{\text{mode}} + \text{TEF}_{\max}}{6}$$

$$\text{LEF} = \text{TEF}_{\text{mean}} \times \text{VULN} \quad [\text{events/year}]$$

> [!NOTE]
> A valid scenario is permitted to yield $\text{LEF} = 0.00$ (e.g., when $\text{TEF} = 0$ or $\text{VULN} = 0$). No artificial lower bounds are imposed.

---

### E. Loss Magnitude Decomposition & Single Loss Expectancy ($\text{SLE}$)

#### 1. Primary Loss ($\text{PL}$)
Direct losses from the incident (incident response, forensic investigation, system restoration, operational outage):
$$\text{PL}_{\text{mean}} = \frac{\text{PL}_{\min} + 4 \times \text{PL}_{\text{mode}} + \text{PL}_{\max}}{6} \quad [\text{USD/event}]$$

#### 2. Secondary Loss ($\text{SL}$)
Conditional losses from external stakeholders (regulatory fines, legal settlements, customer churn, vendor default):
$$\text{SL}_{\text{mean}} = \frac{\text{SL}_{\min} + 4 \times \text{SL}_{\text{mode}} + \text{SL}_{\max}}{6} \quad [\text{USD/event}]$$

Given Secondary Loss Event Probability ($\text{SLoP} \in [0.0, 1.0]$):
$$\text{ExpectedSecondaryLoss} = \text{SL}_{\text{mean}} \times \text{SLoP} \quad [\text{USD/event}]$$

#### 3. Mean Loss Magnitude ($\text{MLM}$) and Single Loss Expectancy ($\text{SLE}$)
$$\text{SLE} = \text{MLM} = \text{PL}_{\text{mean}} + \text{ExpectedSecondaryLoss} \quad [\text{USD/event}]$$

---

### F. Annualized Loss Expectancy ($\text{ALE}$)
$$\text{ALE} = \text{LEF} \times \text{SLE} \quad [\text{USD/year}]$$

#### Dimensional Consistency Proof:
$$[\text{ALE}] = \left[\frac{\text{events}}{\text{year}}\right] \times \left[\frac{\text{USD}}{\text{event}}\right] = \left[\frac{\text{USD}}{\text{year}}\right]$$

---

### G. Dual-Tier Value at Risk ($\text{VaR}$) Formulation

#### 1. Primary Authority: Empirical Simulation $\text{VaR}$ ($\text{VaR}^{\text{sim}}$)
The authoritative metric displayed on governance dashboards is derived directly from the empirical order statistics of $N = 10,000$ simulation trials:
$$\text{VaR}_{95\%}^{\text{sim}} = \text{Percentile}\left(\{L_1, L_2, \dots, L_N\}, 95.0\right)$$
$$\text{VaR}_{99\%}^{\text{sim}} = \text{Percentile}\left(\{L_1, L_2, \dots, L_N\}, 99.0\right)$$

#### 2. Analytical Comparison: Parametric Lognormal $\text{VaR}$ ($\text{VaR}^{\text{param}}$)
To provide rapid validation without running full simulations, the parametric lognormal approximation is derived from the compound mean ($\mu_{\text{loss}}$) and compound variance ($\sigma^2_{\text{loss}}$):

$$\mu_{\text{loss}} = \text{ALE} = \text{LEF} \times \text{MLM}$$

$$\sigma^2_{\text{loss}} = \text{LEF} \times (\sigma^2_{\text{PL}} + \text{SLoP} \times \sigma^2_{\text{SL}}) + \text{LEF} \times \text{MLM}^2$$

The lognormal location ($\mu_{\ln}$) and scale ($\sigma_{\ln}$) parameters are calculated as:
$$\sigma_{\ln} = \sqrt{\ln\left(1 + \frac{\sigma^2_{\text{loss}}}{\mu^2_{\text{loss}}}\right)}$$
$$\mu_{\ln} = \ln(\mu_{\text{loss}}) - \frac{1}{2} \sigma^2_{\ln}$$

Parametric Value-at-Risk at $(1 - \alpha)$ confidence:
$$\text{VaR}_{1-\alpha}^{\text{param}} = \exp\left(\mu_{\ln} + z_{1-\alpha} \times \sigma_{\ln}\right)$$
- For $95\%$ confidence: $z_{0.95} = 1.644853$
- For $99\%$ confidence: $z_{0.99} = 2.326348$

---

### H. Return on Security Investment ($\text{ROSI}$) Engine
The ROSI engine computes the financial return of executing a Phase 11 Remediation Plan (`RemediationPlan`):

$$\Delta \text{ALE} = \text{ALE}_{\text{current}} - \text{ALE}_{\text{projected}}$$

$$\text{NetEconomicBenefit} = \Delta \text{ALE} - \text{RemediationCost}$$

$$\text{ROSI} = \left(\frac{\text{NetEconomicBenefit}}{\text{RemediationCost}}\right) \times 100\% = \left(\frac{(\text{ALE}_{\text{current}} - \text{ALE}_{\text{projected}}) - \text{RemediationCost}}{\text{RemediationCost}}\right) \times 100\%$$

#### Invariants:
- $\text{RemediationCost} > 0.00$ (must be strictly positive).
- If $\text{RemediationCost} \le 0$, the request fails validation with `HTTP 422 Unprocessable Entity`.
- Negative ROSI values (where remediation cost exceeds risk reduction) are valid economic indicators and correctly reported.

---

### I. Financial Risk Appetite & Breach Governance
Organizations configure board-approved quantitative appetite thresholds:
- $\text{ALE}_{\text{limit}}$: Maximum acceptable annual expected loss in USD.
- $\text{VaR}_{95\%\text{limit}}$: Maximum acceptable tail loss at 95% confidence in USD.

#### Portfolio Appetite Evaluation State:
$$\text{Status} = \begin{cases}
\text{WITHIN\_APPETITE} & \text{if } \text{ALE} \le \text{ALE}_{\text{limit}} \land \text{VaR}_{95\%} \le \text{VaR}_{95\%\text{limit}} \\
\text{EXCEEDS\_ALE} & \text{if } \text{ALE} > \text{ALE}_{\text{limit}} \land \text{VaR}_{95\%} \le \text{VaR}_{95\%\text{limit}} \\
\text{EXCEEDS\_VAR} & \text{if } \text{ALE} \le \text{ALE}_{\text{limit}} \land \text{VaR}_{95\%} > \text{VaR}_{95\%\text{limit}} \\
\text{EXCEEDS\_BOTH} & \text{if } \text{ALE} > \text{ALE}_{\text{limit}} \land \text{VaR}_{95\%} > \text{VaR}_{95\%\text{limit}}
\end{cases}$$

#### Four-Eyes Appetite Governance:
- Changes to `FinancialRiskAppetite` require four-eyes review (`requester_id != approver_id`).
- Approved appetite configurations become **immutable** historical snapshots; updates create new sequential versions.

---

### J. Capital Allocation Scope Definition
To prevent ambiguous algorithmic claims, Capital Allocation in Phase 12 is explicitly defined as:
1. **Marginal ROSI Remediation Prioritization**: Ranking candidate Phase 11 CAPA plans by $\frac{\Delta \text{ALE}}{\text{RemediationCost}}$ to identify maximum risk reduction per dollar spent.
2. **Deterministic Risk Capital Reservation**: Sizing required enterprise cyber risk reserves based on portfolio $\text{VaR}_{95\%} - \text{ALE}$.
3. *Theoretical portfolio-variance optimization algorithms are explicitly deferred.*

---

## 5. SOURCE-OF-TRUTH & AUTHORITY MATRIX

| Module / Entity | Source of Truth | Client Mutable? | Server Derived? | Historical? | Tenant Scoped? | Immutability Rule |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| **Phase 5 Qualitative Risk** | `risks` | Yes (in P5) | No | Yes | Yes | Independent baseline. P12 cannot mutate. |
| **Phase 7 CCM Health** | `control_health_snapshots` | No | Yes (P7) | Yes | Yes | Read-only input for $\text{CS}_{\text{base}}$. |
| **Phase 9 TPRM Vendor Risk** | `vendors` | Yes (in P9) | Yes (P9) | Yes | Yes | Read-only threat modifier. |
| **Phase 10 Incident Losses** | `security_incidents` | Yes (in P10) | Yes (P10) | Yes | Yes | Read-only baseline for loss magnitude calibration. |
| **Phase 11 Remediation Plan** | `remediation_plans` | Yes (in P11) | Yes (P11) | Yes | Yes | Read-only input for ROSI cost and REI. |
| **Phase 12 Scenario Inputs** | `quant_risk_scenarios` | Yes (in Draft) | No | No | Yes | Mutable in `DRAFT`; immutable once `FROZEN`. |
| **Phase 12 Calculated Metrics** | `quant_risk_scenarios` | **NO** | **YES** | Yes | Yes | Server-authoritative ($\text{LEF}, \text{SLE}, \text{ALE}, \text{VaR}$). |
| **Phase 12 Simulation Runs** | `quant_simulation_runs` | **NO** | **YES** | Yes | Yes | **100% Immutable** upon creation. |
| **Phase 12 ROSI Analysis** | `rosi_analyses` | Yes (Inputs) | Yes (Metrics) | Yes | Yes | Historical calculations immutable. |
| **Phase 12 Risk Appetite** | `financial_risk_appetites` | Yes (Draft) | Yes (Status) | Yes | Yes | Immutable once approved (four-eyes). |

---

## 6. DOMAIN ENTITY ARCHITECTURE (STAGE 1 SPECIFICATION)

### 1. `QuantitativeRiskScenario` (`quant_risk_scenarios`)
- `id: int` (Primary Key)
- `organization_id: int` (Foreign Key $\rightarrow$ `organizations.id`, Non-nullable, Indexed)
- `scenario_code: str` (Unique per tenant, e.g. `QRS-2026-001`)
- `title: str`, `description: str`
- `status: Enum(ScenarioStatusEnum)` (`DRAFT`, `ACTIVE`, `FROZEN`, `ARCHIVED`)
- `threat_actor_category: Enum(ThreatActorCategoryEnum)` (`CYBERCRIMINAL`, `NATION_STATE`, `INSIDER`, `HACKTIVIST`, `ACCIDENTAL`)
- **Upstream References (Nullable FKs)**:
  - `risk_id: int` (Optional link to Phase 5 `risks.id`)
  - `organization_control_id: int` (Optional link to Phase 2 `organization_controls.id`)
  - `vendor_id: int` (Optional link to Phase 9 `vendors.id`)
- **Three-Point Threat & Loss Inputs**:
  - `tef_min: float`, `tef_mode: float`, `tef_max: float`
  - `tcap: float` (Threat capability $[0.0, 1.0]$)
  - `pl_min: float`, `pl_mode: float`, `pl_max: float`
  - `sl_min: float`, `sl_mode: float`, `sl_max: float`
  - `slop: float` (Secondary loss probability $[0.0, 1.0]$)
- **Server-Authoritative Computed Fields**:
  - `control_strength: float` ($\text{CS} \in [0.0, 1.0]$)
  - `vulnerability_factor: float` ($\text{VULN} \in [0.0, 1.0]$)
  - `loss_event_frequency: float` ($\text{LEF}$)
  - `single_loss_expectancy: float` ($\text{SLE}$)
  - `annualized_loss_expectancy: float` ($\text{ALE}$)
  - `var_95_parametric: float`
  - `var_99_parametric: float`
  - `var_95_empirical: float` (populated after simulation)
  - `var_99_empirical: float` (populated after simulation)
- **Snapshotting & Immutability**:
  - `is_immutable: bool` (default `False`)
  - `calculation_version: str` (`"2026.12.1"`)
  - `input_snapshot_hash: str` (SHA-256 hash of all upstream inputs)
  - `calculated_at: datetime`
  - `created_by_id: int`, `created_at: datetime`, `updated_at: datetime`

### 2. `QuantitativeSimulationRun` (`quant_simulation_runs`)
- `id: int` (Primary Key)
- `organization_id: int` (Foreign Key $\rightarrow$ `organizations.id`)
- `scenario_id: int` (Foreign Key $\rightarrow$ `quant_risk_scenarios.id`)
- `trial_count: int` (e.g. $10,000$, range $100 - 50,000$)
- `simulation_seed: int` (For exact determinism and reproducibility)
- `algorithm_version: str` (`"SIM_PERT_V1"`)
- `mean_loss: float`, `variance_loss: float`, `std_dev_loss: float`
- `percentile_10: float`, `percentile_50: float`, `percentile_90: float`, `percentile_95: float`, `percentile_99: float`
- `simulated_by_id: int`, `simulated_at: datetime`

### 3. `RosiAnalysis` (`rosi_analyses`)
- `id: int` (Primary Key)
- `organization_id: int` (Foreign Key $\rightarrow$ `organizations.id`)
- `scenario_id: int` (Foreign Key $\rightarrow$ `quant_risk_scenarios.id`)
- `remediation_plan_id: int` (Foreign Key $\rightarrow$ `remediation_plans.id`)
- `remediation_cost: float` ($> 0.0$)
- `current_ale: float`, `projected_ale: float`
- `risk_reduction_ale: float` ($\Delta \text{ALE}$)
- `net_economic_benefit: float`
- `rosi_percentage: float`
- `created_by_id: int`, `created_at: datetime`

### 4. `FinancialRiskAppetite` (`financial_risk_appetites`)
- `id: int` (Primary Key)
- `organization_id: int` (Foreign Key $\rightarrow$ `organizations.id`)
- `version: int` (Sequential per tenant: 1, 2, 3...)
- `ale_limit: float` (Board-approved ALE threshold in USD)
- `var_95_limit: float` (Board-approved VaR threshold in USD)
- `status: Enum(AppetiteStatusEnum)` (`DRAFT`, `APPROVED`, `SUPERSEDED`)
- `requested_by_id: int`, `approved_by_id: int` (Four-eyes: `requested_by != approved_by`)
- `created_at: datetime`, `approved_at: datetime`

---

## 7. STALE CCM TELEMETRY POLICY

When a scenario is linked to an `OrganizationControl` and queries Phase 7 Continuous Control Monitoring:
- **Definition of Stale**: A CCM snapshot is classified as **STALE** if the latest snapshot timestamp is older than **30 days** (`now - snapshot.created_at > 30 days`) or if no snapshot exists.
- **Deterministic Resolution Behavior**:
  1. If a snapshot exists but is stale, the engine uses the snapshot score but attaches a `is_ccm_stale: True` flag and emits a `STALE_CCM_WARNING` in the response payload.
  2. If no CCM snapshot exists at all, the engine falls back to the baseline control status mapping (`IMPLEMENTED=0.70`, etc.) and sets `ccm_telemetry_source = "CONTROL_BASELINE"`.
  3. The exact telemetry state and snapshot timestamp are recorded in the immutable `input_snapshot_hash`.

---

## 8. RBAC PERMISSION MATRIX

| Role | `quantrisk:read` | `quantrisk:manage` | `quantrisk:execute` | `quantrisk:approve` | Description |
|:---|:---:|:---:|:---:|:---:|:---|
| **ADMIN** | Yes | Yes | Yes | Yes | Full control over scenarios, simulations, ROSI, and appetite approval. |
| **MANAGER** | Yes | Yes | Yes | Yes | Full control over scenarios, simulations, ROSI, and appetite approval. |
| **GRC_ANALYST** | Yes | Yes | Yes | No | Scenario CRUD, simulation execution, ROSI analysis (cannot approve appetite). |
| **SECURITY_ANALYST** | Yes | Yes | Yes | No | Scenario CRUD, simulation execution, ROSI analysis (cannot approve appetite). |
| **AUDITOR** | Yes | No | No | No | Strict read-only audit inspection of quantitative models and simulations. |
| **VIEWER** | Yes | No | No | No | Strict read-only dashboard observation. |

---

## 9. AUDIT LOGGING SPECIFICATION

All Phase 12 operations trigger immutable structured events in `audit_logs`:
- `QUANTRISK_SCENARIO_CREATED`
- `QUANTRISK_SCENARIO_UPDATED`
- `QUANTRISK_SCENARIO_FROZEN`
- `QUANTRISK_SIMULATION_EXECUTED`
- `QUANTRISK_ROSI_CALCULATED`
- `QUANTRISK_APPETITE_CREATED`
- `QUANTRISK_APPETITE_APPROVED`
- `QUANTRISK_APPETITE_SUPERSEDED`

---

## 10. ADV-P12 ADVERSARIAL ATTACK DEFENSE MATRIX

| Vector ID | Attack Vector | Expected Result | Enforcement Mechanism | Layer |
|:---|:---|:---:|:---|:---:|
| `ADV-P12-01` | Cross-Tenant Scenario Read (IDOR) | **HTTP 404** | Filter `organization_id == current_user.organization_id` | API / Router |
| `ADV-P12-02` | Cross-Tenant Scenario Mutation | **HTTP 404** | Tenant check in `get_scenario_by_id` | Domain Service |
| `ADV-P12-03` | Foreign Phase 5 Risk ID Injection | **HTTP 404** | Validates `Risk.organization_id == current_user.organization_id` | Domain Service |
| `ADV-P12-04` | Foreign Phase 2 Control ID Injection | **HTTP 404** | Validates `OrganizationControl.organization_id == user.org_id` | Domain Service |
| `ADV-P12-05` | Foreign Phase 9 Vendor ID Injection | **HTTP 404** | Validates `Vendor.organization_id == current_user.organization_id` | Domain Service |
| `ADV-P12-06` | Foreign Phase 11 Plan ID in ROSI | **HTTP 404** | Validates `RemediationPlan.organization_id == user.org_id` | Domain Service |
| `ADV-P12-07` | Organization ID Spoofing in Payload | **Ignored** | Overwritten by JWT `current_user.organization_id` | Endpoint Dependency |
| `ADV-P12-08` | Client Injection of Financial Metrics | **Ignored** | Excluded from create/update schemas; computed server-side | Pydantic Schema |
| `ADV-P12-09` | Client Control Strength Injection | **Ignored** | Derived strictly from Phase 7 CCM / Findings engine | Domain Service |
| `ADV-P12-10` | Inverted Loss Ranges ($a > m$ or $m > b$) | **HTTP 422** | Pydantic model validator `@root_validator` + DB CHECK | Schema & DB |
| `ADV-P12-11` | Negative Frequency or Loss Amounts | **HTTP 422** | `Field(ge=0.0)` validation + DB CHECK constraints | Schema & DB |
| `ADV-P12-12` | Risk Appetite Self-Approval Violation | **HTTP 403** | Four-eyes check `approver_id != requested_by_id` | Domain Service |
| `ADV-P12-13` | Direct Mutation of Historical Simulation | **HTTP 409** | Rejects PATCH/PUT on `quant_simulation_runs` | API Router |
| `ADV-P12-14` | Unauthorized Simulation Execution (Viewer) | **HTTP 403** | RBAC permission check `quantrisk:execute` | Permission Guard |
| `ADV-P12-15` | Zero or Negative Remediation Cost in ROSI | **HTTP 422** | `Field(gt=0.0)` strictly enforced on remediation cost | Pydantic Schema |
| `ADV-P12-16` | Stale CCM Telemetry Exploitation | **Handled** | Deterministic 30-day staleness tag and fallback logging | Domain Engine |
| `ADV-P12-17` | Cross-Tenant Appetite Modification | **HTTP 404** | Tenant check on `FinancialRiskAppetite` | Domain Service |
| `ADV-P12-18` | Non-Existent Upstream Reference ID | **HTTP 404** | Verifies existence of referenced entity before linkage | Domain Service |
| `ADV-P12-19` | Mutation of Frozen Baseline Scenario | **HTTP 409** | Rejects updates when `is_immutable == True` or `status==FROZEN` | Domain Service |
| `ADV-P12-20` | Simulation Trial Count Exhaustion ($>50k$) | **HTTP 422** | Enforces `Field(ge=100, le=50000)` on trial counts | Pydantic Schema |

---

## 11. MATHEMATICAL EDGE CASES EVALUATION

| Edge Case Scenario | Mathematical Condition | Engine Handling & Result |
|:---|:---|:---|
| **Zero Threat Event Frequency** | $\text{TEF}_{\min} = \text{TEF}_{\text{mode}} = \text{TEF}_{\max} = 0.0$ | $\text{LEF} = 0.0$, $\text{ALE} = \$0.00$, $\text{VaR}_{95\%} = \$0.00$. Valid zero-risk scenario. |
| **Zero Vulnerability / Perfect Control** | $\text{CS} = 1.0 \implies \text{VULN} = 0.0$ | $\text{LEF} = 0.0$, $\text{ALE} = \$0.00$. Controls completely mitigate threat. |
| **Zero Loss Magnitude** | $\text{PL} = 0, \text{SL} = 0$ | $\text{SLE} = \$0.00$, $\text{ALE} = \$0.00$. Zero financial loss. |
| **Deterministic Distribution** | $\text{Min} = \text{Mode} = \text{Max}$ | $\mu = \text{Min}$, $\sigma = 0.0$. Handled as deterministic constant in simulation. |
| **$100\%$ Secondary Loss Probability** | $\text{SLoP} = 1.0$ | $\text{ExpectedSecondaryLoss} = \text{SL}_{\text{mean}}$. Full secondary loss added. |
| **$0\%$ Secondary Loss Probability** | $\text{SLoP} = 0.0$ | $\text{ExpectedSecondaryLoss} = \$0.00$. Only primary loss applied. |
| **Huge Financial Losses** | $\text{Loss} = \$10^{11}$ ($100$ Billion USD) | Supported with 64-bit IEEE 754 precision; no overflow. |
| **Zero Remediation Cost in ROSI** | $\text{Cost} = 0$ | Rejected with `HTTP 422` (division by zero prevented). |
| **Negative ROSI** | $\Delta \text{ALE} < \text{Cost}$ | Returns negative percentage (e.g. $-45.2\%$). Valid economic return. |
| **Missing CCM Telemetry** | Control unmonitored | Falls back to control baseline implementation tier ($0.70/0.40/0.10/0.00$). |
| **Missing Active Findings** | Control has 0 active findings | $\text{Penalty}_{\text{total}} = 0.0 \implies \text{CS} = \text{CS}_{\text{base}}$. |
| **Finding Penalties $> 1.0$** | Multiple critical findings | $\text{Penalty}_{\text{total}}$ clamped to $1.0 \implies \text{CS} = 0.0$. |

---

## 12. VERSIONING IDENTIFIERS

```python
CALCULATION_VERSION = "2026.12.1"
ALGORITHM_VERSION   = "SIM_PERT_V1"
RULE_VERSION        = "PENALTY_RULE_2026_1"
```

---

## 13. STAGE 1 IMPLEMENTATION CONTRACT

When Phase 12 Stage 1 is authorized, the implementation will deliver:
1. **Alembic Migration**: `0012_cyber_risk_quantification.py` (`0011` $\rightarrow$ `0012`).
2. **SQLAlchemy Models** in `backend/app/models/quant_risk.py`:
   - `QuantitativeRiskScenario`
   - `QuantitativeSimulationRun`
   - `RosiAnalysis`
   - `FinancialRiskAppetite`
3. **Model Base Registration** in `backend/app/models/__init__.py`.
4. **Pydantic Schemas** in `backend/app/schemas/quant_risk.py`.
5. **RBAC Permission Constants** in `backend/app/core/permissions.py`.
6. **Mathematical Calculation Engine** in `backend/app/services/quant_risk_service.py`.
7. **Domain Unit & Mathematical Verification Tests** in `backend/tests/test_quant_risk_domain.py`.

---

## 14. STAGE 0 VERIFICATION CHECKLIST

- [x] No migration `0012` created.
- [x] No production code in `backend/` or `frontend/` modified.
- [x] Dependencies added: **0 Python, 0 Node**.
- [x] Full mathematical consistency across Beta-PERT, LEF, SLE, ALE, VaR, and ROSI.
- [x] Dimensional analysis proven ($[\text{events/year}] \times [\text{USD/event}] = [\text{USD/year}]$).
- [x] Dual-tier VaR distinction mathematically defined and justified.
- [x] Complete ADV-P12 adversarial defense matrix specified.
- [x] Working tree clean and verified.

---

PHASE 12 STAGE 0 — ARCHITECTURAL HARDENING COMPLETE
STATUS: GO FOR STAGE 1
