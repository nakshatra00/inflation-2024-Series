# How to Use the CPI Hierarchy Export Module

## Quick Start

### Step 1: Module is already imported in your notebook

The notebook cell has been updated to use the `export_hierarchy.py` module. When you run the cell, it will:

1. Import the `CPIHierarchyExporter` class
2. Create the `weights/` directory if needed
3. Export all hierarchy data to CSV and JSON files

### Step 2: Run the export cell

Simply run the cell titled "EXPORT HIERARCHY TO CSV AND JSON" in your notebook. You'll see output like:

```
================================================================================
EXPORTING CSV FILES
================================================================================
✓ divisions.csv - X rows
✓ groups.csv - X rows
✓ classes.csv - X rows
✓ subclasses.csv - X rows
✓ items.csv - X rows

================================================================================
EXPORTING JSON FILE
================================================================================
✓ cpi_hierarchy.json - X divisions, Y items

================================================================================
EXPORT SUMMARY
================================================================================
CSV Files:
  • divisions.csv: X divisions
  • groups.csv: X groups
  • classes.csv: X classes
  • subclasses.csv: X subclasses
  • items.csv: X items

JSON File:
  • cpi_hierarchy.json: Complete hierarchical structure
    - Divisions: X
    - Total Weight: 100.00

Output Directory: /Users/nakshatragupta/Documents/Coding/inflation-2024-Series/weights
================================================================================
```

### Step 3: Files are created

All files will be saved in the `weights/` directory:
- `divisions.csv` - Top level divisions
- `groups.csv` - Groups with division references
- `classes.csv` - Classes with group references
- `subclasses.csv` - Subclasses with class references
- `items.csv` - Items with subclass references
- `cpi_hierarchy.json` - Complete nested hierarchy

## Using the Exported Data

### Load and explore CSVs

```python
import pandas as pd

# Load any level
divisions = pd.read_csv('weights/divisions.csv')
items = pd.read_csv('weights/items.csv')

print(divisions)
print(items.head())
```

### Join CSVs to reconstruct hierarchy

```python
import pandas as pd

# Load all levels
divisions = pd.read_csv('weights/divisions.csv')
groups = pd.read_csv('weights/groups.csv')
classes = pd.read_csv('weights/classes.csv')
subclasses = pd.read_csv('weights/subclasses.csv')
items = pd.read_csv('weights/items.csv')

# Join to get complete picture
result = items.merge(subclasses, on='Subclass_Code')
result = result.merge(classes, on='Class_Code')
result = result.merge(groups, on='Group_Code')
result = result.merge(divisions, on='Division_Code')

print(result.head())
```

### Load JSON for application logic

```python
import json

# Load the complete hierarchy
with open('weights/cpi_hierarchy.json', 'r') as f:
    hierarchy = json.load(f)

# Check metadata
print(f"Total items: {hierarchy['metadata']['total_items']}")
print(f"Total weight: {hierarchy['metadata']['total_weight']}")

# Iterate through divisions
for division in hierarchy['divisions']:
    print(f"\n{division['Division_Name']} (Weight: {division['Weight']})")
    for group in division['groups']:
        print(f"  └─ {group['Group_Name']} (Weight: {group['Weight']})")
```

### Create CPI variants using Include/Exclude

```python
import json
import copy

# Load hierarchy
with open('weights/cpi_hierarchy.json', 'r') as f:
    base_hierarchy = json.load(f)

# Create a variant by excluding a division
ex_food_hierarchy = copy.deepcopy(base_hierarchy)
for division in ex_food_hierarchy['divisions']:
    if 'Food' in division['Division_Name']:
        division['Include'] = False

# Save modified configuration
with open('weights/ex_food_hierarchy.json', 'w') as f:
    json.dump(ex_food_hierarchy, f, indent=2)
```

## File Relationships

### CSV Relationships (Foreign Keys)

```
divisions (Division_Code)
    ↓
groups (Division_Code → Division_Code)
    ↓
classes (Group_Code → Group_Code)
    ↓
subclasses (Class_Code → Class_Code)
    ↓
items (Subclass_Code → Subclass_Code)
```

### JSON Structure

```
hierarchy
├── metadata (base_year, total_items, total_weight, etc.)
└── divisions[] (5 hierarchy levels nested)
    └── groups[]
        └── classes[]
            └── subclasses[]
                └── items[]
```

## Integration with CPI Calculations

The exported hierarchy JSON works seamlessly with your CPI calculation functions:

```python
# Load the exported hierarchy
with open('weights/cpi_hierarchy.json', 'r') as f:
    hierarchy_config = json.load(f)

# Modify for exclusions (e.g., ex-Food)
for division in hierarchy_config['divisions']:
    if division['Division_Name'] == 'Food and beverages':
        division['Include'] = False

# Use with your CPI functions
selected_items = get_selected_items_enhanced(hierarchy_config)
result = calculate_cpi_index_enhanced(selected_items, price_relatives, "CPI Ex-Food")
```

## Key Benefits

✅ **Flexibility**: Use CSV for analytics, JSON for applications  
✅ **Maintainability**: Single source of truth exported to multiple formats  
✅ **Scalability**: Normalized CSV structure for large datasets  
✅ **Reusability**: Include/Exclude flags for variant analysis  
✅ **Portability**: Standard formats (CSV, JSON) work everywhere  

## Notes

- CSV files are normalized and can be imported into any database
- JSON includes Include/Exclude flags for CPI variant creation
- All weights are aggregated from the item level
- Parent-child relationships are maintained through code references
- States data is excluded (as per requirements)
