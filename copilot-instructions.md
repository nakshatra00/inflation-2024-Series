# INDIA CPI 2024 ANALYTICS SPECIFICATION
## Configuration-Driven Index & Inflation Computation Blueprint

**Version:** 1.0  
**Date:** February 2026  
**Scope:** All-India, Rural, Urban geographies | Item-level granularity  
**Base Month:** Jan 2024 = 100 (assumed)

---

## 0. DATA SCHEMA REQUIREMENTS
### What You Must Provide

Before any computation, your three input datasets must conform to this schema:

#### 0.1 WEIGHTS REFERENCE TABLE
**File:** `cpi_weights_2024.csv`  
**Granularity:** Item-level (most atomic unit)  
**Structure:**

| item_id | item_name | coicop_code | coicop_division | coicop_group | coicop_class | weight_combined | weight_rural | weight_urban | tags | priority | availability_flag |
|---------|-----------|-------------|-----------------|--------------|--------------|-----------------|--------------|--------------|------|----------|-------------------|
| `I001` | Rice (medium) | 01.11.11 | Food & Non-Alc Bev | Food | Cereals | 4.23 | 5.10 | 3.51 | food; staple | 1 | 1 |
| `I002` | Wheat flour | 01.11.12 | Food & Non-Alc Bev | Food | Cereals | 2.18 | 2.65 | 1.83 | food; staple | 1 | 1 |
| `I_GOLD` | Gold (22 carat) | 09.51.11 | Recreation & Culture | Personal care | Jewellery | 2.50 | 0.85 | 3.85 | precious_metals; gold | 2 | 1 |

**Column Definitions:**
- `item_id`: Unique identifier (alphanumeric, e.g., `I001`, `I_GOLD`, `I_FUEL_PETROL`)
- `item_name`: Human-readable description
- `coicop_code`: 8-digit code (DD.DD.DD) per COICOP 2018 or RBI equivalent
- `coicop_division`, `coicop_group`, `coicop_class`: Hierarchical levels (text or numeric)
- `weight_combined`, `weight_rural`, `weight_urban`: Absolute weight shares (values between 0–100, NOT normalized, sum across all items in a geography = 100)
- `tags`: Semicolon-delimited tags for filtering (e.g., `food; fuel; volatile; administered; precious_metals; gold; silver`)
- `priority`: Integer (1=critical publication item, 2=standard, 3=low-priority)
- `availability_flag`: 1 = item included in 2024 base; 0 = not included/deprecated

**Validation Rules:**
- Every item_id must be unique
- Every item must map to exactly one COICOP code
- `weight_combined` ≈ `weight_rural` + `weight_urban` is NOT required; geographies are independent
- Σ `weight_combined` = 100.0 (or 1.0; normalization is in formulas)
- Σ `weight_rural` = 100.0
- Σ `weight_urban` = 100.0

#### 0.2 INDEX TIME SERIES TABLE
**File:** `cpi_indices_monthly_2024.csv`  
**Granularity:** Item-level, monthly  
**Structure:**

| item_id | year_month | index_combined | index_rural | index_urban | is_provisional | data_source | notes |
|---------|-----------|-----------------|-------------|-------------|----------------|-------------|-------|
| I001 | 2024-01 | 100.00 | 100.00 | 100.00 | 0 | RBI | Base month |
| I001 | 2024-02 | 102.35 | 102.10 | 102.45 | 0 | RBI | |
| I001 | 2024-03 | 102.45 | 102.25 | 102.60 | 0 | RBI | |
| I_GOLD | 2024-01 | 100.00 | 100.00 | 100.00 | 0 | RBI | Base month |
| I_GOLD | 2024-02 | 98.50 | 98.50 | 98.50 | 1 | RBI | Provisional |

**Column Definitions:**
- `item_id`: Foreign key to weights table
- `year_month`: ISO format (YYYY-MM)
- `index_combined`, `index_rural`, `index_urban`: Index level (base=100 at base month). Can be NULL if data unavailable.
- `is_provisional`: 0/1 flag (affects QA reporting)
- `data_source`: Source identifier
- `notes`: Optional text

**Validation Rules:**
- Every (item_id, year_month) combination should appear at most once
- Index values must be positive (> 0)
- Base month (2024-01) index = 100.00 for all items
- NULL values allowed; handled by missing-data policies (Section 4)

#### 0.3 HIERARCHY METADATA TABLE
**File:** `cpi_hierarchy_2024.csv`  
**Purpose:** Support rollup computation from items to groups/divisions  
**Structure:**

| hierarchy_level | code | name | parent_code | parent_name | item_count |
|-----------------|------|------|------------|-------------|-----------|
| Division | 01 | Food & Non-Alcoholic Beverages | NULL | CPI Headline | 45 |
| Division | 02 | Alcoholic Beverages & Tobacco | NULL | CPI Headline | 12 |
| Group | 01.01 | Food | 01 | Food & Non-Alc Bev | 40 |
| Group | 01.02 | Non-Alc Beverages | 01 | Food & Non-Alc Bev | 5 |
| Class | 01.01.01 | Cereals & Cereal Prep. | 01.01 | Food | 10 |

**Validation Rules:**
- Hierarchy must form a valid tree (no cycles)
- COICOP codes must match weights table
- Every item's COICOP must appear in this table

---

## 1. NOTATION & DEFINITIONS

### 1.1 Core Sets & Indices

**Universe of items:**
$$U = \{i : i \text{ has item\_id in weights table}\}$$
Cardinality: typically $|U| = 300$–$500$ for India CPI.

**Month index:**
$$t \in \mathbb{T} = \{\text{2024-01, 2024-02, ..., 2024-12, 2025-01, ...}\}$$

**Geography:**
$$g \in \{\_combined, \_rural, \_urban\}$$
Computations are independent per geography; no cross-geography weight constraints.

**Item weight (absolute share):**
$$w_{i,g} \in [0, 100]$$
Read from weights table for item $i$ and geography $g$.
Σ_{i ∈ U} w_{i,g} = 100 \text{ (for each } g \text{)}

**Item index level (base = 100):**
$$I_{i,g,t} \in (0, +∞)$$
Read from indices time series; NULL/missing allowed.

**Item inflation (year-on-year, %):**
$$\pi^{YoY}_{i,g,t} = \left(\frac{I_{i,g,t}}{I_{i,g,t-12}} - 1\right) \times 100$$

**Item inflation (month-on-month, %):**
$$\pi^{MoM}_{i,g,t} = \left(\frac{I_{i,g,t}}{I_{i,g,t-1}} - 1\right) \times 100$$

### 1.2 Definition-Based Subsets

**Inclusion universe for definition d:**
$$S(d, g) \subseteq U$$
Determined by **config rules** in Section 2 (exclusions/inclusions/tag filters).

**Availability set (non-missing data) for definition d at month t:**
$$A(d,g,t) = \{i \in S(d,g) : I_{i,g,t} \neq \text{NULL}\}$$

**Total available weight in definition d:**
$$W_A(d,g,t) = \sum_{i \in A(d,g,t)} w_{i,g}$$

