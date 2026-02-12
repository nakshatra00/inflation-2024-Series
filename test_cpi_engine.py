"""
Test script for CPI Engine
Validates that the engine works with weights_new data
"""

import sys
from pathlib import Path
import pandas as pd

# Add dashboard to path
dashboard_dir = Path(__file__).parent / 'dashboard'
sys.path.insert(0, str(dashboard_dir))

from cpi_engine import CPIEngine

def test_engine():
    """Test CPI Engine initialization and basic calculations"""
    
    print("=" * 80)
    print("TESTING CPI ENGINE")
    print("=" * 80)
    
    # Initialize engine
    weights_dir = Path(__file__).parent / 'weights_new'
    
    print(f"\n1. Loading weights from: {weights_dir}")
    engine = CPIEngine(weights_dir)
    print("   ✓ Weights loaded successfully")
    
    # Check hierarchy
    print(f"\n2. Hierarchy structure:")
    print(f"   • Divisions: {len(engine.hierarchy)}")
    
    total_groups = sum(len(d['groups']) for d in engine.hierarchy.values())
    print(f"   • Groups: {total_groups}")
    
    total_classes = sum(
        len(c) for d in engine.hierarchy.values() 
        for g in d['groups'].values() 
        for c in [g.get('classes', {})]
    )
    print(f"   • Classes: {total_classes}")
    
    total_items = engine.items_df.shape[0]
    print(f"   • Items: {total_items}")
    
    # Display divisions
    print(f"\n3. Division Summary:")
    for div_code in sorted(engine.hierarchy.keys()):
        div_data = engine.hierarchy[div_code]
        print(f"   {div_code}: {div_data['name']:50s} Weight: {div_data['weight']:7.2f}%")
    
    # Check weights sum
    total_weight = engine.divisions_df['Weight'].sum()
    print(f"\n4. Weight Validation:")
    print(f"   Total weight of all divisions: {total_weight:.4f}")
    print(f"   Expected: 100.0000")
    print(f"   ✓ PASS" if abs(total_weight - 100.0) < 0.01 else "   ✗ FAIL")
    
    # Check Rice
    print(f"\n5. Critical Item Check (Rice):")
    rice = engine.items_df[engine.items_df['Item_Code'] == '01.1.1.1.1.01']
    if len(rice) > 0:
        rice_weight = rice['Weight'].iloc[0]
        print(f"   Rice weight: {rice_weight:.6f}")
        print(f"   Expected: 2.013186")
        print(f"   ✓ PASS" if abs(rice_weight - 2.013186) < 0.001 else "   ✗ FAIL")
    else:
        print("   ✗ Rice item not found!")
    
    print("\n" + "=" * 80)
    print("✓ ENGINE INITIALIZATION TEST COMPLETE")
    print("=" * 80)
    
    return engine

if __name__ == "__main__":
    engine = test_engine()
    
    print("\nTo run the dashboard:")
    print("  cd /Users/nakshatragupta/Documents/Coding/inflation-2024-Series/dashboard")
    print("  streamlit run app_new.py")
