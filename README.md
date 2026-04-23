# FinOps Azure Cost Optimization Skill

A Claude skill that scans Azure resource groups for common waste patterns and savings opportunities using the `az` CLI.

## What It Does

Given a subscription and a set of resource groups, the skill auto-detects which Azure resource types are deployed, runs the applicable finders, and produces a ranked report of waste and optimization opportunities.

### Finders Included

| # | Finder | Data Source | What It Detects |
|---|--------|------------|-----------------|
| 1 | storage_compute_inversion | Cost Management | Storage cost > 13.5x compute cost in an RG |
| 2 | staging_continuous | Cost Management | Dev/staging RGs billing 24/7 for 3+ months |
| 3 | redis_idle | ARG + Monitor | Redis caches with zero commands for 30 days |
| 4 | laws_workspace_sprawl | ARG + Monitor | Multiple Log Analytics workspaces that could be consolidated |
| 5 | vm_idle | ARG + Monitor | VMs with avg CPU < 5% and max CPU < 55% |
| 6 | vm_legacy_series | ARG | VMs on v2/v3 or older SKU families |
| 7 | unattached_managed_disks | ARG | Managed disks not attached to any VM |
| 8 | orphaned_public_ips | ARG | Public IPs not associated to any resource |
| 9 | idle_app_service_plans | ARG + Monitor | App Service Plans with zero apps or very low CPU |
| 10 | snapshot_accumulation | ARG | Disk snapshots older than 90 days |
| 11 | stopped_not_deallocated_vms | ARG | Stopped VMs still incurring compute charges |
| 12 | idle_sql_databases | ARG + Monitor | SQL databases with avg CPU < 10% and max CPU < 60% |

## Prerequisites

- **Azure CLI** (`az`) installed and authenticated
- **Reader access** to the target subscription
- **Access** to Azure Monitor metrics and Cost Management data

## Usage

The skill prompts for three inputs:

1. **Subscription** — name or ID
2. **Resource groups** — one or more (required, max 30)
3. **Report format** — CSV (default), Markdown, or Both

### Specifying Resource Groups

You can use exact names, wildcard patterns, or a mix of both.

**Exact names:**
```
rg-orders-prod, rg-payments-prod
```

**Wildcard patterns:**
```
rg-orders-*
```
Matches: `rg-orders-prod`, `rg-orders-staging`, `rg-orders-dev`

```
*-prod
```
Matches: `rg-orders-prod`, `rg-payments-prod`, `rg-data-prod`

```
*payments*
```
Matches: `rg-payments-prod`, `rg-payments-staging`, `rg-payments-dev`

**Mixed:**
```
rg-orders-prod, rg-payments-*, *-data-*
```

The skill resolves all patterns, shows the matched list, and asks for confirmation before scanning.

## Output

- **In conversation:** Summary table of findings ranked by estimated savings (always shown)
- **CSV** (default): `finops_report_YYYY-MM-DD_{subscription_name}.csv` — one row per finding, importable into Excel or any analysis tool
- **Markdown** (optional): `finops_report_YYYY-MM-DD_{subscription_name}.md` — human-readable report with full detail per finding
- **Both:** produces both files in the same run

## Scope

This skill is designed for **team-scoped analysis** — scanning specific resource groups, not entire subscriptions. Resource groups are required input, with a maximum of 30 per scan.

## Token Cost Awareness

Running this skill consumes Claude API tokens — if you're using your own API key or a metered plan, be aware of the following estimates before scanning large environments.