**Total selected weight (ignoring missing):**
$$W_S(d,g) = \sum_{i \in S(d,g)} w_{i,g}$$

**Coverage metric (fraction of weight available at month t):**
$$\text{cov}(d,g,t) = \frac{W_A(d,g,t)}{W_S(d,g)}$$
Range: $[0, 1]$. Must be ≥ 0.95 for publication-quality indices.

### 1.3 Renormalized Weights

When items are missing, renormalization ensures selected items sum to their total weight.

$$\hat{w}_{i,g,t}(d) = \begin{cases}
\frac{w_{i,g}}{W_A(d,g,t)} & \text{if } i \in A(d,g,t) \\
0 & \text{otherwise}
\end{cases}$$

These sum to 1:
$$\sum_{i \in A(d,g,t)} \hat{w}_{i,g,t}(d) = 1$$

If you want weights to sum to 100:
$$\hat{w}^{(100)}_{i,g,t}(d) = 100 \times \hat{w}_{i,g,t}(d)$$

---

## 2. CORE/EXCLUSION DEFINITION SPEC

### 2.1 Configuration Schema (JSON Format)

```json
{
  "definition_id": "core_ex_fuel",
  "name": "Core ex Fuel",
  "description": "CPI excluding fuel & light division",
  "geography_scope": ["combined", "rural", "urban"],
  "apply_missing_data_policy": "DROP_AND_RENORMALIZE",
  
  "include_rules": {
    "mode": "EXCLUDE_FROM_UNIVERSE",
    "include_item_ids": null,
    "include_tags": null,
    "include_coicop_divisions": null
  },
  
  "exclude_rules": {
    "mode": "EXPLICIT_EXCLUSION",
    "exclude_item_ids": ["I_FUEL_PETROL", "I_FUEL_DIESEL", "I_FUEL_LPGAS"],
    "exclude_tags": ["fuel"],
    "exclude_coicop_divisions": [
      {"code": "04", "name": "Fuel and Light"}
    ],
    "exclude_coicop_groups": null,
    "exclude_coicop_classes": null
  },
  
  "metadata": {
    "category": "CORE",
    "published": true,
    "min_coverage_threshold": 0.95,
    "notes": "Excludes all fuel & light items; used to assess core inflation net of energy shocks"
  }
}
```

### 2.2 Definition Logic (Set Algebra)

**Step 1: Build Universe**
```
If include_rules.mode == INCLUDE_ONLY:
    S(d,g) := items matching include_item_ids OR include_tags OR include_coicop_divisions
Else (EXCLUDE_FROM_UNIVERSE):
    S(d,g) := U
```

**Step 2: Apply Exclusions**
```
S(d,g) := S(d,g) \ {i : 
    i.item_id in exclude_item_ids 
    OR any(tag in i.tags for tag in exclude_tags)
    OR i.coicop_division in exclude_coicop_divisions
    OR i.coicop_group in exclude_coicop_groups
    OR i.coicop_class in exclude_coicop_classes
}
```

**Step 3: Geography Filter**
```
Apply only to geographies listed in geography_scope
(compute separately for each)
```

### 2.3 Six Standard Definitions

#### Definition 1: HEADLINE (No exclusions)
```json
{
  "definition_id": "headline",
  "name": "Headline CPI",
  "exclude_rules": {
    "exclude_item_ids": [],
    "exclude_tags": [],
    "exclude_coicop_divisions": []
  }
}
```
$$S(\text{headline}, g) = U$$

#### Definition 2: CORE EX FOOD+FUEL
```json
{
  "definition_id": "core_ex_food_fuel",
  "name": "Core (ex Food & Fuel)",
  "exclude_rules": {
    "exclude_coicop_divisions": [
      {"code": "01", "name": "Food & Non-Alcoholic Beverages"},
      {"code": "04", "name": "Fuel and Light"}
    ]
  }
}
```
$$S(\text{core\_food\_fuel}, g) = U \setminus \{i : \text{coicop\_division} \in \{\text{01, 04}\}\}$$
Typical weight: ~60% of headline.

#### Definition 3: CORE EX FUEL
```json
{
  "definition_id": "core_ex_fuel",
  "name": "Core (ex Fuel)",
  "exclude_rules": {
    "exclude_coicop_divisions": [
      {"code": "04", "name": "Fuel and Light"}
    ]
  }
}
```
$$S(\text{core\_fuel}, g) = U \setminus \{i : \text{coicop\_division} = \text{04}\}$$
Typical weight: ~93% of headline.

#### Definition 4: CORE EX PRECIOUS METALS
```json
{
  "definition_id": "core_ex_precious_metals",
  "name": "Core (ex Precious Metals)",
  "exclude_rules": {
    "exclude_tags": ["precious_metals"]
  }
}
```
$$S(\text{core\_pm}, g) = U \setminus \{i : \text{"precious\_metals"} \in i.\text{tags}\}$$
Typical weight: ~98% of headline (gold + silver ≈ 2%).

#### Definition 5: CORE EX SILVER
```json
{
  "definition_id": "core_ex_silver",
  "name": "Core (ex Silver)",
  "exclude_rules": {
    "exclude_tags": ["silver"]
  }
}
```
$$S(\text{core\_silver}, g) = U \setminus \{i : \text{"silver"} \in i.\text{tags}\}$$
Typical weight: ~99% of headline (silver ≈ 0.4%).

#### Definition 6: CORE EX GOLD+SILVER
```json
{
  "definition_id": "core_ex_gold_silver",
  "name": "Core (ex Gold & Silver)",
  "exclude_rules": {
    "exclude_tags": ["gold", "silver"]
  }
}
```
$$S(\text{core\_gs}, g) = U \setminus \{i : \text{"gold"} \in i.\text{tags} \vee \text{"silver"} \in i.\text{tags}\}$$
Equivalent to Definition 4 in most cases.

---

## 3. REQUIRED FORMULAS

### 3.1 Universe Selection (Set Logic)

**Algorithm to compute S(d,g):**

```
Input: definition d, geography g
Output: set S(d,g)

1. Start with candidate set C := U
2. If d.include_rules.mode == INCLUDE_ONLY:
     C := {i ∈ U : i matches ANY include_item_ids OR include_tags OR include_coicop_*}
3. For each item i in C:
     removed := FALSE
     For each rule in d.exclude_rules.*:
       if i matches rule:
         removed := TRUE
         break
     if removed:
       C := C \ {i}
4. Return S(d,g) := C
```

**Postcondition:** Record $W_S(d,g) = \sum_{i \in S(d,g)} w_{i,g}$ for audit.

### 3.2 Weight Normalization (Core of Computation)

**Given:**
- Definition d, geography g, month t
- Set S(d,g) from Section 3.1
- Time series I_{i,g,t} (may be NULL for some items)
- Missing-data policy (Section 4)

**Step 1: Compute Availability Set**
$$A(d,g,t) = \{i \in S(d,g) : I_{i,g,t} \neq \text{NULL}\}$$

