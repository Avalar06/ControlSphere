# ControlSphere Phase 7 — Canonical Continuous Control Monitoring (CCM) Specification

**Authoritative Baseline Reference**: Phase 7 Continuous Control Monitoring & Health Telemetry  
**Status**: APPROVED & CANONICAL  
**Enforcement**: Server-Authoritative (Backend Engine)

---

## 1. Evidence Freshness Metric ($E$)

For a control $c$ and tenant $T$:
Let $t_{\text{now}}$ be the authoritative evaluation UTC timestamp.
Let $\mathcal{E}_A(c)$ be the set of all accepted evidence items linked to control $c$ for tenant $T$.

1. **No Accepted Evidence** ($\mathcal{E}_A(c) = \emptyset$):
   $$E(c) = 0.0, \quad \Delta_{\text{ev}}(c) = \text{None}$$
2. **Accepted Evidence Present** ($\mathcal{E}_A(c) \neq \emptyset$):
   Let $e_{\text{latest}}$ be the evidence item with the most recent `created_at` timestamp.
   $$\Delta_{\text{ev}}(c) = \max\Big(0, \lfloor (t_{\text{now}} - t_{\text{latest}}) \rfloor_{\text{days}}\Big)$$
   - **Fresh Evidence** ($\Delta_{\text{ev}}(c) \le \tau_{\text{ev}}$ where $\tau_{\text{ev}} = \text{evidence\_max\_age\_days}$, default 90 days):
     $$E(c) = 100.0$$
   - **Stale Evidence** ($\Delta_{\text{ev}}(c) > \tau_{\text{ev}}$):
     Decays linearly over a window of $\tau_{\text{ev}}$ days:
     $$\text{overage} = \Delta_{\text{ev}}(c) - \tau_{\text{ev}}$$
     $$E(c) = \text{round}\Big(\max\big(0.0, 1.0 - \frac{\text{overage}}{\tau_{\text{ev}}}\big) \times 100.0, 1\Big)$$

---

## 2. Assessment Currency Metric ($A$)

Let $S(c)$ be the implementation status of control $c$:

1. **`IMPLEMENTED`**:
   - Assessed within threshold ($\Delta_{\text{assess}}(c) \le \tau_{\text{assess}}$, default 180 days):
     $$A(c) = 100.0$$
   - Overdue assessment ($\Delta_{\text{assess}}(c) > \tau_{\text{assess}}$):
     $$A(c) = 60.0$$
2. **`PARTIALLY_IMPLEMENTED`**:
   $$A(c) = 50.0$$
3. **`IN_PROGRESS`** / **`NEEDS_REVIEW`**:
   $$A(c) = 25.0$$
4. **`NOT_STARTED`** / **`NOT_APPLICABLE`**:
   $$A(c) = 0.0$$

---

## 3. Finding Penalty Score ($P_F$)

Let $\mathcal{F}_{\text{open}}(c)$ be the set of open findings linked to control $c$ where:
$$\text{status} \notin \{\text{RESOLVED}, \text{CLOSED}, \text{ACCEPTED\_RISK}\}$$

For each $f \in \mathcal{F}_{\text{open}}(c)$, let $\text{age}(f) = \lfloor (t_{\text{now}} - t_{\text{created}})\rfloor_{\text{days}}$:
- **`CRITICAL`**:
  $$\text{penalty}(f) = 20.0 + \begin{cases} 10.0 & \text{if } \text{age}(f) > \tau_{\text{sla\_crit}} \text{ (default 15d)} \\ 0.0 & \text{otherwise} \end{cases}$$
- **`HIGH`**:
  $$\text{penalty}(f) = 10.0 + \begin{cases} 5.0 & \text{if } \text{age}(f) > \tau_{\text{sla\_high}} \text{ (default 30d)} \\ 0.0 & \text{otherwise} \end{cases}$$
- **`MEDIUM`**:
  $$\text{penalty}(f) = 4.0$$
- **`LOW`** / **`INFO`**:
  $$\text{penalty}(f) = 1.0$$

$$P_F(c) = \sum_{f \in \mathcal{F}_{\text{open}}(c)} \text{penalty}(f)$$

---

## 4. Exception Penalty Score ($P_E$)

Let $\mathcal{X}_{\text{active}}(c)$ be the set of security exceptions linked to control $c$ where $\text{status} \in \{\text{APPROVED}, \text{ACTIVE}\}$.

For each $x \in \mathcal{X}_{\text{active}}(c)$:
$$\text{penalty}(x) = \begin{cases} 15.0 & \text{if } x.\text{expiry\_date} < t_{\text{now}}.\text{date()} \text{ (Expired Active Exception)} \\ 5.0 & \text{otherwise (Active Approved Exception)} \end{cases}$$

$$P_E(c) = \sum_{x \in \mathcal{X}_{\text{active}}(c)} \text{penalty}(x)$$

---

## 5. Authoritative Control Health Score Formula

$$\text{raw\_score}(c) = \big(E(c) \times 0.35\big) + \big(A(c) \times 0.25\big) + \Big(40.0 - \min\big(40.0, P_F(c) + P_E(c)\big)\Big)$$

$$\text{HealthScore}(c) = \text{round}\Big(\max\big(0.0, \min(100.0, \text{raw\_score}(c))\big), 1\Big)$$

