
#!/usr/bin/env python3
"""
CPI Index Calculator & Comparison Dashboard (Simplified)
Interactive dashboard for calculating CPI indices with dynamic exclusions
Uses Laspeyres index with renormalized weights
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from cpi_engine import CPIEngine

# Configure page
st.set_page_config(
    page_title="CPI Index Calculator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# DATA LOADING & CACHING
# =============================================================================

@st.cache_resource
def initialize_engine():
    """Initialize CPI Engine with weights"""
    weights_dir = Path(__file__).parent.parent / 'weights_new'
    
    try:
        engine = CPIEngine(weights_dir)
        return engine
    except Exception as e:
        st.error(f"Error loading weights: {e}")
        st.stop()

@st.cache_resource
def load_prices(engine):
    """Load price data"""
    # Try to find price data file
    price_files = [
        Path(__file__).parent.parent / 'price_data.xlsx',
        Path(__file__).parent.parent / 'data' / 'price_data.xlsx',
    ]
    
    for price_file in price_files:
        if price_file.exists():
            try:
                engine.load_prices(price_file)
                return True
            except Exception as e:
                continue
    
    st.error("Could not find price data file (price_data.xlsx)")
    return False

# =============================================================================
# CPI CALCULATION & DISPLAY FUNCTIONS
# =============================================================================

def create_hierarchy_ui(engine):
    """Create sidebar UI for hierarchy exclusions"""
    excluded_divisions = []
    excluded_groups = []
    excluded_classes = []
    
    st.sidebar.markdown("## 🎯 Category Selection")
    st.sidebar.markdown(f"**Total Divisions: {len(engine.hierarchy)}**")
    
    for div_code in sorted(engine.hierarchy.keys()):
        div_data = engine.hierarchy[div_code]
        div_name = div_data['name']
        div_weight = div_data['weight']
        
        with st.sidebar.expander(f"📍 {div_name} ({div_weight:.2f}%)", expanded=False):
            # Division level toggle
            div_include = st.checkbox(
                f"Include {div_name}",
                value=True,
                key=f"div_{div_code}"
            )
            
            if not div_include:
                excluded_divisions.append(div_code)
                st.info(f"❌ {div_name} will be excluded")
            
            # Show groups in this division
            if div_include and div_data['groups']:
                st.markdown(f"**Groups ({len(div_data['groups'])}):**")
                
                for grp_code in sorted(div_data['groups'].keys()):
                    grp_data = div_data['groups'][grp_code]
                    grp_name = grp_data['name']
                    grp_weight = grp_data['weight']
                    
                    grp_include = st.checkbox(
                        f"✓ {grp_name} ({grp_weight:.2f}%)",
                        value=True,
                        key=f"grp_{grp_code}"
                    )
                    
                    if not grp_include:
                        excluded_groups.append(grp_code)
                    
                    # Show class count
                    if grp_include and grp_data['classes']:
                        class_count = len(grp_data['classes'])
                        items_count = sum(c['item_count'] for c in grp_data['classes'].values())
                        st.caption(f"└─ {class_count} classes, {items_count} items")
    
    return excluded_divisions, excluded_groups, excluded_classes

def display_metrics(headline, current):
    """Display comparison metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        headline_items = headline['Items_Count']
        current_items = current['Items_Count']
        excluded = headline_items - current_items
        st.metric("📦 Items", f"{current_items}/{headline_items}", f"-{excluded} excluded")
    
    with col2:
        headline_weight = headline['Total_Weight']
        current_weight = current['Total_Weight']
        excluded_pct = current['excluded_weight'] if 'excluded_weight' in current else 0
        st.metric("⚖️ Weight", f"{current_weight:.2f}", f"-{excluded_pct:.2f}% excluded")
    
    with col3:
        headline_idx = headline['Monthly_Data'][-1]['Index'] if headline['Monthly_Data'] else 100
        current_idx = current['Monthly_Data'][-1]['Index'] if current['Monthly_Data'] else 100
        diff = current_idx - headline_idx
        st.metric("📈 Latest Index", f"{current_idx:.2f}", f"{diff:+.2f} vs Headline")
    
    with col4:
        if len(current['Monthly_Data']) > 1:
            curr_idx = current['Monthly_Data'][-1]['Index']
            prev_idx = current['Monthly_Data'][-2]['Index']
            mom_change = ((curr_idx - prev_idx) / prev_idx) * 100
            st.metric("📊 MoM Change", f"{mom_change:+.3f}%")