**Step 2: Compute Available Weight**
$$W_A(d,g,t) = \sum_{i \in A(d,g,t)} w_{i,g}$$

**Step 3: Compute Coverage Metric**
$$\text{cov}(d,g,t) = \frac{W_A(d,g,t)}{W_S(d,g)}$$

**Step 4: Check Minimum Coverage (QA)**
```
if cov(d,g,t) < 0.95:
    FLAG for review (do not suppress publication, but annotate)
if W_A(d,g,t) == 0:
    ERROR: Cannot compute index; all items missing
```

**Step 5: Renormalize Weights**
$$\hat{w}_{i,g,t}(d) = \begin{cases}
\frac{w_{i,g}}{W_A(d,g,t)} & \text{if } i \in A(d,g,t) \\
0 & \text{otherwise}
\end{cases}$$

Verify: $\sum_{i \in A(d,g,t)} \hat{w}_{i,g,t}(d) = 1$ (within numerical tolerance $\epsilon = 10^{-8}$).

### 3.3 Index Aggregation Formula (Weighted Mean)

**Primary Method: Weighted Arithmetic Mean of Item Indices**

$$I_{d,g,t} = \sum_{i \in A(d,g,t)} \hat{w}_{i,g,t}(d) \cdot I_{i,g,t}$$

**Equivalent form (using non-renormalized weights):**
$$I_{d,g,t} = \frac{\sum_{i \in A(d,g,t)} w_{i,g} \cdot I_{i,g,t}}{W_A(d,g,t)}$$

**Numerator:** Weighted sum of indices  
**Denominator:** Total available weight

**Examples (toy basket, 5 items):**

| i | w_i | I_{i,t=0} | I_{i,t=1} | Available |
|---|-----|-----------|-----------|-----------|
| 1 | 20 | 100 | 102 | ✓ |
| 2 | 30 | 100 | 101 | ✓ |
| 3 | 25 | 100 | 103 | ✗ NULL |
| 4 | 15 | 100 | 100 | ✓ |
| 5 | 10 | 100 | 99 | ✓ |
| | 100 | | | |

At $t=1$:
- $S = \{1, 2, 3, 4, 5\}$
- $A = \{1, 2, 4, 5\}$ (item 3 is NULL)
- $W_A = 20 + 30 + 15 + 10 = 75$
- $\text{cov} = 75 / 100 = 0.75$ (below threshold; flag for review)

Renormalized weights:
- $\hat{w}_1 = 20/75 = 0.2667$
- $\hat{w}_2 = 30/75 = 0.4000$
- $\hat{w}_4 = 15/75 = 0.2000$
- $\hat{w}_5 = 10/75 = 0.1333$

Index:
$$I_{d,g,t=1} = 0.2667 \times 102 + 0.4000 \times 101 + 0.2000 \times 100 + 0.1333 \times 99$$
$$= 27.2034 + 40.4000 + 20.0000 + 13.1967 = 100.8001$$

**Error Conditions:**
- If $W_A = 0$: **FATAL ERROR**. Abort computation and report missing-data crisis.
- If $\text{cov} < 0.95$: **CAUTION FLAG**. Compute but annotate with low-coverage warning.
- If $\text{cov} < 0.85$: **WEAK SIGNAL FLAG**. Compute but mark as provisional.

### 3.4 Hierarchical Aggregation (Group/Division Level)

**If you compute rollups:**

Let $\text{Child}(k)$ = set of child nodes (items or subnodes) under parent node $k$ in the hierarchy.

**Parent index at month t (using same formula recursively):**
$$I_{k,g,t} = \frac{\sum_{j \in \text{Child}(k)} w_{j,g} \cdot I_{j,g,t}}{\sum_{j \in \text{Child}(k)} w_{j,g}}$$

Apply the same missing-data handling: if a child is NULL, exclude it and renormalize.

**Example: Cereals Group (within Food Division)**

| Item | Weight | Index (t=1) | Available |
|------|--------|-------------|-----------|
| Rice | 4.23 | 102.5 | ✓ |
| Wheat | 2.18 | 101.0 | ✓ |
| Coarse cereals | 1.25 | NULL | ✗ |
| Maida/Flour | 1.89 | 103.0 | ✓ |

$$W_{\text{cereals}} = 4.23 + 2.18 + 1.89 = 8.30 \text{ (excluding unavailable coarse cereals)}$$

$$I_{\text{cereals},g,t=1} = \frac{4.23 \times 102.5 + 2.18 \times 101.0 + 1.89 \times 103.0}{8.30}$$
$$= \frac{434.075 + 220.18 + 194.67}{8.30} = \frac{848.925}{8.30} = 102.28$$

### 3.5 Inflation Rate Formulas

**Month-on-Month (MoM) Inflation:**
$$\pi^{MoM}_{d,g,t} = \left(\frac{I_{d,g,t}}{I_{d,g,t-1}} - 1\right) \times 100 \quad \text{(%)}$$

**Year-on-Year (YoY) Inflation:**
$$\pi^{YoY}_{d,g,t} = \left(\frac{I_{d,g,t}}{I_{d,g,t-12}} - 1\right) \times 100 \quad \text{(%)}$$

**Example Continuation (toy basket):**
- $I_{d,g,t=0} = 100.00$
- $I_{d,g,t=1} = 100.80$

$$\pi^{MoM}_{d,g,t=1} = \left(\frac{100.80}{100.00} - 1\right) \times 100 = 0.80\%$$

**Special Case: If Linking / Splicing**
(See Section 7; apply inflation formulas to linked series consistently.)

### 3.6 Contribution Decomposition (Additive in pp)

**Goal:** Break down inflation into item-level or group-level contributions such that:
$$\pi^{YoY}_{d,g,t} = \sum_{i \in A(d,g,t)} C^{YoY(pp)}_{i \to d,g,t}$$

where each contribution $C$ is in **percentage points (pp)**.

#### **Method 1: Index-Difference Decomposition (Recommended)**

**Step 1: Compute Index Change (absolute points)**

For YoY baseline (month $t-12$):
$$\Delta I^{YoY}_{d,g,t} = I_{d,g,t} - I_{d,g,t-12}$$

**Step 2: Decompose to Item-Level Index Change**

Because $I_{d,g,t} = \sum_{i \in A} \hat{w}_{i,g,t} \cdot I_{i,g,t}$ and renormalization applies at $t$, attribute the index change:

$$\Delta I^{YoY}_{i \to d,g,t} = \hat{w}_{i,g,t}(d) \cdot (I_{i,g,t} - I_{i,g,t-12})$$

where $\hat{w}_{i,g,t}(d)$ is the **current-month (t) renormalized weight**.

**Verify additivity:**
$$\sum_{i \in A(d,g,t)} \Delta I^{YoY}_{i \to d,g,t} = I_{d,g,t} - \text{(weighted avg of }I_{i,t-12}\text{)} \approx \Delta I^{YoY}_{d,g,t}$$

(This is exact if $A(d,g,t) = A(d,g,t-12)$; if sets differ, small residuals arise; report them.)