### Mathematical Guarantees:
1. **Upper Bound**: In a baseline state with fresh evidence ($E=100$), current assessment ($A=100$), and 0 penalties ($P_F=0, P_E=0$), $\text{HealthScore}(c) = 35.0 + 25.0 + 40.0 = 100.0\%$.
2. **Lower Bound**: $E \times 0.35 \ge 0$, $A \times 0.25 \ge 0$, and $(40.0 - \min(40.0, P_F + P_E)) \ge 0$. Therefore, $\text{raw\_score} \ge 0.0$ at all times, preventing arithmetic underflow.
3. **Deterministic Clamping**: Explicitly bounded in $[0.0, 100.0]$ rounded to 1 decimal place.

---

## 6. Health Status Bands

| Health Band | Score Range | Operational Meaning |
|:---|:---|:---|
| **`HEALTHY`** | $[80.0, 100.0]$ | Control is compliant, evidence fresh, findings/exceptions minimal. |
| **`DEGRADED`** | $[60.0, 79.9]$ | Evidence nearing expiration or minor/moderate gap detected. |
| **`AT_RISK`** | $[40.0, 59.9]$ | Significant gap, stale evidence, or open high finding present. |
| **`FAILING`** | $[0.0, 39.9]$ | Critical deficiency, SLA breach, unmitigated gaps, or expired exceptions. |

---

## 7. Compliance Drift Alert Rules & Generation

During an evaluation run, the engine deterministically checks for 7 drift alert conditions per control:

1. **`EVIDENCE_MISSING`** (Severity: `HIGH`): Triggered if control has no accepted evidence items.
2. **`EVIDENCE_EXPIRED`** (Severity: `MEDIUM`): Triggered if $\Delta_{\text{ev}}(c) > \tau_{\text{ev}}$.
3. **`ASSESSMENT_OVERDUE`** (Severity: `MEDIUM`): Triggered if control status is `IMPLEMENTED` but unassessed for $> \tau_{\text{assess}}$ days.
4. **`CRITICAL_FINDING_SLA_BREACH`** (Severity: `CRITICAL`): Triggered if an open critical finding has $\text{age} > \tau_{\text{sla\_crit}}$.
5. **`EXCEPTION_EXPIRING_SOON`** (Severity: `MEDIUM`): Triggered if an active exception expires within $\tau_{\text{exc\_warn}}$ (default 14 days).
6. **`EXCEPTION_EXPIRED`** (Severity: `HIGH`): Triggered if an active exception is past its expiry date.
7. **`CONTROL_DEGRADED`** (Severity: `CRITICAL` for `FAILING`, `HIGH` for `AT_RISK`): Triggered if health status drops to `AT_RISK` or `FAILING`.

---

## 8. Alert Lifecycle & Immutability

```
        ┌──────────────┐
        │    ACTIVE    │
        └──────┬───────┘
               │
      ┌────────┴────────┐
      ▼                 ▼
┌──────────────┐  ┌───────────┐
│ ACKNOWLEDGED │  │ DISMISSED │ (Terminal State, Requires Justification)
└──────┬───────┘  └───────────┘
       │
       ▼
┌──────────────┐
│   RESOLVED   │ (Terminal State, Requires Resolution Notes)
└──────────────┘
```

1. **Active Alerts**: Can be acknowledged, resolved, or dismissed.
2. **Acknowledged Alerts**: Can be resolved or dismissed. Cannot be re-acknowledged.
3. **Resolved Alerts (Terminal)**: Cannot be acknowledged, dismissed, or re-resolved.
4. **Dismissed Alerts (Terminal)**: Cannot be acknowledged, resolved, or re-dismissed.

---

## 9. Multi-Tenancy & Authorization Security

1. **Tenant Derivation**: All database queries must derive `organization_id` strictly from `current_user.organization_id`.
2. **Zero Client Trust**:
   - Client cannot supply or alter `organization_id`, `actor_id`, `actor_email`, `health_score`, or `created_at`.
   - All evaluation timestamps are generated on the server using UTC (`datetime.now(timezone.utc)`).
3. **RBAC Permission Matrix**:
   - `monitoring:read`: Granted to `ADMIN`, `SECURITY_ENGINEER`, `COMPLIANCE_OFFICER`, `GRC_ANALYST`, `AUDITOR`, `VIEWER`.
   - `monitoring:execute`: Granted to `ADMIN`, `SECURITY_ENGINEER`, `COMPLIANCE_OFFICER`, `GRC_ANALYST`.
   - `monitoring:manage`: Granted to `ADMIN`, `SECURITY_ENGINEER`, `COMPLIANCE_OFFICER`.
   - `monitoring:alert_action`: Granted to `ADMIN`, `SECURITY_ENGINEER`, `COMPLIANCE_OFFICER`, `GRC_ANALYST`.

---

## 10. Audit Logging Specification

Immutable audit logs are written for:
- `monitoring.evaluate`: Records trigger, evaluated count, alerts count, average health score.
- `monitoring.alert_acknowledge`: Records alert ID, alert type, severity.
- `monitoring.alert_resolve`: Records alert ID, alert type, resolution notes.
- `monitoring.alert_dismiss`: Records alert ID, alert type, dismissal justification.
- `monitoring.config_update`: Records updated threshold parameters.
