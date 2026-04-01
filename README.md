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

The skill prompts for two inputs:

1. **Subscription** — name or ID
2. **Resource groups** — one or more (required, max 30)

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

- **In conversation:** Summary table of findings ranked by estimated savings
- **Report file:** `finops_report_YYYY-MM-DD_{subscription_name}.md` written to the working directory with full detail per finding

## Scope

This skill is designed for **team-scoped analysis** — scanning specific resource groups, not entire subscriptions. Resource groups are required input, with a maximum of 30 per scan.

## Credits

- Detection logic derived from internal FinOps investigation scripts
- Thresholds and enrichment patterns based on operational experience with Azure cost optimization