**Step 3: Convert Index Change to pp of Inflation**

$$C^{YoY(pp)}_{i \to d,g,t} = \frac{\Delta I^{YoY}_{i \to d,g,t}}{I_{d,g,t-12}} \times 100$$

This scales the index change by the base-period denominator, converting to pp.

**Verification (must hold exactly within numerical tolerance $\epsilon = 0.01$ pp):**
$$\left| \pi^{YoY}_{d,g,t} - \sum_{i \in A(d,g,t)} C^{YoY(pp)}_{i \to d,g,t} \right| < \epsilon$$

#### **Method 1 Worked Example (toy basket, YoY):**

**Setup:**
- $t = 0$ (base): $I_{d,g,0} = 100.00$
- $t = 1$ (current): $I_{d,g,1} = 100.80$ (computed in Section 3.3)
- $t = 1-12 = -11$: Assume $I_{d,g,-11} = 99.50$ (historical)

**YoY Inflation:**
$$\pi^{YoY}_{d,g,1} = \frac{100.80 - 99.50}{99.50} \times 100 = 1.307\%$$

**Item Contributions:**

| Item | w_i | $\hat{w}_{i,1}$ | $I_{i,1}$ | $I_{i,-11}$ | $\Delta I_i$ | Contribution (pp) |
|------|-----|--------|---------|---------|---------|-----------------|
| 1 | 20 | 0.2667 | 102 | 100.5 | 1.5 | 0.2667 × 1.5 / 99.50 × 100 = 0.402 |
| 2 | 30 | 0.4000 | 101 | 99.0 | 2.0 | 0.4000 × 2.0 / 99.50 × 100 = 0.803 |
| 4 | 15 | 0.2000 | 100 | 100.5 | -0.5 | 0.2000 × (-0.5) / 99.50 × 100 = -0.101 |
| 5 | 10 | 0.1333 | 99 | 98.0 | 1.0 | 0.1333 × 1.0 / 99.50 × 100 = 0.134 |

**Sum of Contributions:**
$$0.402 + 0.803 - 0.101 + 0.134 = 1.238 \text{ pp}$$

(Residual: $1.307 - 1.238 = 0.069$ pp, due to item 3 unavailability affecting renormalization; acceptable.)

#### **Step 4: Group-Level Contributions**

Aggregate item contributions within each COICOP group/division:

$$C^{YoY(pp)}_{G \to d,g,t} = \sum_{i \in G \cap A(d,g,t)} C^{YoY(pp)}_{i \to d,g,t}$$

This gives contribution of each group to overall inflation.

#### **Method 2 (Alternative): Laspeyres Implicit Weights**

If you prefer a "base-period weight" approach:

$$C^{YoY(pp)}_{i \to d,g,t}|_{\text{Laspeyres}} = w_{i,g} \times \left(\frac{\pi^{YoY}_{i,g,t}}{100}\right)$$

where $w_{i,g}$ is the **original (unadjusted) weight**.

**Pro:** Uses official weight hierarchy consistently.  
**Con:** Does not sum exactly to total inflation when items are missing; residual = contribution of missing items.

**Residual:**
$$\text{Residual} = (100 - W_A) \times \text{(avg inflation of missing items)}$$

**Recommendation:** Use Method 1 by default; report Method 2 as sensitivity.

### 3.7 "Wedge" Between Headline and Core & Attribution

**Definitions:**
- **Headline:** Definition `headline` from Section 2.3
- **Core:** Definition `core_ex_food_fuel` (or any other core measure)

#### **Wedge (YoY):**
$$\text{wedge}^{YoY}_{g,t} = \pi^{YoY}_{\text{headline},g,t} - \pi^{YoY}_{\text{core},g,t}$$

Interpretation: percentage points of YoY inflation attributable to the difference between headline and core.

#### **Attribution Approach A (Consistent Weighting) — RECOMMENDED**

Compute contributions within each index using its own weights:

**Headline contributions:**
$$\pi^{YoY}_{\text{headline},g,t} = \sum_{i=1}^{|U|} C^{YoY(pp)}_{i \to \text{headline},g,t}$$

**Core contributions (excludes certain items):**
$$\pi^{YoY}_{\text{core},g,t} = \sum_{i \in S(\text{core},g)} C^{YoY(pp)}_{i \to \text{core},g,t}$$

**Group G wedge contribution:**
$$\text{wedgeContr}^{YoY}(G) = \sum_{i \in G} C^{YoY(pp)}_{i \to \text{headline},g,t} - \sum_{i \in G \cap S(\text{core},g)} C^{YoY(pp)}_{i \to \text{core},g,t}$$

**Verification (if same items available in both):**
$$\sum_{G} \text{wedgeContr}^{YoY}(G) = \text{wedge}^{YoY}_{g,t}$$

If coverage differs, report residual.

#### **Attribution Approach B (Simpler, Approximate)**

Let $E = S(\text{headline}, g) \setminus S(\text{core}, g)$ = items excluded from core.

**Excluded-basket contribution (using headline weights):**
$$\text{exclContr}^{YoY(pp)}_{g,t} = \sum_{i \in E} C^{YoY(pp)}_{i \to \text{headline},g,t}$$

**Insight:**
$$\text{exclContr}^{YoY(pp)} \approx \text{wedge}^{YoY}_{g,t}$$

**Caveat:** Not exact because core renormalizes remaining items' weights. If all items available, residual ≈ 0.01–0.05 pp.

#### **Worked Example: Wedge**

**Setup:**
- Headline YoY: 5.50%
- Core (ex F+F) YoY: 4.20%
- Wedge: 1.30 pp

**Excluded groups (Food + Fuel):**

| Group | Headline Contrib (pp) | Residual Inflation (%) | Wedge Contrib (pp) |
|-------|----------------------|----------------------|------------------|
| Food | 2.50 | 12.0% | 2.50 |
| Fuel & Light | 0.75 | 8.5% | 0.75 |
| **Total Excluded** | **3.25** | - | **3.25** |

**Wedge Reconciliation:**
- Headline: 5.50%
- Core (ex F+F): 4.20%
- Excluded-basket widening: +3.25 pp
- Expected wedge: 3.25 pp

**Actual wedge: 1.30 pp**  
**Residual (due to renormalization): 3.25 - 1.30 = 1.95 pp**

This residual arises because core renormalizes weights of the 60 remaining items upward, which affects their contribution. Document this in output.

---

## 4. MISSING DATA POLICY (Formula Level)

### 4.1 Policy 1: DROP AND RENORMALIZE (Default, Recommended)

**When to use:** Item data is unavailable (temporary processing delay, collection failure, item discontinued).

**Formula:**

For definition d, geography g, month t:

1. Identify available items: $A(d,g,t) = \{i \in S(d,g) : I_{i,g,t} \neq \text{NULL}\}$
2. Compute denominator: $W_A(d,g,t) = \sum_{i \in A} w_{i,g}$
3. Check coverage: $\text{cov} = W_A / W_S(d,g)$
4. If $\text{cov} \geq 0.95$: Proceed (renormalize weights as in Section 3.2)
5. If $0.85 \leq \text{cov} < 0.95$: Proceed with CAUTION flag
6. If $\text{cov} < 0.85$: FLAG as WEAK SIGNAL
7. If $W_A = 0$: ERROR, abort

