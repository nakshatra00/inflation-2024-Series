"""
Generate sample price data for testing
Creates price indices for all 358 items over 24 months
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

def generate_price_data(output_file='price_data.xlsx', num_months=24):
    """Generate synthetic price data"""
    
    # Load items to get item codes
    items_df = pd.read_csv(Path(__file__).parent / 'weights_new' / 'items.csv')
    num_items = len(items_df)
    
    print(f"Generating price data for {num_items} items over {num_months} months...")
    
    # Create months
    months = pd.date_range(start='2024-01', periods=num_months, freq='M')
    month_cols = [m.strftime('%Y-%m') for m in months]
    
    # Generate price relatives for all items and all months
    np.random.seed(42)
    price_matrix = np.zeros((num_items, num_months))
    
    for i in range(num_items):
        # Random monthly inflation between 0.2% and 1.5%
        monthly_inflation = 0.002 + (i % 20) * 0.0007  # Vary by item
        
        # Generate cumulative price relatives
        for month_idx in range(num_months):
            relative = (1 + monthly_inflation) ** (month_idx + 1) * 100
            price_matrix[i, month_idx] = relative
    
    # Create dataframe
    price_data = pd.DataFrame(price_matrix, columns=month_cols)
    price_data.insert(0, 'Item_Code', items_df['Item_Code'].values)
    price_data.insert(1, 'Item_Name', items_df['Item_Name'].values)
    
    # Save to Excel
    output_path = Path(__file__).parent / output_file
    price_data.to_excel(output_path, index=False)
    
    print(f"✓ Generated price data saved to: {output_path}")
    print(f"\nData shape: {price_data.shape}")
    print(f"Months: {month_cols[0]} to {month_cols[-1]}")
    print(f"\nSample (first 5 items, first 3 months + last month):")
    
    sample_cols = ['Item_Code', 'Item_Name'] + month_cols[:3] + [month_cols[-1]]
    print(price_data[sample_cols].head())
    
    return price_data

if __name__ == "__main__":
    generate_price_data()
    print("\n✓ Ready to test dashboard!")
    print("\nTo test the dashboard:")
    print("  cd dashboard")
    print("  streamlit run app_new.py")