def display_comparison_chart(headline, current):
    """Display comparison chart"""
    if not headline or not current:
        return
    
    headline_data = pd.DataFrame(headline['Monthly_Data'])
    current_data = pd.DataFrame(current['Monthly_Data'])
    
    fig = go.Figure()
    
    # Headline line
    fig.add_trace(go.Scatter(
        x=headline_data['Month'],
        y=headline_data['Index'],
        mode='lines+markers',
        name='Headline CPI',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=5),
        hovertemplate='<b>Headline</b><br>%{x}<br>Index: %{y:.2f}<extra></extra>'
    ))
    
    # Current (with exclusions) line
    fig.add_trace(go.Scatter(
        x=current_data['Month'],
        y=current_data['Index'],
        mode='lines+markers',
        name='Current CPI',
        line=dict(color='#ff7f0e', width=2, dash='dash'),
        marker=dict(size=5),
        hovertemplate='<b>Current</b><br>%{x}<br>Index: %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title='CPI Index Comparison: Headline vs Current',
        xaxis_title='Month',
        yaxis_title='Index Value (Base 2024 = 100)',
        template='plotly_white',
        hovermode='x unified',
        height=450,
        legend=dict(x=0.02, y=0.98)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_comparison_table(headline, current):
    """Display data comparison table"""
    if not headline or not current:
        return
    
    comparison_data = []
    
    for i, headline_month in enumerate(headline['Monthly_Data']):
        if i < len(current['Monthly_Data']):
            current_month = current['Monthly_Data'][i]
            
            headline_idx = headline_month['Index']
            current_idx = current_month['Index']
            diff = current_idx - headline_idx
            diff_pct = (diff / headline_idx * 100) if headline_idx != 0 else 0
            
            comparison_data.append({
                'Month': headline_month['Month'],
                'Headline': round(headline_idx, 2),
                'Current': round(current_idx, 2),
                'Difference': round(diff, 2),
                'Diff %': round(diff_pct, 3)
            })
    
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

# =============================================================================
# MAIN APP
# =============================================================================

def main():
    # Page title
    st.title("📊 CPI Index Calculator & Comparison Dashboard")
    st.markdown("**Base Year: 2024 (Index = 100) | Methodology: Laspeyres Index with Fixed Weights**")
    
    # Load data
    hierarchy, price_relatives, months, weights_dir = load_data()
    item_grouped = load_item_weights()
    
    # Initialize session state
    if 'selected_divisions' not in st.session_state:
        st.session_state.selected_divisions = {}
    
    # Sidebar - Category Selection
    st.sidebar.markdown("## 🎯 Category Selection")
    st.sidebar.markdown(f"**Available Divisions: {len(hierarchy['divisions'])}**")
    
    selected_divisions = {}
    
    for div in hierarchy['divisions']:
        div_code = str(div['Division_Code']).strip()
        div_name = div['Division_Name']
        div_weight = div['Weight']
        
        with st.sidebar.expander(f"📍 {div_name} ({div_weight:.1f}%)", expanded=False):
            # Division level toggle
            div_include = st.checkbox(
                f"Include Division",
                value=True,
                key=f"div_{div_code}"
            )
            
            selected_divisions[div_code] = {
                'name': div_name,
                'include': div_include,
                'weight': div_weight,
                'groups': {}
            }
            
            if div_include and div['Groups']:
                st.markdown("**Groups in this Division:**")
                for group in div['Groups']:
                    group_code = str(group['Group_Code']).strip()
                    group_name = group['Group_Name']
                    group_weight = group['Weight']
                    
                    group_include = st.checkbox(
                        f"{group_name} ({group_weight:.1f}%)",
                        value=True,
                        key=f"grp_{group_code}"
                    )
                    
                    selected_divisions[div_code]['groups'][group_code] = {
                        'name': group_name,
                        'include': group_include
                    }
    
    # Sidebar - Controls
    st.sidebar.markdown("---")
    st.sidebar.markdown("## ⚡ Actions")
    
    col1, col2 = st.sidebar.columns(2)
    reset_btn = col1.button("� Reset", use_container_width=True)
    calc_btn = col2.button("✅ Calculate", use_container_width=True, type="primary")
    
    # Build configuration
    def build_config():
        config = json.loads(json.dumps(hierarchy))
        for division in config['divisions']:
            div_code = str(division['Division_Code']).strip()
            if div_code in selected_divisions:
                division['Include'] = selected_divisions[div_code]['include']
                for group in division.get('Groups', []):
                    group_code = str(group['Group_Code']).strip()
                    if group_code in selected_divisions[div_code]['groups']:
                        group['Include'] = selected_divisions[div_code]['groups'][group_code]['include']
        return config
    
    # Main content area
    if reset_btn:
        st.rerun()
    
    if calc_btn:
        config = build_config()
        selected_items = get_selected_item_codes(config, price_relatives)
        result = calculate_cpi_index(selected_items, price_relatives, months, "Custom CPI")
        
        if result:
            st.markdown("### � Custom CPI Index")
            display_metrics(result)
            st.markdown("---")
            display_chart(result, "Custom CPI Index Trend")
            st.markdown("### � Monthly Index Values")
            display_table(result)
        else:
            st.warning("No items selected. Please select at least one category.")
    else:
        # Show Headline CPI by default
        headline_config = json.loads(json.dumps(hierarchy))
        selected_items = get_selected_item_codes(headline_config, price_relatives)
        result = calculate_cpi_index(selected_items, price_relatives, months, "Headline CPI")
        
        if result:
            st.markdown("### 📈 Headline CPI Index (All Categories)")
            display_metrics(result)
            st.markdown("---")
            display_chart(result, "Headline CPI Index Trend")
            st.markdown("### 📋 Monthly Index Values")
            display_table(result)
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; color: #999; font-size: 11px;'>
        CPI Index Calculator v1.0 | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