**Renormalized weights:**
$$\hat{w}_{i,g,t}(d) = \frac{w_{i,g}}{W_A(d,g,t)} \quad \text{for } i \in A(d,g,t)$$

**Index computation:**
$$I_{d,g,t} = \sum_{i \in A(d,g,t)} \hat{w}_{i,g,t}(d) \cdot I_{i,g,t}$$

**Pros:**
- Unbiased if missing is random
- Transparent; coverage metric is published
- Avoids extrapolation bias

**Cons:**
- Index is not directly comparable to prior month if composition shifts (resolved by contribution analysis)

### 4.2 Policy 2: CARRY FORWARD (Optional)

**When to use:** Single-month gap in a stable series (e.g., delayed data release, assumed flat month).

**Formula:**

Define a filled index:
$$I^{\text{filled}}_{i,g,t} = \begin{cases}
I_{i,g,t} & \text{if } I_{i,g,t} \neq \text{NULL} \\
I_{i,g,t-1} & \text{if } I_{i,g,t} = \text{NULL}
\end{cases}$$

Then compute as usual:
$$I_{d,g,t} = \frac{\sum_i w_{i,g} \cdot I^{\text{filled}}_{i,g,t}}{\sum_i w_{i,g}} \quad \text{(using original weights if all items carry forward)}$$

**Report fill-rate:**
$$\text{fillRate}(d,g,t) = \frac{|\{i : I_{i,g,t} = \text{NULL}\}|}{|S(d,g)|}$$

**Pros:**
- Continuous series; no renormalization artifacts

**Cons:**
- Biased if missing items have different inflation trajectory
- Can hide data quality issues
- Violates principle of publishing available data only

**Recommendation:** Use only for MoM calculations over 1-month gaps; avoid for YoY.

### 4.3 Policy 3: IMPUTE PARENT (Hierarchy-Based)

**When to use:** Item unavailable; parent (group) index available (e.g., item discontinued; category index still published).

**Requirement:** Hierarchy table (Section 0.3) must be complete.

**Formula:**

If $i$ missing at month $t$, impute from parent:
$$I^{\text{imputed}}_{i,g,t} = I_{\text{parent}(i),g,t}$$

If parent also missing, impute from grandparent, etc., until available ancestor found (or error).

**Imputed index:**
$$I_{d,g,t} = \frac{\sum_{i \in A \cup I^*} w_{i,g} \cdot I_{i,g,t}^{\text{imputed}}}{W_A + W_{I^*}}$$

where $I^*$ = items imputed.

**Report imputation-rate:**
$$\text{imputeRate}(d,g,t) = \frac{W_{I^*}}{W_S(d,g)}$$

**Bias Risk:**

If the imputed item's inflation differs significantly from its parent:
$$\text{Bias} \approx w_i \times (\pi_i - \pi_{\text{parent}})$$

Keep imputation rate $< 5\%$ to limit bias.

**Recommendation:** Use as fallback only; prefer DROP_AND_RENORMALIZE where possible.

---

## 5. QA CHECKS (Formula-Based Checklist)

### 5.1 Input Data Validation

**Check 1.1: Weight Sum (by Geography)**
```
For each geography g:
  W_sum = Σ_{i ∈ U} w_{i,g}
  Assert |W_sum - 100.0| < 0.01  (allow ±0.01 rounding)
  If fail: ERROR, list items with missing weights
```

**Check 1.2: Unique Item Mapping**
```
For each item_id in weights table:
  count := number of rows with this item_id
  Assert count == 1
  If fail: ERROR, remove duplicates
```

**Check 1.3: COICOP Hierarchy Integrity**
```
For each item i in weights:
  coicop_code := i.coicop_code
  Assert: exists exactly one row in hierarchy_metadata with this code
  If fail: ERROR, reconcile missing codes
```

**Check 1.4: Index Base Month**
```
For each item i:
  I_{i,g,"2024-01"} (base month index)
  Assert I_{i,g,"2024-01"} == 100.0 (or 100.0 ± 0.5 if rounding)
  If fail: WARN, may indicate rebasing event
```

### 5.2 Definition-Level Checks

**Check 2.1: Weight Selection (per definition)**
```
For each definition d and geography g:
  W_S(d,g) = Σ_{i ∈ S(d,g)} w_{i,g}
  Assert 0 < W_S(d,g) ≤ 100.0
  Record W_S for documentation
  If W_S == 0: ERROR, definition selects nothing
```

**Check 2.2: Exclusion Overlap**
```
For definitions D = {d1, d2, ...}:
  For each pair (d1, d2):
    overlap := S(d1,g) ∩ S(d2,g)
    If overlap is unexpected (e.g., core ex F+F and core ex F):
      Alert user to confirm intentionality
```

### 5.3 Time-Series Quality Checks (each month)

**Check 3.1: Coverage per Definition**
```
For each definition d, geography g, month t:
  cov(d,g,t) = W_A(d,g,t) / W_S(d,g)
  If cov < 0.95: FLAG (CAUTION)
  If cov < 0.85: FLAG (WEAK SIGNAL); consider not publishing
  If cov < 0.70: ERROR, critical data gap
  Record cov in audit log
```

**Check 3.2: Index Bounds**
```
For each item i, geography g, month t:
  Assert 50 < I_{i,g,t} < 200 (allow extreme moves, but flag unusual)
  If I_{i,g,t} < 0: ERROR
  If I_{i,g,t} == 0: ERROR
```

**Check 3.3: Month-on-Month Inflation Outliers**
```
For each item i:
  π^{MoM}_{i,g,t} computed as in Section 3.5
  If |π^{MoM}| > 10%: WARN (unusual; verify data)
  Record flagged items
```

**Check 3.4: Index Monotonicity (Inflation >= Base)**
```
For definition d, monthly indices should form a plausible series:
  I_{d,g,t} / I_{d,g,t-1} ∈ [0.95, 1.05] (allow up to ±5% MoM for shocks)
  Severe deviations (>5%): WARN, review data
```

### 5.4 Aggregation Integrity

**Check 4.1: Contribution Sum Identity**
```
For definition d, geography g, month t:
  π^{YoY}_{d,g,t} computed as in Section 3.5
  Σ_i C^{YoY(pp)}_{i→d,g,t} computed as in Section 3.6
  Assert |π^{YoY} - ΣC| < 0.01 pp
  If fail: Investigate missing-item residuals; document
```

**Check 4.2: Group-Level Rollup**
```
For each COICOP division k:
  I_{k,g,t} computed from child items/groups
  Σ_{k} w_{k,g} == W_S(d,g) (if d is headline)
  Contributions by group sum to definition inflation
```

