"""
CPI Index Calculator Engine
Handles Laspeyres calculation with dynamic exclusions
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple


class CPIEngine:
    """Core CPI calculation engine with exclusion support"""
    
    def __init__(self, weights_dir: Path):
        """Initialize with weights and price data"""
        self.weights_dir = Path(weights_dir)
        self.items_df = None
        self.divisions_df = None
        self.groups_df = None
        self.classes_df = None
        self.subclasses_df = None
        self.prices_df = None
        self.months = None
        self.hierarchy = None
        
        self._load_weights()
    
    def _load_weights(self):
        """Load all weight files"""
        try:
            self.items_df = pd.read_csv(self.weights_dir / 'items.csv')
            self.subclasses_df = pd.read_csv(self.weights_dir / 'subclasses.csv')
            self.classes_df = pd.read_csv(self.weights_dir / 'classes.csv')
            self.groups_df = pd.read_csv(self.weights_dir / 'groups.csv')
            self.divisions_df = pd.read_csv(self.weights_dir / 'divisions.csv')
            
            # Build hierarchy for UI
            self._build_hierarchy()
        except FileNotFoundError as e:
            raise Exception(f"Missing weight file: {e}")
    
    def _build_hierarchy(self):
        """Build nested hierarchy structure for UI"""
        self.hierarchy = {}
        
        for _, div_row in self.divisions_df.iterrows():
            div_code = str(div_row['Division_Code']).strip()
            div_name = div_row['Division_Name']
            div_weight = float(div_row['Weight'])
            
            # Get groups in this division
            groups_in_div = self.groups_df[
                self.groups_df['Division_Code'].astype(str) == div_code
            ]
            
            self.hierarchy[div_code] = {
                'name': div_name,
                'weight': div_weight,
                'groups': {}
            }
            
            for _, grp_row in groups_in_div.iterrows():
                grp_code = str(grp_row['Group_Code']).strip()
                grp_name = grp_row['Group_Name']
                grp_weight = float(grp_row['Weight'])
                
                # Get classes in this group
                classes_in_grp = self.classes_df[
                    self.classes_df['Group_Code'].astype(str) == grp_code
                ]
                
                self.hierarchy[div_code]['groups'][grp_code] = {
                    'name': grp_name,
                    'weight': grp_weight,
                    'classes': {}
                }
                
                for _, cls_row in classes_in_grp.iterrows():
                    cls_code = str(cls_row['Class_Code']).strip()
                    cls_name = cls_row['Class_Name']
                    cls_weight = float(cls_row['Weight'])
                    
                    # Get items in this class
                    items_in_cls = self.items_df[
                        self.items_df['Subclass_Code'].str.startswith(
                            cls_code.split('.')[0] + '.' + cls_code.split('.')[1] if '.' in cls_code else cls_code,
                            na=False
                        )
                    ]
                    
                    # Simpler approach: get items via subclass
                    subclasses_in_cls = self.subclasses_df[
                        self.subclasses_df['Class_Code'].astype(str) == cls_code
                    ]
                    
                    item_list = []
                    for _, sub_row in subclasses_in_cls.iterrows():
                        sub_code = str(sub_row['Subclass_Code']).strip()
                        items = self.items_df[
                            self.items_df['Subclass_Code'].astype(str) == sub_code
                        ]['Item_Code'].tolist()
                        item_list.extend(items)
                    
                    self.hierarchy[div_code]['groups'][grp_code]['classes'][cls_code] = {
                        'name': cls_name,
                        'weight': cls_weight,
                        'item_count': len(item_list),
                        'items': item_list
                    }
    
    def load_prices(self, prices_file: Path) -> bool:
        """Load price data"""
        try:
            self.prices_df = pd.read_excel(prices_file)
            
            # Identify month columns (format: YYYY-MM or Price_Relative_YYYY-MM)
            month_cols = [col for col in self.prices_df.columns 
                         if '-' in str(col) and ('20' in str(col) or '21' in str(col))]
            self.months = sorted(month_cols)
            
            return True
        except Exception as e:
            raise Exception(f"Error loading prices: {e}")
    
    def get_headline_index(self) -> Dict:
        """Calculate headline CPI (all items)"""
        selected_items = self.items_df['Item_Code'].tolist()
        return self._calculate_laspeyres(selected_items, "Headline CPI")
    
    def get_index_with_exclusions(self, excluded_divisions: List[str] = None, 
                                  excluded_groups: List[str] = None,
                                  excluded_classes: List[str] = None) -> Dict:
        """Calculate CPI with exclusions"""
        excluded_divisions = excluded_divisions or []
        excluded_groups = excluded_groups or []
        excluded_classes = excluded_classes or []
        
        # Get all item codes
        all_items = set(self.items_df['Item_Code'].tolist())
        excluded_items = set()
        
        # Exclude by division
        for div_code in excluded_divisions:
            div_groups = self.hierarchy.get(div_code, {}).get('groups', {})
            for grp_code in div_groups.keys():
                classes_dict = div_groups[grp_code].get('classes', {})
                for cls_code in classes_dict.keys():
                    excluded_items.update(classes_dict[cls_code].get('items', []))
        
        # Exclude by group
        for grp_code in excluded_groups:
            for div_code, div_data in self.hierarchy.items():
                if grp_code in div_data['groups']:
                    classes_dict = div_data['groups'][grp_code].get('classes', {})
                    for cls_code in classes_dict.keys():
                        excluded_items.update(classes_dict[cls_code].get('items', []))
        
        # Exclude by class
        for cls_code in excluded_classes:
            for div_code, div_data in self.hierarchy.items():
                for grp_code, grp_data in div_data['groups'].items():
                    if cls_code in grp_data.get('classes', {}):
                        excluded_items.update(grp_data['classes'][cls_code].get('items', []))
        
        selected_items = list(all_items - excluded_items)
        
        # Calculate excluded weight
        excluded_weight = self.items_df[
            self.items_df['Item_Code'].isin(excluded_items)
        ]['Weight'].sum()
        
        result = self._calculate_laspeyres(selected_items, "CPI with Exclusions")
        result['excluded_items_count'] = len(excluded_items)
        result['excluded_weight'] = float(excluded_weight)
        
        return result
    
    def _calculate_laspeyres(self, item_codes: List[str], variant_name: str) -> Dict:
        """
        Calculate Laspeyres index
        Formula: L = SUM(P_t / P_0 * W) / SUM(W) * 100
        """
        if not item_codes or self.prices_df is None:
            return None
        
        # Filter data to selected items
        items_data = self.items_df[self.items_df['Item_Code'].isin(item_codes)].copy()
        prices_data = self.prices_df[self.prices_df['Item_Code'].isin(item_codes)].copy()
        
        if len(items_data) == 0 or len(prices_data) == 0:
            return None
        
        # Get weights and normalize to sum to 100
        weights = items_data.set_index('Item_Code')['Weight']
        weight_sum = weights.sum()
        weights_normalized = (weights / weight_sum) * 100
        
        # Calculate index for each month
        monthly_data = []
        
        for month in self.months:
            # Get price relatives for this month
            month_prices = prices_data.set_index('Item_Code')[month]
            
            # Match items
            matched_items = list(set(month_prices.index) & set(weights_normalized.index))
            
            if len(matched_items) == 0:
                continue
            
            # Laspeyres calculation
            weighted_sum = (month_prices[matched_items] * weights_normalized[matched_items]).sum()
            weight_total = weights_normalized[matched_items].sum()
            
            if weight_total > 0:
                index_value = weighted_sum / weight_total * 100
            else:
                index_value = 100.0
            
            monthly_data.append({
                'Month': month,
                'Index': float(index_value)
            })
        
        # Calculate MoM changes
        for i, data in enumerate(monthly_data):
            if i > 0:
                prev_index = monthly_data[i-1]['Index']
                mom_change = ((data['Index'] - prev_index) / prev_index) * 100
                data['MoM_Change_%'] = float(mom_change)
            else:
                data['MoM_Change_%'] = 0.0
        
        result = {
            'Variant': variant_name,
            'Items_Count': len(items_data),
            'Total_Weight': float(weight_sum),
            'Weight_Normalized': float(weight_sum / weight_sum * 100),  # Should be 100
            'Monthly_Data': monthly_data
        }
        
        return result
    
    def get_comparison(self, headline: Dict, current: Dict) -> pd.DataFrame:
        """Create comparison dataframe"""
        if not headline or not current:
            return None
        
        comparison = []
        
        for i, month in enumerate(self.months):
            headline_idx = headline['Monthly_Data'][i]['Index'] if i < len(headline['Monthly_Data']) else None
            current_idx = current['Monthly_Data'][i]['Index'] if i < len(current['Monthly_Data']) else None
            
            if headline_idx is None or current_idx is None:
                continue
            
            comparison.append({
                'Month': month,
                'Headline': round(headline_idx, 2),
                'Current': round(current_idx, 2),
                'Difference': round(current_idx - headline_idx, 2),
                'Difference_%': round(((current_idx - headline_idx) / headline_idx) * 100, 3)
            })
        
        return pd.DataFrame(comparison)
    
    def calculate_custom_index(self, index_configs: List[Dict]) -> Dict:
        """
        Calculate weighted average of custom indices
        
        Args:
            index_configs: List of dicts with keys:
                - name: str (e.g., "Food Only", "Headline")
                - value: float (e.g., 115.45)
                - weight: float (e.g., 100.0)
        
        Returns:
            Dict with comparison data and validation info
        """
        if not index_configs:
            return None
        
        # Validate inputs
        validation_errors = []
        total_weight = 0.0
        indices_data = []
        
        for idx_config in index_configs:
            # Validate required fields
            if not isinstance(idx_config.get('name'), str) or not idx_config['name'].strip():
                validation_errors.append("Missing or invalid index name")
                continue
            
            try:
                value = float(idx_config['value'])
                weight = float(idx_config['weight'])
            except (ValueError, TypeError):
                validation_errors.append(f"Invalid values for {idx_config['name']}: must be numbers")
                continue
            
            if value <= 0:
                validation_errors.append(f"{idx_config['name']}: Index value must be positive")
                continue
            
            if weight < 0:
                validation_errors.append(f"{idx_config['name']}: Weight cannot be negative")
                continue
            
            total_weight += weight
            indices_data.append({
                'name': idx_config['name'].strip(),
                'value': value,
                'weight': weight,
                'contribution': 0.0  # Will be calculated after normalization
            })
        
        if validation_errors:
            return {
                'success': False,
                'errors': validation_errors,
                'indices': []
            }
        
        if total_weight == 0:
            return {
                'success': False,
                'errors': ['Total weight is zero'],
                'indices': []
            }
        
        # Normalize weights to sum to 100
        weight_imbalance = False
        if abs(total_weight - 100.0) > 0.01:  # Allow small rounding errors
            weight_imbalance = True
        
        # Calculate contributions and weighted average
        weighted_sum = 0.0
        for idx in indices_data:
            normalized_weight = (idx['weight'] / total_weight) * 100
            idx['normalized_weight'] = normalized_weight
            idx['contribution'] = (idx['value'] * normalized_weight) / 100
            weighted_sum += idx['contribution']
        
        # Calculate differences from first index (if multiple)
        for idx in indices_data:
            idx['difference'] = idx['value'] - indices_data[0]['value']
            idx['difference_pct'] = ((idx['value'] - indices_data[0]['value']) / indices_data[0]['value'] * 100) if indices_data[0]['value'] != 0 else 0
        
        return {
            'success': True,
            'weighted_average': float(weighted_sum),
            'total_weight_original': float(total_weight),
            'weight_imbalance': weight_imbalance,
            'indices': indices_data,
            'errors': []
        }
    
    def validate_custom_indices(self, index_configs: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate custom index configurations"""
        errors = []
        
        for idx_config in index_configs:
            if not idx_config.get('name', '').strip():
                errors.append("Index name cannot be empty")
            
            try:
                float(idx_config['value'])
            except (ValueError, TypeError):
                errors.append(f"Invalid value for {idx_config['name']}: must be a number")
            
            try:
                float(idx_config['weight'])
            except (ValueError, TypeError):
                errors.append(f"Invalid weight for {idx_config['name']}: must be a number")
        
        return len(errors) == 0, errors
    
    def calculate_core_with_manual_exclusions(
        self,
        headline_old_index: float,
        headline_old_weight: float,
        headline_new_index: float,
        headline_new_weight: float,
        exclusions: List[Dict],
        scenario_name: str = None
    ) -> Dict:
        """
        Calculate CPI after excluding certain items using Laspeyres method
        
        The formula is:
        CPI Ex. Items = (Headline Index × W_total - Σ(Excluded_i Index × W_i)) / (W_total - Σ W_i)
        
        This calculates what the CPI would be if certain items were removed from the basket.
        
        Args:
            headline_old_index: Headline CPI index for base period (e.g., 100.00)
            headline_old_weight: Headline total weight % for base period (usually 100.0)
            headline_new_index: Headline CPI index for current period (e.g., 115.45)
            headline_new_weight: Headline total weight % for current period (usually 100.0)
            exclusions: List of dicts with:
                {
                    'name': str,
                    'old_index': float,  # Excluded item's index for base period
                    'old_weight': float, # Excluded item's weight % for base period
                    'new_index': float,  # Excluded item's index for current period
                    'new_weight': float  # Excluded item's weight % for current period
                }
            scenario_name: Name for this scenario (e.g., "CPI Ex. Food & Energy")
        
        Returns:
            Dict with calculated CPI exclusion metrics
        """
        errors = []
        
        # Validate headline inputs
        try:
            headline_old_index = float(headline_old_index)
            headline_new_index = float(headline_new_index)
            headline_old_weight = float(headline_old_weight)
            headline_new_weight = float(headline_new_weight)
        except (ValueError, TypeError):
            return {
                'success': False,
                'errors': ['Invalid headline index or weight values'],
                'scenario_name': scenario_name or 'Unknown'
            }
        
        if headline_old_index <= 0 or headline_new_index <= 0:
            errors.append("Headline index values must be positive")
        
        if headline_old_weight <= 0 or headline_new_weight <= 0:
            errors.append("Headline weight values must be positive")
        
        # Validate and parse exclusions
        total_excluded_old_weight = 0.0
        total_excluded_new_weight = 0.0
        weighted_sum_old_exclusions = 0.0
        weighted_sum_new_exclusions = 0.0
        valid_exclusions = []
        
        for excl in exclusions:
            try:
                name = excl.get('name', 'Unknown')
                old_idx = float(excl.get('old_index', 0))
                old_wt = float(excl.get('old_weight', 0))
                new_idx = float(excl.get('new_index', 0))
                new_wt = float(excl.get('new_weight', 0))
                
                if old_wt <= 0 and new_wt <= 0:
                    continue  # Skip empty exclusions
                
                # Accumulate weighted sums
                weighted_sum_old_exclusions += old_idx * old_wt
                weighted_sum_new_exclusions += new_idx * new_wt
                total_excluded_old_weight += old_wt
                total_excluded_new_weight += new_wt
                
                valid_exclusions.append({
                    'name': name,
                    'old_index': old_idx,
                    'old_weight': old_wt,
                    'new_index': new_idx,
                    'new_weight': new_wt
                })
                
            except (ValueError, TypeError) as e:
                errors.append(f"Invalid values for exclusion '{excl.get('name', 'Unknown')}': {e}")
        
        if not valid_exclusions:
            errors.append("No valid exclusions provided")
        
        # Check exclusion weights don't exceed headline weights
        if total_excluded_old_weight >= headline_old_weight:
            errors.append(f"Total excluded old weight ({total_excluded_old_weight:.2f}%) must be less than headline weight ({headline_old_weight:.2f}%)")
        
        if total_excluded_new_weight >= headline_new_weight:
            errors.append(f"Total excluded new weight ({total_excluded_new_weight:.2f}%) must be less than headline weight ({headline_new_weight:.2f}%)")
        
        if errors:
            return {
                'success': False,
                'errors': errors,
                'scenario_name': scenario_name or 'Unknown'
            }
        
        # ==========================================================================
        # LASPEYRES CALCULATION FOR CORE INFLATION
        # ==========================================================================
        # Core Index = (Headline Index × W_headline - Σ(Exclusion_i Index × W_i)) / (W_headline - Σ W_i)
        
        # Old period (base)
        weighted_headline_old = headline_old_index * headline_old_weight
        remaining_old_weight = headline_old_weight - total_excluded_old_weight
        cpi_ex_old_index = (weighted_headline_old - weighted_sum_old_exclusions) / remaining_old_weight
        
        # New period (current)
        weighted_headline_new = headline_new_index * headline_new_weight
        remaining_new_weight = headline_new_weight - total_excluded_new_weight
        cpi_ex_new_index = (weighted_headline_new - weighted_sum_new_exclusions) / remaining_new_weight
        
        # Calculate inflation rates
        headline_inflation = ((headline_new_index - headline_old_index) / headline_old_index) * 100
        cpi_ex_inflation = ((cpi_ex_new_index - cpi_ex_old_index) / cpi_ex_old_index) * 100
        diff_from_headline = cpi_ex_inflation - headline_inflation
        
        # Calculate exclusion inflation rates for each item
        for excl in valid_exclusions:
            if excl['old_index'] > 0:
                excl['inflation_rate'] = ((excl['new_index'] - excl['old_index']) / excl['old_index']) * 100
            else:
                excl['inflation_rate'] = 0.0
        
        return {
            'success': True,
            'scenario_name': scenario_name or 'CPI Ex. Items',
            # Headline values
            'headline_old_index': float(headline_old_index),
            'headline_new_index': float(headline_new_index),
            'headline_old_weight': float(headline_old_weight),
            'headline_new_weight': float(headline_new_weight),
            'headline_inflation': float(headline_inflation),
            # CPI Ex. values (after exclusions)
            'old_index': float(cpi_ex_old_index),
            'new_index': float(cpi_ex_new_index),
            'old_weight': float(remaining_old_weight),
            'new_weight': float(remaining_new_weight),
            'inflation_rate': float(cpi_ex_inflation),
            # Differences
            'difference_from_headline': float(diff_from_headline),
            # Exclusion details
            'total_excluded_old_weight': float(total_excluded_old_weight),
            'total_excluded_new_weight': float(total_excluded_new_weight),
            'remaining_old_weight': float(remaining_old_weight),
            'remaining_new_weight': float(remaining_new_weight),
            'excluded_items_count': len(valid_exclusions),
            'remaining_items_count': len(self.items_df) if self.items_df is not None else 0,
            'exclusions': valid_exclusions,
            'errors': []
        }

