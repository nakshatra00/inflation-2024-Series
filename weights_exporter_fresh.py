
"""CPI Weights Exporter - Fresh Start

Module for extracting, deduplicating, and exporting CPI weights from Excel
to clean CSV and JSON hierarchy formats.

Usage:
    from weights_exporter_fresh import CPIWeightsExporter
    exporter = CPIWeightsExporter(excel_path='CPI_2024_Weights.xlsx', output_dir='weights_new')
    exporter.export_all()
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional


class CPIWeightsExporter:
    """Export CPI weights from Excel to CSV + JSON hierarchy."""
    
    def __init__(self, excel_path: str = 'CPI_2024_Weights.xlsx', 
                 output_dir: str = 'weights_new',
                 sheet_name: str = '5.3d',
                 header_row: int = 3):
        """Initialize exporter.
        
        Args:
            excel_path: Path to Excel file
            output_dir: Output directory for exports
            sheet_name: Sheet name in Excel
            header_row: Header row number (0-indexed)
        """
        self.excel_path = excel_path
        self.output_dir = Path(output_dir)
        self.sheet_name = sheet_name
        self.header_row = header_row
        self.output_dir.mkdir(exist_ok=True)
        
        self.df_raw = None
        self.items_unique = None
        self.subclass_df = None
        self.class_df = None
        self.group_df = None
        self.division_df = None
    
    def load_and_deduplicate(self) -> bool:
        """Load Excel and deduplicate items."""
        try:
            self.df_raw = pd.read_excel(self.excel_path, sheet_name=self.sheet_name, 
                                        header=self.header_row)
            self.df_raw.columns = self.df_raw.columns.str.strip().str.replace('*', '', regex=False)
            
            self.items_unique = self.df_raw.drop_duplicates(subset=['Item Code'], keep='first')
            required_cols = ['Item Code', 'Item Name', 'Subclass Code', 'Subclass Name',
                           'Class Code', 'Class Name', 'Group Code', 'Group Name',
                           'Division Code', 'Division Name', 'Share in All India**']
            
            # Normalize column names
            self.items_unique.columns = self.items_unique.columns.str.replace(' ', '_')
            self.items_unique = self.items_unique[[c.replace(' ', '_') for c in required_cols]]
            self.items_unique = self.items_unique.reset_index(drop=True)
            
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def build_hierarchy(self) -> bool:
        """Build hierarchy from items."""
        try:
            # Subclass level
            self.subclass_df = self.items_unique.groupby('Subclass_Code').agg({
                'Subclass_Name': 'first',
                'Class_Code': 'first',
                'Class_Name': 'first',
                'Share_in_All_India': 'sum'
            }).reset_index()
            self.subclass_df.columns = ['Subclass_Code', 'Subclass_Name', 'Class_Code', 
                                       'Class_Name', 'Weight']
            
            # Class level
            class_info = self.items_unique.groupby('Class_Code')[['Class_Name', 'Group_Code']].first().reset_index()
            self.class_df = self.subclass_df.groupby('Class_Code')[['Weight']].sum().reset_index()
            self.class_df = self.class_df.merge(class_info, on='Class_Code')
            self.class_df = self.class_df[['Class_Code', 'Class_Name', 'Group_Code', 'Weight']]
            
            # Group level
            group_info = self.items_unique.groupby('Group_Code')[['Group_Name', 'Division_Code']].first().reset_index()
            self.group_df = self.class_df.groupby('Group_Code')[['Weight']].sum().reset_index()
            self.group_df = self.group_df.merge(group_info, on='Group_Code')
            self.group_df = self.group_df[['Group_Code', 'Group_Name', 'Division_Code', 'Weight']]
            
            # Division level
            division_info = self.items_unique.groupby('Division_Code')[['Division_Name']].first().reset_index()
            self.division_df = self.group_df.groupby('Division_Code')[['Weight']].sum().reset_index()
            self.division_df = self.division_df.merge(division_info, on='Division_Code')
            self.division_df = self.division_df[['Division_Code', 'Division_Name', 'Weight']]
            
            return True
        except Exception as e:
            print(f"Error building hierarchy: {e}")
            return False
    
    def export_csvs(self) -> bool:
        """Export to CSV files."""
        try:
            items_export = self.items_unique[['Item_Code', 'Item_Name', 'Subclass_Code', 
                                             'Share_in_All_India']].copy()
            items_export.columns = ['Item_Code', 'Item_Name', 'Subclass_Code', 'Weight']
            items_export['Include_in_CPI'] = True
            items_export.to_csv(self.output_dir / 'items.csv', index=False)
            
            subclass_export = self.subclass_df.copy()
            subclass_export['Include_in_CPI'] = True
            subclass_export.to_csv(self.output_dir / 'subclasses.csv', index=False)
            
            class_export = self.class_df.copy()
            class_export['Include_in_CPI'] = True
            class_export.to_csv(self.output_dir / 'classes.csv', index=False)
            
            group_export = self.group_df.copy()
            group_export['Include_in_CPI'] = True
            group_export.to_csv(self.output_dir / 'groups.csv', index=False)
            
            division_export = self.division_df.copy()
            division_export['Include_in_CPI'] = True
            division_export.to_csv(self.output_dir / 'divisions.csv', index=False)
            
            return True
        except Exception as e:
            print(f"Error exporting CSVs: {e}")
            return False
    
    def export_all(self) -> bool:
        """Run complete export pipeline."""
        if not self.load_and_deduplicate():
            return False
        if not self.build_hierarchy():
            return False
        if not self.export_csvs():
            return False
        return True


if __name__ == '__main__':
    exporter = CPIWeightsExporter()
    exporter.export_all()
    print(f"Export complete: {exporter.output_dir}")
