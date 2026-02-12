# CPI Index Calculator & Comparison Dashboard

An interactive Streamlit-based dashboard for calculating and comparing CPI (Consumer Price Index) variants by dynamically including/excluding categories.

## 📋 Features

- **Interactive Category Selection**: Toggle divisions, groups, and classes on/off
- **Real-time CPI Calculation**: Laspeyres index calculation with base year 2024
- **Visual Analytics**: Interactive charts showing index trends
- **Metrics Dashboard**: View items count, total weight, current index, and month-on-month changes
- **Data Export**: Download index data with MoM changes
- **Multiple Variants**: Compare Headline, Core, and custom CPI variants

## 🚀 Quick Start

### Installation

```bash
cd dashboard
pip install -r requirements.txt
```

### Running the Dashboard

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

## 📊 How It Works

1. **Headline CPI** (Default): Shows all categories with their weights
2. **Select Categories**: Use the sidebar to include/exclude divisions and groups
3. **Calculate**: Click the "Calculate" button to compute the custom CPI
4. **View Results**: See metrics, charts, and data tables

## 📁 Data Structure

The dashboard reads from the `weights/` directory:
- `cpi_hierarchy.json` - Hierarchical structure of divisions, groups, and classes
- `item_laspeyres_indices.xlsx` - Price relatives and weights for each item
- `cpi_variants_comparison.xlsx` - Pre-calculated variant comparisons

## 🧮 Methodology

**Laspeyres Index Formula:**
$$I_t = \frac{\sum (P_t \times W_{2024})}{\sum (P_{2024} \times W_{2024})} \times 100$$

Where:
- $P_t$ = Price at time t (represented by price relatives)
- $W_{2024}$ = 2024 base year weights
- Base year 2024 = 100

## 🎨 Interface Components

### Sidebar
- **Category Selection**: Hierarchical expandable sections for each division
- **Actions**: Reset and Calculate buttons

### Main Area
- **Metrics Cards**: Key performance indicators
- **Interactive Chart**: Line chart showing index trends over time
- **Data Table**: Monthly index values with MoM changes

## 💡 Example Use Cases

1. **Core CPI Analysis**: Exclude Food and Tobacco
2. **Ex-Housing Analysis**: Understand inflation excluding housing costs
3. **Custom Mix**: Select specific categories relevant to your analysis
4. **Comparison**: Compare different variants side-by-side

## 📈 Outputs

- **Current Index**: Latest month's index value
- **MoM Change**: Month-on-month percentage change
- **Items Count**: Number of items included in the calculation
- **Total Weight**: Sum of weights for selected items

## 🔧 Configuration

The dashboard automatically loads configuration from:
- Weights directory path: `../weights/`
- Hierarchy structure: Stored in `cpi_hierarchy.json`
- Price data: Stored in Excel files

## 📝 Notes

- Base year for all indices is 2024 (Index = 100)
- Weights are fixed at 2024 values (Laspeyres methodology)
- Data spans 24 months (2024-01 to 2025-12)
- All calculations are done in real-time

## 🐛 Troubleshooting

**Issue**: "Error loading data"
- **Solution**: Ensure `weights/` directory exists with required Excel files

**Issue**: "No items selected"
- **Solution**: Select at least one category before clicking Calculate

**Issue**: Slow performance with many categories
- **Solution**: Use the Reset button to deselect all, then select specific categories

## 📞 Support

For issues or feature requests, check the project repository.