**Check 4.3: Wedge Consistency**
```
If headline and core (ex F+F) indices published:
  wedge(t) = π^{YoY}_{headline} - π^{YoY}_{core}
  exclContr(t) = contribution of excluded items under headline weight
  Report |wedge - exclContr| as reconciliation residual
  If > 0.2 pp: investigate renormalization effects
```

### 5.5 Reconciliation Checks (if official series exists)

**Check 5.1: Against Published Series**
```
If RBI/MoSPI publishes official CPI indices:
  For each definition d in our build:
    I^{official}_{d,g,t} from published data
    I^{computed}_{d,g,t} from our formulas
    err_{d,g,t} = I^{computed} - I^{official}
    Assert |err| < 0.10 (points), or ±0.10% relative
    If fail for multiple items: investigate weights/indices input
```

**Check 5.2: Inflation Rate Accuracy**
```
π^{official}_{d,g,t} computed from published indices
π^{computed}_{d,g,t} computed from our indices
Assert |π^{official} - π^{computed}| < 0.05 pp
```

### 5.6 Data Quality Summary Report

**Output Table (monthly):**

| Definition | Geography | Coverage | MissingCount | FillRate | ImputeRate | π^{YoY} | π^{MoM} | QAStatus |
|-----------|-----------|----------|--------------|----------|-----------|---------|---------|----------|
| headline | combined | 0.996 | 2 | 0.0% | 0.0% | 5.23% | 0.42% | ✓ PASS |
| core_ex_food_fuel | rural | 0.948 | 18 | 0.0% | 0.0% | 4.12% | 0.38% | ⚠ CAUTION |

---

## 6. VISUALIZATION REQUIREMENTS

### 6.1 Data Series Definition

For each visualization, specify the exact computation required (using Section 3 formulas):

#### **V1: Headline vs Core Indices (Level)**

**Data:**
- Time series: $I_{\text{headline},g,t}$ for $t \in [2024-01, \text{latest}]$
- Time series: $I_{\text{core\_ex\_food\_fuel},g,t}$ (or multiple cores)
- Base month = 100

**Computation:**
- Direct output from Section 3.3 for each definition and month

**Plot Type:** Dual-axis line plot  
**Geographies:** Combined; optionally rural/urban panels

---

#### **V2: Headline vs Core Inflation (YoY & MoM)**

**Data:**
- $\pi^{YoY}_{\text{headline},g,t}$ from Section 3.5
- $\pi^{YoY}_{\text{core\_ex\_food\_fuel},g,t}$
- $\pi^{MoM}$ variants (optional)

**Computation:**
$$\pi^{YoY}_{d,g,t} = \left(\frac{I_{d,g,t}}{I_{d,g,t-12}} - 1\right) \times 100$$

**Plot Type:** Dual-line chart (level & date)  
**Axes:** Y = inflation %; X = date (YYYY-MM)

---

#### **V3: Wedge Time Series**

**Data:**
$$\text{wedge}^{YoY}_{g,t} = \pi^{YoY}_{\text{headline},g,t} - \pi^{YoY}_{\text{core\_ex\_food\_fuel},g,t}$$

**Computation:** From Section 3.7

**Plot Type:** Bar or line chart  
**Interpretation:** Positive wedge → headline > core (excluding items are hotter)

---

#### **V4: Contribution Stack (YoY Inflation Breakdown)**

**Data:**
- $C^{YoY(pp)}_{G \to d,g,t}$ for each COICOP division/group $G$ and definition $d$
- Computed from Section 3.6, aggregated to group level

**Composition:**
$$\pi^{YoY}_{d,g,t} = \sum_G C^{YoY(pp)}_{G \to d,g,t}$$

**Plot Type:** Stacked bar chart (groups as colors)  
**X-axis:** Month (YYYY-MM)  
**Y-axis:** Contribution (pp)

**Example:**
```
Month | Food | Fuel | Services | Recreation | Other
2024-02 | +2.1 | +0.8 | +1.2 | -0.2 | +1.1 = +5.0 YoY
2024-03 | +1.9 | +1.2 | +1.3 | +0.1 | +0.9 = +5.4 YoY
```

---

#### **V5: Wedge Attribution (Division-Level Contribution Difference)**

**Data:**
$$\text{wedgeContr}^{YoY}(G,t) = \sum_{i \in G} \left[C^{YoY(pp)}_{i \to \text{headline},g,t} - C^{YoY(pp)}_{i \to \text{core},g,t}\right]$$

(From Approach A, Section 3.7)

**Computation:** Difference of contributions by group between headline and core.

**Plot Type:** Horizontal bar chart or stacked bar (positive = contributed to wedge)  
**Groups:** Food, Fuel, Precious Metals, etc.

---

#### **V6: Breadth Metrics (Diffusion Index)**

**Data:**

Number of items with YoY inflation > threshold X:
$$\text{breadth}_X(d,g,t) = \frac{\sum_{i \in A(d,g,t)} w_{i,g} \cdot \mathbf{1}[\pi^{YoY}_{i,g,t} > X]}{W_A(d,g,t)} \times 100$$

where $\mathbf{1}[\cdot]$ is an indicator (1 if true, 0 otherwise).

**Example thresholds:** X ∈ {3%, 5%, 7%}

**Computation:**
1. For each item $i$: compute $\pi^{YoY}_{i,g,t}$ (Section 3.5)
2. For each threshold: sum weights of items exceeding it
3. Divide by total available weight

**Plot Type:** Multi-line or bar chart showing breadth over time

---

#### **V7: Monthly Release Table (QA & Audit)**

**Data per month:** Structured table including:
- Definition name
- Geography
- Index level ($I_{d,g,t}$)
- YoY inflation ($\pi^{YoY}_{d,g,t}$), pp to 2 decimals
- MoM inflation ($\pi^{MoM}_{d,g,t}$), pp to 2 decimals
- Coverage metric ($\text{cov}(d,g,t)$), % to 1 decimal
- Data quality flag (✓ PASS / ⚠ CAUTION / ⚠ WEAK SIGNAL)
- Link to detailed contribution breakdown

---

### 6.2 Interactive Dashboard Specification

**Suggested Widgets:**
1. **Inflation Tracker:** Headline, Core (ex F+F), Core (ex Fuel), Core (ex PM), selectable by geography
2. **Contribution Browser:** Drill-down by month → division → group → item, with full contribution attribution
3. **Comparison Tool:** Select two definitions and dates; compare indices and inflation rates side-by-side
4. **Wedge Analysis:** Wedge time series + attribution stacked chart
5. **Data Quality Monitor:** Coverage %, fill rates, imputation counts by month and definition

---

## 7. LINKING OLD VS NEW SERIES (if required)

### 7.1 Scenario & Motivation

If moving from a 2012-base CPI to 2024-base CPI, the historical 2012 series and new 2024 series must be linked to form a continuous inflation time series.

**Link Month:** $T^* = $ month when both series have indices (typically Jan 2024).

### 7.2 Link Factor Computation

**At link month $T^*$:**
- Old series: $I^{\text{old}}_{g,T^*}$
- New series: $I^{\text{new}}_{g,T^*}$

