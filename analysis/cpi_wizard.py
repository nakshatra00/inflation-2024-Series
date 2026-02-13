import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import os

def calculate_mom_change(df, value_column='index', group_columns=None):
    if group_columns is None:
        group_columns = ['division', 'state', 'sector']
    df = df.sort_values(group_columns + ['date']).copy()
    df['mom_change'] = df.groupby(group_columns)[value_column].pct_change() * 100
    return df

def calculate_yoy_change(df, value_column='index', group_columns=None):
    if group_columns is None:
        group_columns = ['division', 'state', 'sector']
    df = df.sort_values(group_columns + ['date']).copy()
    df['yoy_change'] = df.groupby(group_columns)[value_column].pct_change(periods=12) * 100
    return df

class CPIWizard:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.analysis_path = self.base_path / "analysis"
        self.weights_path = self.base_path / "weights_new"
        
        self.data_file = self.analysis_path / "inflation_analysis_results.csv"
        if not self.data_file.exists():
            # Fallback to scraped_cpi if results doesn't exist
            self.data_file = self.analysis_path / "scraped_cpi.csv"
            
        print(f"Loading data from {self.data_file}...")
        self.df = pd.read_csv(self.data_file)
        if 'date' not in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['year'].astype(str) + '-' + self.df['month'], format='%Y-%B')
        else:
            self.df['date'] = pd.to_datetime(self.df['date'])
            
        # Load all weights and build mapping
        self.weights = {
            'division': pd.read_csv(self.weights_path / "divisions.csv"),
            'group': pd.read_csv(self.weights_path / "groups.csv"),
            'class': pd.read_csv(self.weights_path / "classes.csv"),
            'item': pd.read_csv(self.weights_path / "items.csv")
        }
        
        # Build hierarchy mapping for items
        # item_code -> (division_name, group_name, class_name, item_name)
        self.item_map = self._build_item_map()
        
        self.selected_exclusions = {
            'division': [],
            'group': [],
            'class': [],
            'item': []
        }
        self.generated_indices = []
        
    def _build_item_map(self):
        """Creates a lookup from item code to its hierarchy names"""
        items_df = self.weights['item']
        classes_df = self.weights['class']
        groups_df = self.weights['group']
        divisions_df = self.weights['division']
        
        # Merge hierarchy
        # items -> subclasses (ignore for now) -> classes -> groups -> divisions
        # Item code 01.1.1.X -> Class 01.1.1 -> Group 1.1 -> Division 1.0
        
        # For simplicity, we can just use the name mapping since we have them in the data
        # but the weight files are more authoritative for "all items".
        
        # Let's use the codes to be safe
        # Item_Code starts with Class_Code
        # Class has Group_Code
        # Group has Division_Code
        
        res = items_df.copy()
        
        # Map Class
        res['class_code'] = res['Item_Code'].str.extract(r'^(\d+\.\d+\.\d+)')
        res = res.merge(classes_df[['Class_Code', 'Class_Name', 'Group_Code']], 
                        left_on='class_code', right_on='Class_Code', how='left')
        
        # Map Group
        res = res.merge(groups_df[['Group_Code', 'Group_Name', 'Division_Code']], 
                        on='Group_Code', how='left')
        
        # Map Division
        res = res.merge(divisions_df[['Division_Code', 'Division_Name']], 
                        on='Division_Code', how='left')
        
        return res[['Item_Code', 'Item_Name', 'Division_Name', 'Group_Name', 'Class_Name', 'Weight']]

    def _get_excluded_item_codes(self):
        """Determine which item codes are excluded based on current selections"""
        items_full = self.item_map
        excluded = set()
        
        # Exclude by division name
        excluded.update(items_full[items_full['Division_Name'].isin(self.selected_exclusions['division'])]['Item_Code'])
        
        # Exclude by group name
        excluded.update(items_full[items_full['Group_Name'].isin(self.selected_exclusions['group'])]['Item_Code'])
        
        # Exclude by class name
        excluded.update(items_full[items_full['Class_Name'].isin(self.selected_exclusions['class'])]['Item_Code'])
        
        # Exclude by item name
        excluded.update(items_full[items_full['Item_Name'].isin(self.selected_exclusions['item'])]['Item_Code'])
        
        return excluded

    def run(self):
        print("\n" + "="*50)
        print("📊 CPI CUSTOM INDEX WIZARD (MULTI-LEVEL)")
        print("="*50)
        
        while True:
            while True:
                self._show_current_status()
                
                print("\nDefine exclusions for current index:")
                print("1. Division level")
                print("2. Group level")
                print("3. Class level")
                print("4. Item level")
                print("5. CALCULATE current index")
                print("0. RESET core exclusions")
                
                choice = input("\nEnter choice (0-5): ").strip()
                
                if choice == "5":
                    break
                elif choice == "0":
                    for k in self.selected_exclusions: self.selected_exclusions[k] = []
                    print("Reset successful.")
                    continue
                elif choice == "1":
                    self._pick_exclusion('division', 'Division_Name')
                elif choice == "2":
                    self._pick_exclusion('group', 'Group_Name')
                elif choice == "3":
                    self._pick_exclusion('class', 'Class_Name')
                elif choice == "4":
                    self._pick_exclusion('item', 'Item_Name')
                else:
                    print("Invalid choice.")
            
            # Calculate the individual index
            custom_series = self._calculate_current()
            if custom_series is not None:
                self.generated_indices.append(custom_series)
                print(f"\n✓ Successfully added '{custom_series['division'].iloc[0]}' to session queue.")
            
            # Ask to clear exclusions or keep them
            clear_ex = input("\nClear current exclusions for the next index? (y/n): ").strip().lower()
            if clear_ex != 'n':
                for k in self.selected_exclusions: self.selected_exclusions[k] = []
            
            next_step = input("\nWould you like to define ANOTHER index? (y/n): ").strip().lower()
            if next_step != 'y':
                break
                
        if self.generated_indices:
            self._save_results()
        else:
            print("\nNo indices were generated. Exiting.")

    def _show_current_status(self):
        excluded_codes = self._get_excluded_item_codes()
        total_weight = self.item_map['Weight'].sum()
        excluded_weight = self.item_map[self.item_map['Item_Code'].isin(excluded_codes)]['Weight'].sum()
        
        print("\n" + "-"*40)
        print("CURRENT EXCLUSIONS:")
        any_ex = False
        for k, v in self.selected_exclusions.items():
            if v:
                print(f"  {k.title()}: {', '.join(v)}")
                any_ex = True
        if not any_ex: print("  None")
        
        print(f"\nIMPACT SUMMARY:")
        print(f"  Items Excluded: {len(excluded_codes)}")
        print(f"  Weight Removed: {excluded_weight:.2f}")
        print(f"  Weight Remaining: {(total_weight - excluded_weight):.2f}")
        print("-" * 40)

    def _pick_exclusion(self, level, col_name):
        w_df = self.weights[level]
        
        # Filter out what's already excluded
        current_excluded_items = self._get_excluded_item_codes()
        
        # To avoid overlaps, we should skip items where ALL their child-items are already excluded?
        # Actually, simpler to just list all and let the user pick.
        
        print(f"\nAvailable {level}s:")
        for i, row in w_df.iterrows():
            status = "[X]" if row[col_name] in self.selected_exclusions[level] else "[ ]"
            print(f"[{i:3}] {status} {row[col_name]:<50} | Weight: {row['Weight']:.2f}")
            
        indices = input(f"\nEnter indices to toggle exclusion (comma separated): ").strip()
        try:
            for idx in indices.split(","):
                if not idx.strip(): continue
                name = w_df.iloc[int(idx)][col_name]
                if name in self.selected_exclusions[level]:
                    self.selected_exclusions[level].remove(name)
                else:
                    self.selected_exclusions[level].append(name)
        except Exception as e:
            print(f"Error: {e}")

    def _calculate_current(self):
        index_name = input("\nEnter a name for this custom index: ").strip()
        if not index_name:
            index_name = f"Custom Index ({datetime.now().strftime('%H%M%S')})"

        print(f"\nCalculating '{index_name}'...")
        
        excluded_codes = self._get_excluded_item_codes()
        remaining_items = self.item_map[~self.item_map['Item_Code'].isin(excluded_codes)].copy()
        
        if remaining_items.empty:
            print("ERROR: All items excluded. Cannot calculate index.")
            return None
            
        total_weight = remaining_items['Weight'].sum()
        remaining_items['norm_weight'] = (remaining_items['Weight'] / total_weight) * 100
        
        # Filter main data for item-level rows
        item_data = self.df[self.df['item'] != '*'].copy()
        
        # Match with remaining items
        merged = item_data.merge(
            remaining_items[['Item_Code', 'norm_weight']], 
            left_on='code', right_on='Item_Code'
        )
        
        # Calculate weighted average
        group_cols = ['date', 'year', 'month', 'state', 'sector']
        custom_series = merged.groupby(group_cols).apply(
            lambda x: (x['index'] * x['norm_weight']).sum() / x['norm_weight'].sum()
        ).reset_index()
        custom_series.columns = group_cols + ['index']
        
        # Metadata
        custom_series['division'] = index_name
        for lvl in ['group', 'class', 'sub_class', 'item', 'code']:
            custom_series[lvl] = '*'
            
        # Derivatives
        custom_series = calculate_mom_change(custom_series)
        custom_series = calculate_yoy_change(custom_series)
        
        # Show sample
        print("\n" + "-"*30)
        print(f"Index Preview: {index_name}")
        sample = custom_series[
            (custom_series['state'] == 'All India') & 
            (custom_series['sector'] == 'Combined')
        ].tail(2)
        if sample.empty: sample = custom_series.tail(2)
        print(sample[['date', 'index', 'mom_change', 'yoy_change']])
        print("-"*30)
        
        return custom_series

    def _save_results(self):
        if not self.generated_indices: return
        
        print("\n" + "="*50)
        print(f"SESSION SUMMARY: {len(self.generated_indices)} index(es) created.")
        for i, df in enumerate(self.generated_indices, 1):
            print(f"{i}. {df['division'].iloc[0]}")
        print("="*50)
        
        all_custom = pd.concat(self.generated_indices, ignore_index=True)
        
        print("\nSave Options:")
        print("1. Append ALL to main analysis file (inflation_analysis_results.csv)")
        print("2. Save ALL as a NEW standalone file")
        print("3. Discard and Exit")
        
        save_choice = input("\nEnter choice (1-3): ").strip()
        
        if save_choice == '1':
            output_df = pd.concat([self.df, all_custom], ignore_index=True)
            output_df.to_csv(self.data_file, index=False)
            print(f"✓ All indices appended to {self.data_file}")
        elif save_choice == '2':
            default_name = f"custom_cpi_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filename = input(f"\nEnter filename (default: {default_name}): ").strip() or default_name
            if not filename.endswith('.csv'): filename += '.csv'
            
            save_path = self.analysis_path / filename
            all_custom.to_csv(save_path, index=False)
            print(f"✓ Standalone file created at {save_path}")
        else:
            print("Changes discarded.")

if __name__ == "__main__":
    wizard = CPIWizard()
    wizard.run()
