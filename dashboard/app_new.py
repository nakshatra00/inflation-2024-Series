#!/usr/bin/env python3
"""
CPI Index Calculator & Comparison Dashboard v4
Unified interface with global index/weight inputs
Tab 1: Category Exclusions (sidebar-based)
Tab 2: Manual Exclusions (fully customizable with Laspeyres)
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
# SESSION STATE INITIALIZATION
# =============================================================================

if 'manual_exclusions' not in st.session_state:
    st.session_state.manual_exclusions = []
if 'scenario_results' not in st.session_state:
    st.session_state.scenario_results = []

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
def load_prices(_engine):
    """Load price data"""
    price_files = [
        Path(__file__).parent.parent / 'price_data.xlsx',
        Path(__file__).parent.parent / 'data' / 'price_data.xlsx',
    ]
    
    for price_file in price_files:
        if price_file.exists():
            try:
                _engine.load_prices(price_file)
                return True
            except Exception as e:
                continue
    
    st.error("Could not find price data file (price_data.xlsx)")
    return False

# =============================================================================
# TAB 1: CATEGORY EXCLUSIONS FUNCTIONS
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
            div_include = st.checkbox(
                f"Include {div_name}",
                value=True,
                key=f"div_{div_code}"
            )
            
            if not div_include:
                excluded_divisions.append(div_code)
                st.info(f"❌ {div_name} will be excluded")
            
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
                    
                    if grp_include and grp_data['classes']:
                        class_count = len(grp_data['classes'])
                        items_count = sum(c['item_count'] for c in grp_data['classes'].values())
                        st.caption(f"└─ {class_count} classes, {items_count} items")
    
    return excluded_divisions, excluded_groups, excluded_classes

# =============================================================================
# TAB 2: MANUAL EXCLUSIONS FUNCTIONS
# =============================================================================

def create_manual_exclusions_form():
    """Create manual exclusions form with full index/weight inputs for headline and each exclusion"""
    st.markdown("## 📝 CPI Exclusion Calculator")
    st.markdown("Calculate CPI after excluding specific items from the headline basket")
    
    # Initialize exclusions in session state with full structure
    if not st.session_state.manual_exclusions:
        st.session_state.manual_exclusions = [{
            'name': '', 
            'old_index': 100.0, 
            'old_weight': 0.0,
            'new_index': 100.0,
            'new_weight': 0.0
        }]
    
    # ==========================================================================
    # HEADLINE CPI INPUTS
    # ==========================================================================
    st.markdown("### 📊 Headline CPI (Full Basket)")
    st.markdown("Enter the headline CPI index values and weights for both periods")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Old Period (Base)**")
        headline_old_index = st.number_input(
            "Headline Old Index",
            value=100.0,
            min_value=0.0,
            step=0.1,
            key="headline_old_index",
            help="CPI index value for the base/previous period"
        )
        headline_old_weight = st.number_input(
            "Headline Old Weight %",
            value=100.0,
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            key="headline_old_weight",
            help="Total weight of headline basket (typically 100%)"
        )
    
    with col2:
        st.markdown("**New Period (Current)**")
        headline_new_index = st.number_input(
            "Headline New Index",
            value=115.45,
            min_value=0.0,
            step=0.1,
            key="headline_new_index",
            help="CPI index value for the current period"
        )
        headline_new_weight = st.number_input(
            "Headline New Weight %",
            value=100.0,
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            key="headline_new_weight",
            help="Total weight of headline basket (typically 100%)"
        )
    
    st.divider()
    
    # ==========================================================================
    # ITEMS TO EXCLUDE
    # ==========================================================================
    st.markdown("### ❌ Items to Exclude from Headline")
    st.markdown("Enter the index values and weights of items you want to remove from the headline CPI")
    
    # Header row
    cols = st.columns([1.8, 1, 1, 1, 1, 0.5])
    cols[0].markdown("**Item Name**")
    cols[1].markdown("**Old Index**")
    cols[2].markdown("**Old Wt %**")
    cols[3].markdown("**New Index**")
    cols[4].markdown("**New Wt %**")
    cols[5].markdown("**Del**")
    st.divider()
    
    indices_to_remove = []
    
    for idx, exclusion in enumerate(st.session_state.manual_exclusions):
        cols = st.columns([1.8, 1, 1, 1, 1, 0.5])
        
        with cols[0]:
            exclusion['name'] = st.text_input(
                "Name",
                value=exclusion.get('name', ''),
                key=f"excl_name_{idx}",
                label_visibility="collapsed",
                placeholder="e.g., Food & Beverages"
            )
        
        with cols[1]:
            exclusion['old_index'] = st.number_input(
                "Old Index",
                value=float(exclusion.get('old_index', 100.0)),
                min_value=0.0,
                step=0.1,
                key=f"excl_old_idx_{idx}",
                label_visibility="collapsed"
            )
        
        with cols[2]:
            exclusion['old_weight'] = st.number_input(
                "Old Weight",
                value=float(exclusion.get('old_weight', 0.0)),
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                key=f"excl_old_wt_{idx}",
                label_visibility="collapsed"
            )
        
        with cols[3]:
            exclusion['new_index'] = st.number_input(
                "New Index",
                value=float(exclusion.get('new_index', 100.0)),
                min_value=0.0,
                step=0.1,
                key=f"excl_new_idx_{idx}",
                label_visibility="collapsed"
            )
        
        with cols[4]:
            exclusion['new_weight'] = st.number_input(
                "New Weight",
                value=float(exclusion.get('new_weight', 0.0)),
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                key=f"excl_new_wt_{idx}",
                label_visibility="collapsed"
            )
        
        with cols[5]:
            if st.button("❌", key=f"del_excl_{idx}", help="Delete row"):
                indices_to_remove.append(idx)
    
    # Remove marked entries
    for idx in sorted(indices_to_remove, reverse=True):
        st.session_state.manual_exclusions.pop(idx)
    
    # Add button
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("➕ Add Exclusion Row", use_container_width=True):
            st.session_state.manual_exclusions.append({
                'name': '', 
                'old_index': 100.0, 
                'old_weight': 0.0,
                'new_index': 100.0,
                'new_weight': 0.0
            })
            st.rerun()
    
    st.divider()
    
    # Scenario Name
    st.markdown("### 📛 Scenario Name")
    scenario_name = st.text_input(
        "Scenario Name",
        value="CPI Ex. Food & Energy",
        placeholder="e.g., CPI Ex. Food, CPI Ex. Fuel",
        label_visibility="collapsed"
    )
    
    return {
        'headline': {
            'old_index': headline_old_index,
            'old_weight': headline_old_weight,
            'new_index': headline_new_index,
            'new_weight': headline_new_weight
        },
        'exclusions': [e for e in st.session_state.manual_exclusions if e['name'].strip()],
        'scenario_name': scenario_name
    }

def display_manual_results(engine, form_data, results_list):
    """Display results from CPI exclusion calculation"""
    if not results_list:
        st.info("No scenarios calculated yet. Fill the form and click Calculate.")
        return
    
    st.markdown("## 📊 Results")
    st.divider()
    
    # Show calculation trace for the latest result
    latest_result = results_list[-1]
    if latest_result['success']:
        with st.expander("🔍 Calculation Trace (Debug)", expanded=True):
            st.markdown("**Laspeyres Exclusion Formula:**")
            st.latex(r"\text{CPI Ex. Items} = \frac{\text{Headline} \times W_{total} - \sum(\text{Excluded}_i \times W_i)}{W_{total} - \sum W_i}")
            
            st.markdown("---")
            st.markdown("**Input Values:**")
            
            h_old_idx = latest_result['headline_old_index']
            h_old_wt = latest_result['headline_old_weight']
            h_new_idx = latest_result['headline_new_index']
            h_new_wt = latest_result['headline_new_weight']
            
            st.write(f"Headline Old: Index = {h_old_idx}, Weight = {h_old_wt}%")
            st.write(f"Headline New: Index = {h_new_idx}, Weight = {h_new_wt}%")
            
            st.markdown("**Items Excluded:**")
            excl_old_sum = 0.0
            excl_new_sum = 0.0
            excl_old_wt_sum = 0.0
            excl_new_wt_sum = 0.0
            
            for excl in latest_result.get('exclusions', []):
                st.write(f"  - {excl['name']}: Old({excl['old_index']} × {excl['old_weight']}%) = {excl['old_index'] * excl['old_weight']:.2f}, New({excl['new_index']} × {excl['new_weight']}%) = {excl['new_index'] * excl['new_weight']:.2f}")
                excl_old_sum += excl['old_index'] * excl['old_weight']
                excl_new_sum += excl['new_index'] * excl['new_weight']
                excl_old_wt_sum += excl['old_weight']
                excl_new_wt_sum += excl['new_weight']
            
            st.markdown("---")
            st.markdown("**Calculation Steps:**")
            
            # Old period
            weighted_headline_old = h_old_idx * h_old_wt
            remaining_old_weight = h_old_wt - excl_old_wt_sum
            cpi_ex_old = (weighted_headline_old - excl_old_sum) / remaining_old_weight if remaining_old_weight > 0 else 0
            
            st.write(f"**Old Period:**")
            st.write(f"  Headline × Weight = {h_old_idx} × {h_old_wt} = {weighted_headline_old}")
            st.write(f"  Sum(Excluded × Weight) = {excl_old_sum:.2f}")
            st.write(f"  Remaining Weight = {h_old_wt} - {excl_old_wt_sum} = {remaining_old_weight}")
            st.write(f"  CPI Ex. Old = ({weighted_headline_old} - {excl_old_sum:.2f}) / {remaining_old_weight} = **{cpi_ex_old:.4f}**")
            
            # New period
            weighted_headline_new = h_new_idx * h_new_wt
            remaining_new_weight = h_new_wt - excl_new_wt_sum
            cpi_ex_new = (weighted_headline_new - excl_new_sum) / remaining_new_weight if remaining_new_weight > 0 else 0
            
            st.write(f"**New Period:**")
            st.write(f"  Headline × Weight = {h_new_idx} × {h_new_wt} = {weighted_headline_new}")
            st.write(f"  Sum(Excluded × Weight) = {excl_new_sum:.2f}")
            st.write(f"  Remaining Weight = {h_new_wt} - {excl_new_wt_sum} = {remaining_new_weight}")
            st.write(f"  CPI Ex. New = ({weighted_headline_new} - {excl_new_sum:.2f}) / {remaining_new_weight} = **{cpi_ex_new:.4f}**")
            
            # Inflation
            headline_infl = ((h_new_idx - h_old_idx) / h_old_idx) * 100
            cpi_ex_infl = ((cpi_ex_new - cpi_ex_old) / cpi_ex_old) * 100 if cpi_ex_old > 0 else 0
            
            st.markdown("---")
            st.write(f"**Headline Inflation:** (({h_new_idx} - {h_old_idx}) / {h_old_idx}) × 100 = **{headline_infl:.4f}%**")
            st.write(f"**CPI Ex. Inflation:** (({cpi_ex_new:.4f} - {cpi_ex_old:.4f}) / {cpi_ex_old:.4f}) × 100 = **{cpi_ex_infl:.4f}%**")
            st.write(f"**Difference:** {cpi_ex_infl:.4f} - {headline_infl:.4f} = **{cpi_ex_infl - headline_infl:.4f} pp**")
    
    st.divider()
    
    # Summary table
    st.markdown("### Scenario Comparison Table")
    
    table_data = []
    for result in results_list:
        if result['success']:
            table_data.append({
                'Scenario': result['scenario_name'],
                'Headline Old': f"{result['headline_old_index']:.2f}",
                'Headline New': f"{result['headline_new_index']:.2f}",
                'CPI Ex. Old': f"{result['old_index']:.2f}",
                'CPI Ex. New': f"{result['new_index']:.2f}",
                'CPI Ex. Infl %': f"{result['inflation_rate']:.3f}%",
                'Headline Infl %': f"{result['headline_inflation']:.3f}%",
                'Diff (pp)': f"{result['difference_from_headline']:+.3f}",
                'Excl. Wt %': f"{result['total_excluded_old_weight']:.2f}%"
            })
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Visualization
        st.markdown("### Inflation Rate Comparison")
        
        scenario_names = [r['scenario_name'] for r in results_list if r['success']]
        inflation_rates = [r['inflation_rate'] for r in results_list if r['success']]
        headline_rates = [r['headline_inflation'] for r in results_list if r['success']]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='CPI Ex. Inflation',
            x=scenario_names,
            y=inflation_rates,
            marker_color='#1f77b4',
            text=[f"{x:.3f}%" for x in inflation_rates],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>CPI Ex.: %{y:.3f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name='Headline Inflation',
            x=scenario_names,
            y=headline_rates,
            marker_color='#ff7f0e',
            text=[f"{x:.3f}%" for x in headline_rates],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Headline: %{y:.3f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title='Inflation Rates: CPI Ex. Items vs Headline',
            xaxis_title='Scenario',
            yaxis_title='Inflation Rate (%)',
            template='plotly_white',
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Detailed breakdown
        st.markdown("### Detailed Breakdown")
        
        for result in results_list:
            if result['success']:
                with st.expander(f"📋 {result['scenario_name']}", expanded=False):
                    st.markdown("**Headline CPI:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Old Index", f"{result['headline_old_index']:.2f}")
                        st.metric("New Index", f"{result['headline_new_index']:.2f}")
                    with col2:
                        st.metric("Old Weight", f"{result['headline_old_weight']:.2f}%")
                        st.metric("New Weight", f"{result['headline_new_weight']:.2f}%")
                    with col3:
                        st.metric("Headline Inflation", f"{result['headline_inflation']:.3f}%")
                    
                    st.divider()
                    st.markdown("**CPI After Exclusions:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("CPI Ex. Old Index", f"{result['old_index']:.2f}")
                        st.metric("CPI Ex. New Index", f"{result['new_index']:.2f}")
                    with col2:
                        st.metric("Remaining Old Wt", f"{result['remaining_old_weight']:.2f}%")
                        st.metric("Remaining New Wt", f"{result['remaining_new_weight']:.2f}%")
                    with col3:
                        st.metric("CPI Ex. Inflation", f"{result['inflation_rate']:.3f}%")
                        st.metric("Diff from Headline", f"{result['difference_from_headline']:+.3f} pp")
                    
                    st.divider()
                    st.markdown("**Items Excluded:**")
                    excl_data = []
                    for excl in result.get('exclusions', []):
                        excl_data.append({
                            'Item': excl['name'],
                            'Old Index': f"{excl['old_index']:.2f}",
                            'Old Weight %': f"{excl['old_weight']:.2f}%",
                            'New Index': f"{excl['new_index']:.2f}",
                            'New Weight %': f"{excl['new_weight']:.2f}%",
                            'Item Inflation %': f"{excl.get('inflation_rate', 0):.3f}%"
                        })
                    if excl_data:
                        excl_df = pd.DataFrame(excl_data)
                        st.dataframe(excl_df, use_container_width=True, hide_index=True)

# =============================================================================
# MAIN APP
# =============================================================================

def main():
    st.title("📊 CPI Exclusion Calculator")
    st.markdown("**Calculate CPI after excluding specific items | Laspeyres Method**")
    
    # Initialize engine
    engine = initialize_engine()
    
    # Load price data
    if not load_prices(engine):
        st.stop()
    
    # Create tabs
    tab1, tab2 = st.tabs(["📍 Exclude from Data (Predefined)", "📝 Manual Input (Custom)"])
    
    # =============================================================================
    # TAB 1
    # =============================================================================
    with tab1:
        st.markdown("### Method 1: Exclude from Loaded Data")
        st.markdown("Select categories from the sidebar to exclude from headline CPI")
        st.markdown("*Note: This method uses the actual CPI data loaded from the system*")
        
        excluded_divisions, excluded_groups, excluded_classes = create_hierarchy_ui(engine)
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("## ⚡ Actions")
        
        col1, col2 = st.sidebar.columns(2)
        reset_btn = col1.button("🔄 Reset", use_container_width=True, key="reset_cat")
        calc_btn = col2.button("✅ Calculate", use_container_width=True, type="primary", key="calc_cat")
        
        if reset_btn:
            st.rerun()
        
        if calc_btn or (excluded_divisions or excluded_groups):
            # Use existing engine method for category-based exclusions
            result = engine.get_index_with_exclusions(
                excluded_divisions=excluded_divisions,
                excluded_groups=excluded_groups,
                excluded_classes=excluded_classes
            )
            
            if result:
                headline = engine.get_headline_index()
                
                st.markdown("## 📊 CPI Comparison")
                st.markdown("---")
                
                # Get latest data
                if result.get('Monthly_Data') and headline.get('Monthly_Data'):
                    latest_core = result['Monthly_Data'][-1]
                    latest_headline = headline['Monthly_Data'][-1]
                    
                    # Metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("📦 Items Included", result['Items_Count'])
                    
                    with col2:
                        excluded_weight = 100 - result['Total_Weight']
                        st.metric("⚖️ Weight Excl.", f"{excluded_weight:.2f}%")
                    
                    with col3:
                        st.metric("📈 Core Index", f"{latest_core['Index']:.2f}")
                    
                    with col4:
                        st.metric("📈 Headline Index", f"{latest_headline['Index']:.2f}")
                    
                    st.markdown("---")
                    
                    # MoM change comparison
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Core MoM Change", f"{latest_core.get('MoM_Change_%', 0):.3f}%")
                    with col2:
                        st.metric("Headline MoM Change", f"{latest_headline.get('MoM_Change_%', 0):.3f}%")
                    
                    st.markdown("---")
                    
                    # Visualization
                    fig = go.Figure()
                    
                    fig.add_trace(go.Bar(
                        x=['Headline', 'Core (Excl.)'],
                        y=[latest_headline['Index'], latest_core['Index']],
                        marker_color=['#ff7f0e', '#1f77b4'],
                        text=[f"{latest_headline['Index']:.2f}", f"{latest_core['Index']:.2f}"],
                        textposition='auto',
                        hovertemplate='<b>%{x}</b><br>Index: %{y:.2f}<extra></extra>'
                    ))
                    
                    fig.update_layout(
                        title='CPI Index Comparison (Latest Month)',
                        xaxis_title='Type',
                        yaxis_title='Index Value',
                        template='plotly_white',
                        height=400,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    st.markdown("### Excluded Categories")
                    
                    excl_data = []
                    for div_code in excluded_divisions:
                        div_data = engine.hierarchy.get(div_code, {})
                        if div_data:
                            excl_data.append({
                                'Type': 'Division',
                                'Category': div_data['name'],
                                'Weight %': f"{div_data['weight']:.2f}%"
                            })
                    
                    for grp_code in excluded_groups:
                        for div_data in engine.hierarchy.values():
                            if grp_code in div_data.get('groups', {}):
                                grp_data = div_data['groups'][grp_code]
                                excl_data.append({
                                    'Type': 'Group',
                                    'Category': grp_data['name'],
                                    'Weight %': f"{grp_data['weight']:.2f}%"
                                })
                    
                    if excl_data:
                        excl_df = pd.DataFrame(excl_data)
                        st.dataframe(excl_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("No monthly data available")
            else:
                st.error("❌ Calculation failed")
        else:
            st.info("👈 Select categories to exclude in the sidebar, then click Calculate")
    
    # =============================================================================
    # TAB 2
    # =============================================================================
    with tab2:
        st.markdown("### Method 2: CPI Exclusion Calculator")
        st.markdown("Enter headline CPI and items to exclude to calculate CPI excluding those items")
        
        form_data = create_manual_exclusions_form()
        
        st.divider()
        
        col1, col2 = st.columns([1, 1])
        with col1:
            calculate = st.button("✅ Calculate", type="primary", use_container_width=True, key="calc_manual")
        with col2:
            clear = st.button("🔄 Clear All", use_container_width=True, key="clear_manual")
        
        if clear:
            st.session_state.manual_exclusions = [{
                'name': '', 
                'old_index': 100.0, 
                'old_weight': 0.0,
                'new_index': 100.0,
                'new_weight': 0.0
            }]
            if 'tab2_results' in st.session_state:
                st.session_state.tab2_results = []
            st.rerun()
        
        if calculate:
            headline = form_data['headline']
            exclusions = form_data['exclusions']
            
            # Validate headline
            if not headline['old_index'] or not headline['new_index']:
                st.error("❌ Please provide both old and new headline index values")
            elif headline['old_weight'] <= 0 or headline['new_weight'] <= 0:
                st.error("❌ Please provide positive headline weight values")
            elif not exclusions:
                st.error("❌ Please add at least one exclusion with weight > 0")
            else:
                # Calculate using updated method with full exclusion structure
                result = engine.calculate_core_with_manual_exclusions(
                    headline_old_index=headline['old_index'],
                    headline_old_weight=headline['old_weight'],
                    headline_new_index=headline['new_index'],
                    headline_new_weight=headline['new_weight'],
                    exclusions=exclusions,
                    scenario_name=form_data['scenario_name']
                )
                
                if result['success']:
                    if 'tab2_results' not in st.session_state:
                        st.session_state.tab2_results = []
                    st.session_state.tab2_results.append(result)
                    st.success(f"✅ Scenario '{form_data['scenario_name']}' calculated!")
                else:
                    st.error("❌ Calculation failed:")
                    for error in result.get('errors', []):
                        st.error(f"  • {error}")
        
        # Display results
        if hasattr(st.session_state, 'tab2_results') and st.session_state.tab2_results:
            display_manual_results(engine, form_data, st.session_state.tab2_results)
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; color: #999; font-size: 11px;'>
        CPI Index Calculator v4.0 | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