**Link factor (ratio):**
$$\text{LF}_g = \frac{I^{\text{new}}_{g,T^*}}{I^{\text{old}}_{g,T^*}}$$

Example: if $I^{\text{old}} = 265.3$ and $I^{\text{new}} = 100.0$, then $\text{LF} = 100 / 265.3 = 0.3769$.

### 7.3 Linked Historical Series

**For months before $T^*$ (using old series):**
$$I^{\text{old,linked}}_{g,t} = I^{\text{old}}_{g,t} \times \text{LF}_g \quad \text{for } t < T^*$$

**For months from $T^*$ onward (using new series):**
$$I^{\text{new,linked}}_{g,t} = I^{\text{new}}_{g,t} \quad \text{for } t \geq T^*$$

**Continuous linked series:**
$$I^{\text{linked}}_{g,t} = \begin{cases}
I^{\text{old}}_{g,t} \times \text{LF}_g & \text{if } t < T^* \\
I^{\text{new}}_{g,t} & \text{if } t \geq T^*
\end{cases}$$

### 7.4 Inflation on Linked Series

**YoY inflation (crossing link month):**

If $t < T^* + 12$ and $t - 12 < T^*$:
$$\pi^{YoY}_{\text{linked},g,t} = \left(\frac{I^{\text{linked}}_{g,t}}{I^{\text{linked}}_{g,t-12}} - 1\right) \times 100$$

Both numerator and denominator use the linked series, so the ratio is consistent.

**Example (with link in Jan 2024):**
- $t = 2025-01$: $I^{\text{new}}_{g,2025-01} = 105.0$
- $t - 12 = 2024-01$: $I^{\text{new}}_{g,2024-01} = 100.0$

$$\pi^{YoY}_{\text{linked},g,2025-01} = \frac{105.0}{100.0} - 1 = 5.0\%$$

**No discontinuity at link month:**
- At $t = T^* = $ Jan 2024:
  $$\pi^{YoY}_{\text{linked},g,2024-01} = \frac{I^{\text{new}}_{2024-01}}{I^{\text{old,linked}}_{2023-01}} = \frac{100.0}{I^{\text{old}}_{2023-01} \times \text{LF}}$$
  This is well-defined and continuous.

### 7.5 Core Indices Under Linking

**For each definition d (headline, core ex F+F, etc.):**

Apply the same SET OF ITEMS and EXCLUSION RULES to both the old and new series.

**Old series, definition d:**
$$I^{\text{old}}_{d,g,t} = \frac{\sum_{i \in S(d,g)} w_{i,g} \times I^{\text{old}}_{i,g,t}}{\sum_{i \in S(d,g)} w_{i,g}}$$

(using old-series indices and old-series weights, which may differ from new series)

**New series, definition d:**
$$I^{\text{new}}_{d,g,t} = \frac{\sum_{i \in S(d,g)} w_{i,g} \times I^{\text{new}}_{i,g,t}}{W_A(d,g,t)}$$

(using new series indices and renormalization)

**Link factor (per definition):**
$$\text{LF}_{d,g} = \frac{I^{\text{new}}_{d,g,T^*}}{I^{\text{old}}_{d,g,T^*}}$$

**Linked series for definition d:**
$$I^{\text{linked}}_{d,g,t} = \begin{cases}
I^{\text{old}}_{d,g,t} \times \text{LF}_{d,g} & \text{if } t < T^* \\
I^{\text{new}}_{d,g,t} & \text{if } t \geq T^*
\end{cases}$$

**Caveat:** If definition $d$ includes/excludes items differently in old vs new series, link factors will differ. Document all link factors in metadata.

---

## APPENDIX A: WORKED EXAMPLE (MINIMAL 5-ITEM BASKET)

### Setup

**Weights & Hierarchy:**

| item_id | item_name | coicop_div | weight_combined | tags |
|---------|-----------|-----------|--------|------|
| I001 | Rice | Food | 20 | food |
| I002 | Wheat | Food | 15 | food |
| I003 | Cooking Oil | Food | 10 | food |
| I_FUEL | Petrol | Fuel | 30 | fuel |
| I_GOLD | Gold | Recreation | 25 | precious_metals; gold |
| | | | **100** | |

**Definitions:**
- **Headline:** All 5 items
- **Core (ex Food+Fuel):** I003 (oil), I_GOLD (gold) only → weight = 35
- **Core (ex Fuel):** I001, I002, I003, I_GOLD → weight = 70

**Indices (2024 base, t=1 and t=1-12 shown):**

| item_id | Index @ t=1-12 | Index @ t=1 |
|---------|-------|-------|
| I001 | 98 | 104 |
| I002 | 99 | 105 |
| I003 | 100 | 102 |
| I_FUEL | 95 | 108 |
| I_GOLD | 97 | 95 |

### Computation 1: Headline Index at t=1

$$I_{\text{headline},g,t=1} = \frac{20 \times 104 + 15 \times 105 + 10 \times 102 + 30 \times 108 + 25 \times 95}{100}$$
$$= \frac{2080 + 1575 + 1020 + 3240 + 2375}{100} = \frac{10290}{100} = 102.90$$

### Computation 2: Core (ex Food+Fuel) at t=1

$S(\text{core\_ff}) = \{I003, I\_GOLD\}$  
$W_S = 10 + 25 = 35$  
All available; $W_A = 35$; cov = 100%.

$$I_{\text{core\_ff},t=1} = \frac{10 \times 102 + 25 \times 95}{35} = \frac{1020 + 2375}{35} = \frac{3395}{35} = 97.00$$

### Computation 3: YoY Inflation

**Headline:**
$$\pi^{YoY}_{\text{headline},t=1} = \left(\frac{102.90}{100.00} - 1\right) \times 100 = 2.90\%$$

(Note: Index at $t=1-12$ baseline is 100 by design in base month.)

**Core (ex F+F):**

Index at $t=1-12$:
$$I_{\text{core\_ff},t=1-12} = \frac{10 \times 100 + 25 \times 97}{35} = \frac{2425}{35} = 69.29$$

$$\pi^{YoY}_{\text{core\_ff},t=1} = \left(\frac{97.00}{69.29} - 1\right) \times 100 = 40.00\%$$

(High inflation due to gold drop from 97 → 95; oil stable.)

### Computation 4: Contributions (YoY) — Headline

Using Method 1 (Section 3.6):

**Index change (absolute):**
$$\Delta I = 102.90 - 100.00 = 2.90$$

**Item-level decomposition:**
Renormalized weights at $t=1$ (all available): $\hat{w}_i = w_i / 100$

$$\Delta I_{I001} = 0.20 \times (104 - 100) = 0.80$$
$$\Delta I_{I002} = 0.15 \times (105 - 100) = 0.75$$
$$\Delta I_{I003} = 0.10 \times (102 - 100) = 0.20$$
$$\Delta I_{I\_FUEL} = 0.30 \times (108 - 100) = 2.40$$
$$\Delta I_{I\_GOLD} = 0.25 \times (95 - 100) = -1.25$$
$$\Sigma = 0.80 + 0.75 + 0.20 + 2.40 - 1.25 = 2.90$$ ✓