**Fixed cost per run (regardless of what's found):**
- Skill instructions loaded into context: ~1,100 tokens
- Auto-detection Resource Graph query: ~100–300 tokens
- **Base overhead: ~1,200–1,400 tokens per scan**

**Variable cost (depends on resources found):**

| Resource type | Approx. tokens per resource |
|---|---|
| ARG-only finders (disks, IPs, snapshots, stopped VMs, legacy series) | ~80 tokens |
| ARG + Monitor finders (VMs, Redis, SQL DBs, LAWS, App Service Plans) | ~120–150 tokens |

**Estimated total by environment size:**

| Environment | Resources | Est. tokens |
|---|---|---|
| Small | 5 VMs, 3 disks, 2 Redis | ~2,500–3,500 |
| Medium | 10 VMs, 5 disks, 3 Redis, 3 SQL DBs | ~4,500–6,000 |
| Large | 30 VMs, 15 disks, 10 Redis, 5 LAWS, 5 SQL DBs | ~12,000–18,000 |

**Tips to keep costs down:**
- Scan specific RGs rather than broad wildcard patterns — fewer resources = fewer Monitor calls
- Run ARG-only finders first if you want a quick look at unambiguous waste (unattached disks, stopped VMs, orphaned IPs) before committing to a full scan
- The 30 RG maximum is a hard cap for a reason — scanning at scale compounds token cost quickly

## Finder Reference

Key thresholds, formulas, and notes per finder.

### storage_compute_inversion
- **Threshold:** Storage cost ≥ $5,000 (3-month total) AND ratio ≥ 13.5x compute cost
- **Savings formula:** `(storage_cost / 3) * 0.35` — assumes 35% reduction via data lifecycle review
- **Meter categories counted as storage:** "Storage"
- **Meter categories counted as compute:** "Virtual Machines", "SQL Managed", "Compute", "Kubernetes"

### staging_continuous
- **RG name keywords:** `staging`, `stg`, `dev`, `test`, `sandbox`, `sbox`, `qa`, `uat`, `nonprod`, `non-prod`, `nprd`
- **Threshold:** Non-zero cost every month for 3 consecutive months AND total 90-day cost > $500
- **Action:** Auto-shutdown schedules, Azure DevTest Labs, or teardown when idle

### redis_idle
- **Metric:** `TotalCommandsProcessed` (captures all traffic — reads, writes, pub/sub, admin)
- **Threshold:** Sum over 30 days == 0 (zero application traffic)

### laws_workspace_sprawl
- **Consolidation threshold:** Combined peak ingestion < 85 GB/day across a logical workspace group
- **PAYG rate:** $2.30/GB (used for cost estimates)
- **Savings formula:** `total_monthly_cost / 2` — assumes consolidating per-env workspaces into one
- **Grouping:** Workspaces grouped by shared RG naming stem where identifiable

### vm_idle
- **CPU thresholds:** 30-day avg < 5% AND 7-day max < 55%
- **Only processes running VMs** (`PowerState/running`)
- **Savings formula:** `monthly_cost * (1 - target_vcpus / current_vcpus)`
- **Memory headroom before recommending downsize:**
  - Prod RGs (name contains `prod`, `-pa-`, `-pb-`): `max(4 GB, 20% of target RAM)`
  - Non-prod: `max(2 GB, 10% of target RAM)`
- **SKU downsize map** (one step down within same family):

| Current SKU | Target SKU |
|---|---|
| Standard_D96ds_v5 | Standard_D48ds_v5 |
| Standard_D48ds_v5 | Standard_D32ds_v5 |
| Standard_D32ds_v5 | Standard_D16ds_v5 |
| Standard_D16ds_v5 | Standard_D8ds_v5 |
| Standard_D8ds_v5 | Standard_D4ds_v5 |
| Standard_D96s_v5 | Standard_D48s_v5 |
| Standard_D48s_v5 | Standard_D32s_v5 |
| Standard_D32s_v5 | Standard_D16s_v5 |
| Standard_D16s_v5 | Standard_D8s_v5 |
| Standard_D8s_v5 | Standard_D4s_v5 |
| Standard_E96s_v5 | Standard_E48s_v5 |
| Standard_E48s_v5 | Standard_E32s_v5 |
| Standard_E32s_v5 | Standard_E16s_v5 |
| Standard_E16s_v5 | Standard_E8s_v5 |
| Standard_E8s_v5 | Standard_E4s_v5 |

### vm_legacy_series
- **v4 and above are acceptable** — only v2, v3, and older are flagged
- **Legacy patterns → recommended upgrade:**
  - `Standard_D*_v2` / `Standard_D*_v3` → Dv5
  - `Standard_E*_v2` / `Standard_E*_v3` → Ev5
  - `Standard_F*s` (v1) / `Standard_F*_v1` → Fv2
  - `Standard_A*` → Dv5 or Bv2
  - `Standard_B*s` (v1) → Bv2

### idle_app_service_plans
- **Skip:** Free and Shared tier plans (no cost)
- **Empty plans** (`numberOfSites == 0`): always flagged, no metrics needed
- **Non-empty plans:** flagged if 30-day avg CPU < 5%

### snapshot_accumulation
- **Threshold:** Snapshot age > 90 days from `timeCreated`

### idle_sql_databases
- **Thresholds:** 30-day avg CPU < 10% AND 30-day max CPU < 60%
- **Excludes:** `master` database
- **Actions:** Downsize service tier, move to elastic pool, or enable serverless auto-pause

## Credits

- Detection logic derived from internal FinOps investigation scripts
- Thresholds and enrichment patterns based on operational experience with Azure cost optimization