**Convert to pp of YoY inflation:**
$$C^{YoY(pp)}_{I001} = \frac{0.80}{100} \times 100 = 0.80 \text{ pp}$$
$$C^{YoY(pp)}_{I002} = \frac{0.75}{100} \times 100 = 0.75 \text{ pp}$$
$$C^{YoY(pp)}_{I003} = \frac{0.20}{100} \times 100 = 0.20 \text{ pp}$$
$$C^{YoY(pp)}_{I\_FUEL} = \frac{2.40}{100} \times 100 = 2.40 \text{ pp}$$
$$C^{YoY(pp)}_{I\_GOLD} = \frac{-1.25}{100} \times 100 = -1.25 \text{ pp}$$
$$\Sigma = 2.90 \text{ pp}$$ ✓

**By Group (COICOP Division):**
$$C^{YoY(pp)}_{\text{Food}} = 0.80 + 0.75 + 0.20 = 1.75 \text{ pp}$$
$$C^{YoY(pp)}_{\text{Fuel}} = 2.40 \text{ pp}$$
$$C^{YoY(pp)}_{\text{Recreation}} = -1.25 \text{ pp}$$

### Computation 5: Wedge Analysis

**Core (ex Fuel) at t=1:**
$$I_{\text{core\_fuel},t=1} = \frac{20 \times 104 + 15 \times 105 + 10 \times 102 + 25 \times 95}{70}$$
$$= \frac{5650}{70} = 80.71$$

**Index at $t=1-12$:**
$$I_{\text{core\_fuel},t=1-12} = \frac{20 \times 98 + 15 \times 99 + 10 \times 100 + 25 \times 97}{70}$$
$$= \frac{4915}{70} = 70.21$$

$$\pi^{YoY}_{\text{core\_fuel},t=1} = \left(\frac{80.71}{70.21} - 1\right) \times 100 = 14.95\%$$

**Wedge:**
$$\text{wedge} = \pi^{YoY}_{\text{headline}} - \pi^{YoY}_{\text{core\_fuel}} = 2.90\% - 14.95\% = -12.05 \text{ pp}$$

(Negative: core ex fuel is much hotter than headline, meaning fuel items are pulling down headline.)

---

## APPENDIX B: CONFIGURATION FILE EXAMPLES

### Example Config (JSON): All Six Definitions

```json
{
  "cpi_definitions": [
    {
      "definition_id": "headline",
      "name": "CPI - Headline",
      "description": "All items in the CPI basket",
      "exclude_rules": {},
      "weight_basis": "ABSOLUTE_TOTAL_SHARES"
    },
    {
      "definition_id": "core_ex_food_fuel",
      "name": "CPI - Core (ex Food & Fuel)",
      "exclude_rules": {
        "exclude_coicop_divisions": [
          {"code": "01", "name": "Food & Non-Alcoholic Beverages"},
          {"code": "04", "name": "Fuel and Light"}
        ]
      }
    },
    {
      "definition_id": "core_ex_fuel",
      "name": "CPI - Core (ex Fuel)",
      "exclude_rules": {
        "exclude_coicop_divisions": [
          {"code": "04", "name": "Fuel and Light"}
        ]
      }
    },
    {
      "definition_id": "core_ex_precious_metals",
      "name": "CPI - Core (ex Precious Metals)",
      "exclude_rules": {
        "exclude_tags": ["precious_metals"]
      }
    },
    {
      "definition_id": "core_ex_silver",
      "name": "CPI - Core (ex Silver)",
      "exclude_rules": {
        "exclude_tags": ["silver"]
      }
    },
    {
      "definition_id": "core_ex_gold_silver",
      "name": "CPI - Core (ex Gold & Silver)",
      "exclude_rules": {
        "exclude_tags": ["gold", "silver"]
      }
    }
  ],
  "global_settings": {
    "base_month": "2024-01",
    "base_index_value": 100.0,
    "missing_data_policy": "DROP_AND_RENORMALIZE",
    "min_coverage_threshold": 0.95,
    "publication_geographies": ["combined", "rural", "urban"]
  }
}
```

---

## SUMMARY TABLE: FORMULA QUICK REFERENCE

| Concept | Formula | Section | Key Notes |
|---------|---------|---------|-----------|
| **Universe Selection** | $S(d,g) = U \setminus \{\text{excluded items}\}$ | 3.1 | Set algebra; configuration-driven |
| **Availability Set** | $A(d,g,t) = \{i \in S : I_{i,g,t} \neq \text{NULL}\}$ | 1.2 | Non-missing items at month t |
| **Coverage** | $\text{cov}(d,g,t) = W_A / W_S$ | 1.2 | Metric: must be ≥ 0.95 for publication |
| **Renormalized Weight** | $\hat{w}_{i,g,t} = w_{i,g} / W_A(d,g,t)$ | 3.2 | Sums to 1; used in index computation |
| **Index (Weighted Mean)** | $I_{d,g,t} = \sum_i \hat{w}_{i,g,t} \cdot I_{i,g,t}$ | 3.3 | Core aggregation formula |
| **YoY Inflation** | $\pi^{YoY}_{d,g,t} = (I_{d,g,t} / I_{d,g,t-12} - 1) \times 100$ | 3.5 | Percentage |
| **MoM Inflation** | $\pi^{MoM}_{d,g,t} = (I_{d,g,t} / I_{d,g,t-1} - 1) \times 100$ | 3.5 | Percentage |
| **Index Change Contribution** | $\Delta I_{i \to d,g,t} = \hat{w}_{i,g,t} \cdot (I_{i,g,t} - I_{i,g,t-12})$ | 3.6 | Additive across items |
| **pp Contribution (YoY)** | $C^{YoY(pp)}_{i \to d,g,t} = \Delta I / I_{d,g,t-12} \times 100$ | 3.6 | Sums exactly to π^{YoY} |
| **Wedge** | $\text{wedge} = \pi^{YoY}_{\text{headline}} - \pi^{YoY}_{\text{core}}$ | 3.7 | pp; attributed to excluded items |
| **Link Factor** | $\text{LF}_g = I^{\text{new}}_{g,T^*} / I^{\text{old}}_{g,T^*}$ | 7.2 | Ratio at link month |
| **Linked Series** | $I^{\text{linked}}_{g,t} = I^{\text{old}}_{g,t} \times \text{LF}$ (if $t < T^*$) | 7.3 | Continuous historical series |

---

**END OF SPECIFICATION**

---

### NEXT STEPS FOR IMPLEMENTATION

1. **Prepare your data files** in the schema specified in Section 0
2. **Load and validate** using checks in Section 5.1–5.2
3. **Define your index definitions** (JSON config; use examples in Appendix B)
4. **Implement aggregation** using core formulas in Section 3.3
5. **Compute contributions** via Section 3.6 (Method 1 recommended)
6. **Generate visualizations** per Section 6
7. **QA and publish** (run full checklist, Section 5)