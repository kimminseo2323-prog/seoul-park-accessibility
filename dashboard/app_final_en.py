"""
Seoul Park Service Analysis Dashboard (English Version)
- QGIS 04.BI Style UI
- Includes all analysis features from s2_module
"""
import dash
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import geopandas as gpd
import numpy as np
import json
from pathlib import Path
import sys

# Project path configuration
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules import DataLoader
from modules.config import BUFFER_DISTANCES, DEFAULT_BUFFER, MAP_CENTER, MAP_ZOOM, MAP_HEIGHT
from modules.visualizations import (
    create_service_map_enhanced,
    add_park_markers,
    add_park_polygons,
    add_park_buffers,
    add_grid_layer,
    add_boundary_lines,
    add_sigungu_boundaries
)

# Dash app initialization
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True
)

app.title = "Seoul Park Service Analysis"

# Dark mode CSS styles
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* ========== QGIS Dark Mode Style ========== */

            /* Global background */
            body {
                background-color: #121212 !important;
                color: #E0E0E0 !important;
            }

            /* Dropdown control */
            .Select-control,
            div[class*="control"] {
                background-color: #1E1E1E !important;
                border-color: #404040 !important;
                color: #E0E0E0 !important;
            }

            /* Dropdown menu */
            .Select-menu-outer,
            .Select-menu,
            div[class*="menu"] {
                background-color: #1E1E1E !important;
                border-color: #404040 !important;
            }

            /* Dropdown option - default */
            .Select-option,
            div[class*="option"] {
                background-color: #1E1E1E !important;
                color: #E0E0E0 !important;
            }

            /* Hover option */
            .Select-option.is-focused,
            .Select-option:hover,
            div[class*="option"]:hover {
                background-color: #3A3A3A !important;
                color: #FFFFFF !important;
            }

            /* Selected option */
            .Select-option.is-selected,
            div[class*="option"][aria-selected="true"] {
                background-color: #64B5F6 !important;
                color: #121212 !important;
            }

            /* Selected value label */
            .Select-value-label,
            div[class*="singleValue"],
            div[class*="multiValue"] {
                color: #E0E0E0 !important;
            }

            /* Placeholder */
            .Select-placeholder,
            div[class*="placeholder"] {
                color: #808080 !important;
            }

            /* Input */
            .Select-input > input,
            input[class*="input"] {
                color: #E0E0E0 !important;
            }

            /* Checklist */
            .checklist-items label {
                color: #E0E0E0 !important;
            }

            .checklist-items input[type="checkbox"]:checked + label {
                color: #64B5F6 !important;
            }

            /* Card */
            .card {
                background-color: #1E1E1E !important;
                border-color: #404040 !important;
            }

            .card-header {
                background-color: #2A2A2A !important;
                color: #E0E0E0 !important;
                border-bottom: 1px solid #404040 !important;
            }

            .card-body {
                background-color: #1E1E1E !important;
                color: #E0E0E0 !important;
            }

            /* Stats card emphasis */
            .stat-card {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border: 1px solid #64B5F6;
            }

            .stat-value {
                color: #64B5F6 !important;
                font-size: 2rem;
                font-weight: bold;
            }

            .stat-label {
                color: #B0B0B0 !important;
                font-size: 0.9rem;
            }

            /* Button */
            .btn {
                border-radius: 8px;
                font-weight: 500;
            }

            .btn-primary {
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%) !important;
                border: none;
            }

            .btn-success {
                background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%) !important;
                border: none;
            }

            /* Scrollbar (QGIS style) */
            ::-webkit-scrollbar {
                width: 10px;
                height: 10px;
            }
            ::-webkit-scrollbar-track {
                background: #1E1E1E;
            }
            ::-webkit-scrollbar-thumb {
                background: #606060;
                border-radius: 5px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #808080;
            }

            /* Table */
            .table {
                color: #E0E0E0 !important;
                background-color: #1E1E1E !important;
            }

            .table thead th {
                background-color: #2A2A2A !important;
                color: #E0E0E0 !important;
                border-color: #404040 !important;
            }

            .table tbody td {
                background-color: #1E1E1E !important;
                border-color: #404040 !important;
            }

            .table tbody tr:hover {
                background-color: #2A2A2A !important;
            }
        </style>
    </head>
    <body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>
'''

# Data loader
data_loader = DataLoader()

# Global data loading
GDF_DONG = None
try:
    GDF_DONG = data_loader.load_dong_geometry()
    print(f"Administrative district boundaries loaded: {len(GDF_DONG)} districts")
except Exception as e:
    print(f"Failed to load administrative district boundaries: {e}")

# ============================================================================
# Layout
# ============================================================================

sidebar = html.Div([
    html.Div([
        html.I(className="fas fa-tree", style={'fontSize': '24px', 'color': '#4CAF50'}),
        html.Span(" Park Analysis", style={'fontSize': '18px', 'fontWeight': '600', 'marginLeft': '10px'})
    ], style={'marginBottom': '30px', 'textAlign': 'center'}),

    html.Div([
        html.Div("Analysis Settings", className="filter-label"),

        # District selection
        html.Label("Region Selection", style={'color': '#B0B0B0', 'fontSize': '13px', 'marginTop': '15px'}),
        dcc.Dropdown(
            id='sigungu-select',
            options=[{'label': s, 'value': s} for s in data_loader.get_sigungu_list()],
            value=['전체'],  # Initial value 'All'
            multi=True,
            className='dark-dropdown'
        ),

        # Buffer distance
        html.Label("Service Range", style={'color': '#B0B0B0', 'fontSize': '13px', 'marginTop': '15px'}),
        dcc.Dropdown(
            id='buffer-distance-select',
            options=[{'label': f'{d}m', 'value': d} for d in BUFFER_DISTANCES],
            value=DEFAULT_BUFFER,
            className='dark-dropdown',
            clearable=False
        ),

        # Map layers
        html.Label("Map Layers", style={'color': '#B0B0B0', 'fontSize': '13px', 'marginTop': '15px'}),
        dcc.Checklist(
            id='map-layers-select',
            options=[
                {'label': ' Administrative Boundary', 'value': 'boundary'},
                {'label': ' Parks', 'value': 'parks'},
                {'label': ' Buffers', 'value': 'buffers'},
                {'label': ' Grid', 'value': 'grid'},
            ],
            value=['boundary'],  # Default: only administrative boundary
            className='checklist-items',
            labelStyle={'display': 'block', 'marginBottom': '8px', 'color': '#E0E0E0'}
        ),

        # Park type selection
        html.Label("Park Type Selection", style={'color': '#B0B0B0', 'fontSize': '13px', 'marginTop': '15px'}),
        dcc.Checklist(
            id='park-type-select',
            options=[{'label': ' All', 'value': '전체'}],  # Initial option
            value=['전체'],  # Default: all selected
            className='checklist-items',
            labelStyle={'display': 'block', 'marginBottom': '8px', 'color': '#E0E0E0'}
        ),
    ], style={'background': '#2b2b2b', 'padding': '20px', 'borderRadius': '8px'}),

    dbc.Button([
        html.I(className="fas fa-sync-alt", style={'marginRight': '8px'}),
        "Refresh"
    ], id='refresh-button', color='success', className='w-100', style={'marginTop': '20px'}),

], style={
    'position': 'fixed', 'top': '0', 'left': '0', 'width': '280px', 'height': '100vh',
    'backgroundColor': '#1e1e1e', 'padding': '30px 20px', 'overflowY': 'auto', 'zIndex': '1000'
})

main_content = html.Div([
    html.Div([
        html.H4("Seoul Park Service Accessibility Analysis", style={'margin': '0', 'color': '#FFFFFF'}),
        html.P("2SFCA (Two-Step Floating Catchment Area) Analysis", style={'margin': '5px 0 0 0', 'color': '#B0B0B0', 'fontSize': '14px'})
    ], style={'marginBottom': '30px'}),

    # Summary statistics cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([html.I(className="fas fa-map-marked-alt", style={'fontSize': '24px', 'color': '#2196F3'})], style={'marginBottom': '10px'}),
                    html.H6("Analysis Areas", className="text-muted", style={'fontSize': '12px'}),
                    html.H3(id='stat-area-count', children="0", className="text-primary", style={'margin': '0'})
                ])
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([html.I(className="fas fa-chart-line", style={'fontSize': '24px', 'color': '#4CAF50'})], style={'marginBottom': '10px'}),
                    html.H6("Average Service Score", className="text-muted", style={'fontSize': '12px'}),
                    html.H3(id='stat-avg-score', children="0.0000", className="text-success", style={'margin': '0'})
                ])
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([html.I(className="fas fa-shield-alt", style={'fontSize': '24px', 'color': '#FF9800'})], style={'marginBottom': '10px'}),
                    html.H6("Coverage", className="text-muted", style={'fontSize': '12px'}),
                    html.H3(id='stat-coverage', children="0.0%", className="text-warning", style={'margin': '0'})
                ])
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([html.I(className="fas fa-balance-scale", style={'fontSize': '24px', 'color': '#9C27B0'})], style={'marginBottom': '10px'}),
                    html.H6("Gini Coefficient", className="text-muted", style={'fontSize': '12px'}),
                    html.H3(id='stat-gini', children="0.000", style={'margin': '0', 'color': '#9C27B0'})
                ])
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=3)
    ], className="mb-4"),

    # Map
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-map", style={'marginRight': '10px'}),
            "Service Accessibility Map"
        ], style={'backgroundColor': '#2b2b2b', 'border': 'none', 'fontSize': '16px', 'fontWeight': '600'}),
        dbc.CardBody([
            # Opacity slider (top placement)
            html.Div([
                html.Label("Administrative District Layer Opacity", style={
                    'fontSize': '12px',
                    'color': '#E0E0E0',
                    'marginBottom': '5px',
                    'display': 'inline-block',
                    'marginRight': '15px'
                }),
                dcc.Slider(
                    id='basemap-opacity-slider',
                    min=0,
                    max=1.0,
                    step=0.05,
                    value=0.8,
                    marks={
                        0: {'label': '0%', 'style': {'color': '#E0E0E0'}},
                        0.25: {'label': '25%', 'style': {'color': '#E0E0E0'}},
                        0.5: {'label': '50%', 'style': {'color': '#E0E0E0'}},
                        0.75: {'label': '75%', 'style': {'color': '#E0E0E0'}},
                        1.0: {'label': '100%', 'style': {'color': '#E0E0E0'}}
                    },
                    tooltip={'placement': 'bottom', 'always_visible': True}
                ),
            ], style={
                'padding': '10px 20px',
                'backgroundColor': '#2b2b2b',
                'borderBottom': '1px solid #3d3d3d'
            }),

            dcc.Loading(
                id="loading-map",
                type="default",
                children=dcc.Graph(
                    id='service-map',
                    config={
                        'displayModeBar': True,
                        'scrollZoom': True,
                        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                    },
                    style={'height': f'{MAP_HEIGHT}px'}
                )
            )
        ], style={'padding': '0'})
    ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}, className="mb-4"),

    # Chart section - Service Beneficiary TOP 10 (side by side)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-bar", style={'marginRight': '10px'}),
                    "Service Beneficiary TOP 10 - Districts"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='top10-sigungu-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-bar", style={'marginRight': '10px'}),
                    "Service Beneficiary TOP 10 - Neighborhoods"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='top10-dong-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=6)
    ], className="mb-4"),

    # Lorenz curve section (side by side)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-area", style={'marginRight': '10px'}),
                    "Lorenz Curve - Districts"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='lorenz-sigungu-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-area", style={'marginRight': '10px'}),
                    "Lorenz Curve - Neighborhoods"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='lorenz-dong-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=6)
    ], className="mb-4"),

    # Park type analysis charts
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-pie", style={'marginRight': '10px'}),
                    "Park Type Distribution"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='park-type-pie-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-pie", style={'marginRight': '10px'}),
                    "Park Type Accessibility Contribution"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='park-type-contribution-pie', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=6)
    ], className="mb-4"),

    # Additional analysis charts (3 charts layout)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-line", style={'marginRight': '10px'}),
                    "Average Accessibility by Buffer"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='buffer-avg-accessibility-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-bar", style={'marginRight': '10px'}),
                    "Gini Coefficient by District"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='sigungu-gini-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-bar", style={'marginRight': '10px'}),
                    "Top/Bottom 5 Neighborhoods Comparison"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='top-bottom-comparison-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=4)
    ], className="mb-4"),

    # Indicator description section
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-book", style={'marginRight': '10px'}),
            "Dashboard Indicators Detailed Description"
        ], style={'backgroundColor': '#2b2b2b', 'border': 'none', 'fontSize': '18px', 'fontWeight': '600'}),
        dbc.CardBody([
            dbc.Accordion([
                # 1. Service Accessibility Score
                dbc.AccordionItem([
                    html.Div([
                        html.H5("Concept and Significance", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.P("The service accessibility score is an indicator that quantitatively measures how well residents of each region (neighborhood or district) can access park services. A higher score means residents can access parks more easily and have a larger park area available per person.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("Calculation Process (2SFCA Methodology)", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P([
                            html.Strong("Step 1: Calculate per capita service capacity for each park"), html.Br(),
                            "R_j = Park_Area_j / Total_Population_within_Buffer_j", html.Br(), html.Br(),
                            "Example: Park A (10,000㎡), population within 500m buffer 5,000 people → R_A = 2.0 (2㎡ per person)"
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8', 'backgroundColor': '#2b2b2b', 'padding': '15px', 'borderRadius': '5px'}),

                        html.P([
                            html.Strong("Step 2: Calculate accessibility score for each population grid"), html.Br(),
                            "Accessibility_Score_i = Σ(R values of all parks accessible from that grid)", html.Br(), html.Br(),
                            "Example: From grid X, can access Park A (R=2.0), Park B (R=1.5) → Accessibility score = 3.5"
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8', 'backgroundColor': '#2b2b2b', 'padding': '15px', 'borderRadius': '5px', 'marginTop': '10px'}),

                        html.H5("Interpretation Standards", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("0~1 points: Very low accessibility - Insufficient parks or overcrowded usage", style={'marginBottom': '8px'}),
                            html.Li("1~3 points: Low accessibility - Park service improvement needed", style={'marginBottom': '8px'}),
                            html.Li("3~5 points: Moderate accessibility - General service level", style={'marginBottom': '8px'}),
                            html.Li("5~10 points: High accessibility - Good service", style={'marginBottom': '8px'}),
                            html.Li("10 points or more: Very high accessibility - Excellent service environment", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'})
                    ])
                ], title="1. Service Accessibility Score"),

                # 2. Gini Coefficient
                dbc.AccordionItem([
                    html.Div([
                        html.H5("Concept and Significance", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.P("The Gini coefficient is an indicator that represents the degree of inequality in park service accessibility between regions as a value between 0 and 1. By applying an indicator originally used to measure income inequality to spatial analysis, it evaluates how equitably park services are distributed throughout Seoul.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("Relationship with Lorenz Curve", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P("The Lorenz curve is a visual representation of the Gini coefficient, with the X-axis representing cumulative population ratio (or number of regions) and the Y-axis representing cumulative service score ratio.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),
                        html.Ul([
                            html.Li("Perfect equality line (45-degree diagonal): Ideal state where all regions receive equal service", style={'marginBottom': '8px'}),
                            html.Li("Lorenz curve: Cumulative distribution of actual service scores. Located below the perfect equality line", style={'marginBottom': '8px'}),
                            html.Li("Gini coefficient = 2 × (Area between perfect equality line and Lorenz curve)", style={'marginBottom': '8px'}),
                            html.Li("The farther the curve is from the perfect equality line, the greater the inequality", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("District vs Neighborhood Comparison", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P([
                            html.Strong("District Lorenz Curve"), ": Distribution of average service scores across 25 autonomous districts. Useful for identifying policy priorities between administrative regions", html.Br(),
                            html.Strong("Neighborhood Lorenz Curve"), ": Detailed service score distribution across 426 neighborhoods. Useful for identifying microscopic gaps within regions"
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8', 'backgroundColor': '#2b2b2b', 'padding': '15px', 'borderRadius': '5px'}),

                        html.H5("Interpretation Standards", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("0.00 ~ 0.20: Very equal - Services evenly distributed", style={'marginBottom': '8px'}),
                            html.Li("0.20 ~ 0.30: Equal - Good distribution", style={'marginBottom': '8px'}),
                            html.Li("0.30 ~ 0.40: Moderate - Some regional gaps exist", style={'marginBottom': '8px'}),
                            html.Li("0.40 ~ 0.50: Unequal - Severe regional gap, policy intervention needed", style={'marginBottom': '8px'}),
                            html.Li("0.50 or more: Very unequal - Extreme imbalance, urgent action needed", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'})
                    ])
                ], title="2. Gini Coefficient"),

                # 3. Coverage Ratio
                dbc.AccordionItem([
                    html.Div([
                        html.H5("Concept and Significance", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.P("The coverage ratio indicates what percentage of the total population within a neighborhood or district resides within park service range. While accessibility score measures 'how good the service received is', coverage ratio measures 'how many people receive service'.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("Calculation Formula", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P("Coverage_Ratio = (Population_within_Service_Range / Total_Population) × 100", style={'color': '#E0E0E0', 'backgroundColor': '#2b2b2b', 'padding': '15px', 'borderRadius': '5px'}),

                        html.H5("Buffer Distance Settings", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("100m: 1-2 minute walk - Accessibility for children/elderly (strict standard)", style={'marginBottom': '8px'}),
                            html.Li("300m: 3-5 minute walk - Neighborhood park standard", style={'marginBottom': '8px'}),
                            html.Li("500m: 5-7 minute walk - Legal standard for urban parks (recommended)", style={'marginBottom': '8px'}),
                            html.Li("1000m: 10-15 minute walk - Large park accessibility", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.P("As buffer distance increases, coverage ratio increases, but actual usability decreases.", style={'color': '#FF9800', 'fontStyle': 'italic', 'marginTop': '15px'})
                    ])
                ], title="3. Coverage Ratio"),

                # 4. Park Type Analysis
                dbc.AccordionItem([
                    html.Div([
                        html.H5("Park Type Classification (Urban Park Act Standards)", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.Ul([
                            html.Li("Children's Park: Small-scale, neighborhood living area, focused on play facilities (average 1,500㎡, within 250m)", style={'marginBottom': '8px'}),
                            html.Li("Neighborhood Park: Medium-scale, daily rest and exercise (average 10,000㎡, within 500m)", style={'marginBottom': '8px'}),
                            html.Li("Urban Natural Park: Large-scale forest type, nature conservation (average 100,000㎡, 1000m+)", style={'marginBottom': '8px'}),
                            html.Li("Cultural Park: Focused on culture and historical facilities", style={'marginBottom': '8px'}),
                            html.Li("Sports Park: Focused on sports facilities (average 50,000㎡, 1000m)", style={'marginBottom': '8px'}),
                            html.Li("Other Parks: Special purpose parks (cemetery parks, small parks, etc.)", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("3% Grouping Rule", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P("For readability, the dashboard consolidates types that account for less than 3% of total parks into 'Other'.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("Interpretation Method", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("High proportion of children's parks: New towns, residential areas - Family-friendly environment", style={'marginBottom': '8px'}),
                            html.Li("High proportion of urban natural parks: Mountain-adjacent areas - Large green space", style={'marginBottom': '8px'}),
                            html.Li("Concentration in specific type: Lack of park service diversity - Need to supplement other types", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'})
                    ])
                ], title="4. Park Type Analysis"),

                # 5. Administrative District Layer Opacity
                dbc.AccordionItem([
                    html.Div([
                        html.H5("Concept and Significance", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.P("Administrative district layer opacity adjusts the opacity of the choropleth map (administrative district boundaries expressed in color) to determine how much of the underlying OpenStreetMap base map to show.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("Usage Scenarios", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("100% opacity: Focus only on service score colors", style={'marginBottom': '8px'}),
                            html.Li("80% opacity (default): Balanced view of colors and base map", style={'marginBottom': '8px'}),
                            html.Li("50% opacity: Emphasize spatial context such as road network, buildings", style={'marginBottom': '8px'}),
                            html.Li("0% opacity (completely transparent): Only base map visible, check only park locations, buffers and other layers", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("Recommended Settings", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("Policy reports: 80~100% (clearly express colors)", style={'marginBottom': '8px'}),
                            html.Li("Field surveys: 50~70% (need to check roads, terrain)", style={'marginBottom': '8px'}),
                            html.Li("Education/presentations: 70~90% (visual balance)", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'})
                    ])
                ], title="5. Administrative District Layer Opacity Control"),

            ], start_collapsed=True, flush=True, style={'backgroundColor': '#2b2b2b'})
        ], style={'padding': '20px', 'backgroundColor': '#2b2b2b'})
    ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}, className="mb-4"),

    dcc.Store(id='analysis-data-store'),

], style={'marginLeft': '300px', 'padding': '30px', 'backgroundColor': '#1e1e1e', 'minHeight': '100vh'})

app.layout = html.Div([sidebar, main_content], style={'backgroundColor': '#1e1e1e'})

# ============================================================================
# Callbacks
# ============================================================================

@app.callback(
    [Output('park-type-select', 'options'),
     Output('park-type-select', 'value')],
    [Input('sigungu-select', 'value')],
    prevent_initial_call=False  # Allow initial call
)
def load_park_type_options(sigungu_list):
    try:
        # Load park data
        gdf_parks = data_loader.load_parks()

        # District filtering
        if sigungu_list and '전체' not in sigungu_list:
            gdf_dong = data_loader.load_dong_geometry()
            gdf_filtered_dong = data_loader.filter_by_sigungu(gdf_dong, sigungu_list)
            gdf_parks = data_loader.spatial_filter_parks(gdf_parks, gdf_filtered_dong, predicate='intersects')

        # Extract park types (text before parentheses from LABEL column)
        gdf_parks['park_type'] = gdf_parks['LABEL'].str.extract(r'^([^(]+)')[0]
        park_types = sorted(gdf_parks['park_type'].unique().tolist())

        # Create options (add 'All')
        options = [{'label': ' All', 'value': '전체'}] + [{'label': f' {pt}', 'value': pt} for pt in park_types]

        # Default: all selected
        return options, ['전체']
    except Exception as e:
        print(f"Error loading park types: {e}")
        return [{'label': ' All', 'value': '전체'}], ['전체']


@app.callback(
    Output('analysis-data-store', 'data'),
    [Input('sigungu-select', 'value'),
     Input('buffer-distance-select', 'value'),
     Input('park-type-select', 'value')],
    prevent_initial_call=False  # Allow initial call
)
def update_analysis_data(sigungu_list, buffer_distance, selected_park_types):
    analysis_mode = 'dong'  # Default: neighborhood unit
    try:
        print(f"\n=== update_analysis_data called ===")
        print(f"  buffer_distance: {buffer_distance}")
        print(f"  selected_park_types: {selected_park_types}")
        print(f"  sigungu_list: {sigungu_list}")

        # Load multi-buffer data
        df_multi = data_loader.load_2sfca_multi_buffer()
        print(f"  Data loaded: {len(df_multi)} rows")

        # Buffer distance filtering
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()
        print(f"  After buffer filtering: {len(df_filtered)} rows")

        # Park type filtering
        if selected_park_types and len(selected_park_types) > 0:
            # Handle case where only 'All' is selected, or 'All' and other types are selected together
            specific_types = [pt for pt in selected_park_types if pt != '전체']

            if len(specific_types) > 0:
                # When specific park types are selected (excluding All)
                df_filtered = df_filtered[df_filtered['park_types'].isin(specific_types)].copy()
                print(f"  After filtering selected park types {specific_types}: {len(df_filtered)} rows")

                # Aggregate by neighborhood when multiple types are selected
                if len(specific_types) > 1:
                    grouped = df_filtered.groupby('ADM_NM').agg({
                        'SIGUNGU_NM': 'first',
                        'total_population': 'first',
                        'covered_population': 'sum',  # Sum (total covered population from multiple park types)
                        'coverage_ratio': 'mean',      # Average
                        'avg_service_per_capita': 'mean'  # Average
                    }).reset_index()
                    # Recalculate coverage ratio
                    grouped['coverage_ratio'] = (grouped['covered_population'] / grouped['total_population'] * 100).clip(upper=100)
                    df_filtered = grouped
                    print(f"  After multi-type aggregation: {len(df_filtered)} rows")
            else:
                # When only 'All' is selected
                df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
                print(f"  After filtering park type 'All': {len(df_filtered)} rows")
        else:
            # If not selected, use "All" type
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
            print(f"  After filtering park type 'All': {len(df_filtered)} rows")

        # District filtering
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()
            print(f"  After district filtering: {len(df_filtered)} rows")
        else:
            print(f"  No district filtering (All or None)")

        if analysis_mode == 'sigungu':
            # District-level aggregation
            df_grouped = df_filtered.groupby('SIGUNGU_NM').agg({
                'total_population': 'sum',
                'covered_population': 'sum',
                'avg_service_per_capita': 'mean'  # Simple average (average per neighborhood)
            }).reset_index()
            df_grouped['coverage_ratio'] = (df_grouped['covered_population'] / df_grouped['total_population'] * 100)
            df_filtered = df_grouped.rename(columns={'SIGUNGU_NM': 'area_name'})
        else:
            # Neighborhood
            df_filtered['area_name'] = df_filtered['ADM_NM']

        # Calculate statistics
        avg_score = float(df_filtered['avg_service_per_capita'].mean())
        avg_coverage = float(df_filtered['coverage_ratio'].mean()) if 'coverage_ratio' in df_filtered.columns else 0

        # Gini coefficient
        scores = df_filtered['avg_service_per_capita'].dropna().sort_values().values
        if len(scores) > 0:
            n = len(scores)
            index = np.arange(1, n + 1)
            gini = (2 * np.sum(index * scores)) / (n * np.sum(scores)) - (n + 1) / n
        else:
            gini = 0

        result = {
            'area_count': len(df_filtered),
            'avg_score': avg_score,
            'coverage': avg_coverage,
            'gini': gini,
            'analysis_mode': analysis_mode
        }
        print(f"  Final result: {result}")
        return result
    except Exception as e:
        print(f"Error in update_analysis_data: {e}")
        import traceback
        traceback.print_exc()
        return {'area_count': 0, 'avg_score': 0, 'coverage': 0, 'gini': 0, 'analysis_mode': 'dong'}


@app.callback(
    [Output('stat-area-count', 'children'),
     Output('stat-avg-score', 'children'),
     Output('stat-coverage', 'children'),
     Output('stat-gini', 'children')],
    [Input('analysis-data-store', 'data')]
)
def update_stats(data):
    print(f"\n=== update_stats called ===")
    print(f"  Received data: {data}")

    if not data:
        print("  Data is None, returning default values")
        return "0", "0.0000", "0.0%", "0.000"

    # Handle None values
    area_count = data.get('area_count', 0) or 0
    avg_score = data.get('avg_score', 0) or 0
    coverage = data.get('coverage', 0) or 0
    gini = data.get('gini', 0) or 0

    print(f"  area_count: {area_count}")
    print(f"  avg_score: {avg_score}")
    print(f"  coverage: {coverage}")
    print(f"  gini: {gini}")

    return (
        f"{area_count:,}",
        f"{avg_score:.4f}",
        f"{coverage:.1f}%",
        f"{gini:.3f}"
    )


@app.callback(
    Output('service-map', 'figure'),
    [Input('sigungu-select', 'value'),
     Input('buffer-distance-select', 'value'),
     Input('map-layers-select', 'value'),
     Input('park-type-select', 'value'),
     Input('refresh-button', 'n_clicks'),
     Input('basemap-opacity-slider', 'value')]
)
def update_service_map(sigungu_list, buffer_distance, layers, selected_park_types, n_clicks, basemap_opacity):
    analysis_mode = 'dong'  # Default: neighborhood unit
    try:
        from modules.config import MIN_POPULATION_THRESHOLD

        gdf_merged = data_loader.merge_2sfca_with_geometry()
        gdf_filtered = data_loader.filter_by_sigungu(gdf_merged, sigungu_list)

        if len(gdf_filtered) == 0:
            raise ValueError("No data available for the selected region.")

        # District analysis mode: aggregate by district
        if analysis_mode == 'sigungu':
            import geopandas as gpd
            from modules.config import SIGUNGU_POLYGON_SHP

            # Load district boundary shapefile
            gdf_sigungu = gpd.read_file(SIGUNGU_POLYGON_SHP, encoding='cp949')
            if gdf_sigungu.crs != 'EPSG:4326':
                gdf_sigungu = gdf_sigungu.to_crs('EPSG:4326')

            # Filter Seoul only
            gdf_sigungu['_sido_cd'] = gdf_sigungu['SIGUNGU_CD'].astype(str).str[:2]
            gdf_sigungu = gdf_sigungu[gdf_sigungu['_sido_cd'] == '11'].copy()

            # Check district name column
            sigungu_col = None
            for col in ['SIGUNGU_NM', 'sigungu_nm']:
                if col in gdf_filtered.columns:
                    sigungu_col = col
                    break

            if sigungu_col:
                # District-level aggregation
                gdf_agg = gdf_filtered.groupby(sigungu_col).agg({
                    'total_population': 'sum',
                    'covered_population': 'sum',
                    'avg_service_per_capita': 'mean'
                }).reset_index()
                gdf_agg['coverage_ratio'] = (gdf_agg['covered_population'] / gdf_agg['total_population'] * 100)

                # Merge with district boundaries (add geometry)
                gdf_filtered = gdf_sigungu.merge(
                    gdf_agg,
                    left_on='SIGUNGU_NM',
                    right_on=sigungu_col,
                    how='inner'
                )
                gdf_filtered['ADM_NM'] = gdf_filtered['SIGUNGU_NM']
                gdf_filtered['id'] = gdf_filtered.index.astype(str)

        # Calculate map center and zoom according to selected region (requires EPSG:4326)
        if gdf_filtered.crs != 'EPSG:4326':
            gdf_temp = gdf_filtered.to_crs('EPSG:4326')
        else:
            gdf_temp = gdf_filtered

        bounds = gdf_temp.total_bounds  # [minx, miny, maxx, maxy]
        center_lon = (bounds[0] + bounds[2]) / 2
        center_lat = (bounds[1] + bounds[3]) / 2

        # Auto-adjust zoom level based on boundary range
        lon_range = bounds[2] - bounds[0]
        lat_range = bounds[3] - bounds[1]
        max_range = max(lon_range, lat_range)

        if max_range > 0.5:  # Entire Seoul
            zoom = 10
        elif max_range > 0.2:  # Multiple districts
            zoom = 11
        elif max_range > 0.1:  # One district
            zoom = 12
        else:  # One neighborhood
            zoom = 13

        # Create enhanced service map (discrete colors)
        # If basemap_opacity is None, use default 1.0
        if basemap_opacity is None:
            basemap_opacity = 1.0

        fig = create_service_map_enhanced(
            gdf_filtered,
            column='avg_service_per_capita',
            title=f"Park Service Accessibility ({analysis_mode} unit, Buffer: {buffer_distance}m)",
            use_discrete_colors=False,  # Test with continuous first
            basemap_opacity=basemap_opacity
        )

        # Update map center and zoom
        fig.update_layout(
            map=dict(
                center={'lat': center_lat, 'lon': center_lon},
                zoom=zoom
            )
        )

        # Add district boundaries (entire Seoul districts - thick black line)
        fig = add_sigungu_boundaries(fig, show_labels=True)  # Use default: black, 3.0px

        # Add administrative boundary lines (preserve original geometry)
        if layers and 'boundary' in layers:
            # Display only neighborhood boundaries (v2 method - no geometry simplification)
            fig = add_boundary_lines(fig, gdf_filtered, name="Administrative District Boundary", color='#666666', width=1.0)

        # Park/buffer layers
        if layers and ('parks' in layers or 'buffers' in layers):
            gdf_parks = data_loader.load_parks()
            print(f"[DEBUG] Total parks: {len(gdf_parks)}")

            gdf_parks_filtered = data_loader.spatial_filter_parks(gdf_parks, gdf_filtered, predicate='intersects')
            print(f"[DEBUG] Parks after spatial filtering: {len(gdf_parks_filtered)}")

            # Park type filtering
            if selected_park_types and '전체' not in selected_park_types:
                gdf_parks_filtered['park_type'] = gdf_parks_filtered['LABEL'].str.extract(r'^([^(]+)')[0]
                print(f"[DEBUG] Selected park types: {selected_park_types}")
                print(f"[DEBUG] Parks before type filtering: {len(gdf_parks_filtered)}")
                gdf_parks_filtered = gdf_parks_filtered[gdf_parks_filtered['park_type'].isin(selected_park_types)]
                print(f"[DEBUG] Parks after type filtering: {len(gdf_parks_filtered)}")

            if 'parks' in layers:
                print(f"[DEBUG] Attempting to add park layer: {len(gdf_parks_filtered)} parks")
                if len(gdf_parks_filtered) > 0:
                    # Display as park area (Polygon)
                    fig = add_park_polygons(fig, gdf_parks_filtered, name="Parks", color='#2ecc71', opacity=0.5)
                    print(f"[DEBUG] Park layer added")
                else:
                    print(f"[DEBUG] No park data - skipping layer addition")

            if 'buffers' in layers and len(gdf_parks_filtered) > 0:
                gdf_buffers = data_loader.create_park_buffers(gdf_parks_filtered, buffer_distance=buffer_distance)
                # Display buffers as area (semi-transparent)
                fig = add_park_buffers(fig, gdf_buffers, show_fill=True)

        # Grid layer
        if layers and 'grid' in layers:
            gdf_grid = data_loader.load_grid()
            gdf_grid_filtered = data_loader.spatial_filter_grid(gdf_grid, gdf_filtered, predicate='intersects', min_population=MIN_POPULATION_THRESHOLD)
            fig = add_grid_layer(fig, gdf_grid_filtered)

        return fig
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        fig = go.Figure()
        fig.update_layout(
            map=dict(style='open-street-map', center=MAP_CENTER, zoom=MAP_ZOOM),
            height=MAP_HEIGHT, margin=dict(l=0, r=0, t=40, b=0),
            title=dict(text=f"Error: {str(e)}", x=0.5, xanchor='center'),
            paper_bgcolor='#1e1e1e', plot_bgcolor='#1e1e1e', font=dict(color='#FFFFFF')
        )
        return fig


@app.callback(
    Output('top10-sigungu-chart', 'figure'),
    [Input('sigungu-select', 'value'),
     Input('buffer-distance-select', 'value'),
     Input('park-type-select', 'value')]
)
def update_top10_sigungu_chart(sigungu_list, buffer_distance, selected_park_types):
    """TOP 10 chart by district"""
    try:
        # Load multi-buffer data
        df_multi = data_loader.load_2sfca_multi_buffer()

        # Buffer distance filtering
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # Park type filtering
        if selected_park_types and len(selected_park_types) > 0:
            if '전체' in selected_park_types:
                df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
            else:
                df_filtered = df_filtered[df_filtered['park_types'].isin(selected_park_types)].copy()
                if len(selected_park_types) > 1:
                    df_filtered = df_filtered.groupby('ADM_NM').agg({
                        'SIGUNGU_NM': 'first',
                        'avg_service_per_capita': 'mean'
                    }).reset_index()
        else:
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()

        # District filtering
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        # District-level aggregation
        df_agg = df_filtered.groupby('SIGUNGU_NM').agg({
            'avg_service_per_capita': 'mean'
        }).reset_index()
        df_agg.columns = ['area_name', 'avg_service_per_capita']

        df_sorted = df_agg.nlargest(10, 'avg_service_per_capita')

        # Blues color gradient
        colors = ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6',
                  '#4292c6', '#2171b5', '#08519c', '#08306b', '#041f4a'][:len(df_sorted)]

        fig = go.Figure(go.Bar(
            x=df_sorted['avg_service_per_capita'],
            y=df_sorted['area_name'],
            orientation='h',
            marker=dict(color=colors[::-1])  # Darker color for higher rank
        ))
        fig.update_layout(
            xaxis_title="Average Service Score (m²/person)",
            yaxis_title="",
            height=400,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#2b2b2b',
            font=dict(color='#FFFFFF'),
            margin=dict(l=120, r=20, t=20, b=40),
            yaxis=dict(autorange='reversed')
        )
        return fig
    except Exception as e:
        print(f"Error in top10 sigungu chart: {e}")
        return go.Figure()


@app.callback(
    Output('top10-dong-chart', 'figure'),
    [Input('sigungu-select', 'value'),
     Input('buffer-distance-select', 'value'),
     Input('park-type-select', 'value')]
)
def update_top10_dong_chart(sigungu_list, buffer_distance, selected_park_types):
    """TOP 10 chart by neighborhood"""
    try:
        # Load multi-buffer data
        df_multi = data_loader.load_2sfca_multi_buffer()

        # Buffer distance filtering
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # Park type filtering
        if selected_park_types and len(selected_park_types) > 0:
            if '전체' in selected_park_types:
                df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
            else:
                df_filtered = df_filtered[df_filtered['park_types'].isin(selected_park_types)].copy()
                if len(selected_park_types) > 1:
                    df_filtered = df_filtered.groupby('ADM_NM').agg({
                        'SIGUNGU_NM': 'first',
                        'avg_service_per_capita': 'mean'
                    }).reset_index()
        else:
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()

        # District filtering
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        df_sorted = df_filtered.nlargest(10, 'avg_service_per_capita')[['ADM_NM', 'avg_service_per_capita']]

        # Blues color gradient
        colors = ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6',
                  '#4292c6', '#2171b5', '#08519c', '#08306b', '#041f4a'][:len(df_sorted)]

        fig = go.Figure(go.Bar(
            x=df_sorted['avg_service_per_capita'],
            y=df_sorted['ADM_NM'],
            orientation='h',
            marker=dict(color=colors[::-1])  # Darker color for higher rank
        ))
        fig.update_layout(
            xaxis_title="Average Service Score (m²/person)",
            yaxis_title="",
            height=400,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#2b2b2b',
            font=dict(color='#FFFFFF'),
            margin=dict(l=120, r=20, t=20, b=40),
            yaxis=dict(autorange='reversed')
        )
        return fig
    except Exception as e:
        print(f"Error in top10 dong chart: {e}")
        return go.Figure()


@app.callback(
    Output('lorenz-sigungu-chart', 'figure'),
    [Input('sigungu-select', 'value'),
     Input('buffer-distance-select', 'value'),
     Input('park-type-select', 'value')]
)
def update_lorenz_sigungu_chart(sigungu_list, buffer_distance, selected_park_types):
    """Lorenz curve by district"""
    try:
        # Load multi-buffer data
        df_multi = data_loader.load_2sfca_multi_buffer()

        # Buffer distance filtering
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # Park type filtering
        if selected_park_types and len(selected_park_types) > 0:
            if '전체' in selected_park_types:
                df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
            else:
                df_filtered = df_filtered[df_filtered['park_types'].isin(selected_park_types)].copy()
                if len(selected_park_types) > 1:
                    df_filtered = df_filtered.groupby('ADM_NM').agg({
                        'SIGUNGU_NM': 'first',
                        'avg_service_per_capita': 'mean'
                    }).reset_index()
        else:
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()

        # District filtering
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        # District-level aggregation
        df_agg = df_filtered.groupby('SIGUNGU_NM').agg({
            'avg_service_per_capita': 'mean'
        }).reset_index()
        scores = df_agg['avg_service_per_capita'].dropna().sort_values().values

        n = len(scores)
        if n == 0:
            return go.Figure()
        cum_scores = np.cumsum(scores) / np.sum(scores)
        cum_pop = np.arange(1, n + 1) / n

        # Calculate Gini coefficient
        gini = (2 * np.sum(np.arange(1, n + 1) * scores)) / (n * np.sum(scores)) - (n + 1) / n

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cum_pop, y=cum_scores,
            mode='lines',
            name='Lorenz Curve',
            line=dict(color='#2196F3', width=2),
            fill='tonexty',
            fillcolor='rgba(33, 150, 243, 0.2)'
        ))
        fig.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode='lines',
            name='Perfect Equality Line',
            line=dict(color='#FF9800', dash='dash', width=2)
        ))

        fig.update_layout(
            title=f"Lorenz Curve - Districts (Gini: {gini:.3f})",
            xaxis_title="Cumulative Population Ratio",
            yaxis_title="Cumulative Service Score Ratio",
            height=400,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#2b2b2b',
            font=dict(color='#FFFFFF'),
            margin=dict(l=60, r=20, t=60, b=60),
            xaxis=dict(range=[0, 1]),
            yaxis=dict(range=[0, 1]),
            showlegend=True,
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(0,0,0,0.3)')
        )
        return fig
    except Exception as e:
        print(f"Error in lorenz sigungu chart: {e}")
        return go.Figure()


@app.callback(
    Output('lorenz-dong-chart', 'figure'),
    [Input('sigungu-select', 'value'),
     Input('buffer-distance-select', 'value'),
     Input('park-type-select', 'value')]
)
def update_lorenz_dong_chart(sigungu_list, buffer_distance, selected_park_types):
    """Lorenz curve by neighborhood"""
    try:
        # Load multi-buffer data
        df_multi = data_loader.load_2sfca_multi_buffer()

        # Buffer distance filtering
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # Park type filtering
        if selected_park_types and len(selected_park_types) > 0:
            if '전체' in selected_park_types:
                df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
            else:
                df_filtered = df_filtered[df_filtered['park_types'].isin(selected_park_types)].copy()
                if len(selected_park_types) > 1:
                    df_filtered = df_filtered.groupby('ADM_NM').agg({
                        'SIGUNGU_NM': 'first',
                        'avg_service_per_capita': 'mean'
                    }).reset_index()
        else:
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()

        # District filtering
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        scores = df_filtered['avg_service_per_capita'].dropna().sort_values().values
        n = len(scores)
        if n == 0:
            return go.Figure()
        cum_scores = np.cumsum(scores) / np.sum(scores)
        cum_pop = np.arange(1, n + 1) / n

        # Calculate Gini coefficient
        gini = (2 * np.sum(np.arange(1, n + 1) * scores)) / (n * np.sum(scores)) - (n + 1) / n

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cum_pop, y=cum_scores,
            mode='lines',
            name='Lorenz Curve',
            line=dict(color='#4CAF50', width=2),
            fill='tonexty',
            fillcolor='rgba(76, 175, 80, 0.2)'
        ))
        fig.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode='lines',
            name='Perfect Equality Line',
            line=dict(color='#FF9800', dash='dash', width=2)
        ))

        fig.update_layout(
            title=f"Lorenz Curve - Neighborhoods (Gini: {gini:.3f})",
            xaxis_title="Cumulative Population Ratio",
            yaxis_title="Cumulative Service Score Ratio",
            height=400,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#2b2b2b',
            font=dict(color='#FFFFFF'),
            margin=dict(l=60, r=20, t=60, b=60),
            xaxis=dict(range=[0, 1]),
            yaxis=dict(range=[0, 1]),
            showlegend=True,
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(0,0,0,0.3)')
        )
        return fig
    except Exception as e:
        print(f"Error in lorenz dong chart: {e}")
        return go.Figure()


@app.callback(
    Output('park-type-pie-chart', 'figure'),
    [Input('sigungu-select', 'value')]
)
def update_park_type_pie(sigungu_list):
    try:
        # Load park data
        gdf_parks = data_loader.load_parks()

        # District filtering (based on park location)
        if sigungu_list and '전체' not in sigungu_list:
            # Load neighborhood boundaries
            gdf_dong = data_loader.load_dong_geometry()
            gdf_filtered_dong = data_loader.filter_by_sigungu(gdf_dong, sigungu_list)

            # Filter parks (spatial join)
            gdf_parks = data_loader.spatial_filter_parks(gdf_parks, gdf_filtered_dong, predicate='intersects')

        # Extract park type from LABEL (e.g. "Other Park (Jeongneung)" -> "Other Park")
        gdf_parks['park_type'] = gdf_parks['LABEL'].str.extract(r'^([^(]+)')[0]

        # Count by park type
        type_counts = gdf_parks['park_type'].value_counts()

        # Group types less than 3% as 'Other'
        total = type_counts.sum()
        threshold = total * 0.03

        type_counts_grouped = {}
        other_count = 0

        for park_type, count in type_counts.items():
            if count >= threshold:
                type_counts_grouped[park_type] = count
            else:
                other_count += count

        if other_count > 0:
            type_counts_grouped['Other'] = other_count

        # Create pie chart (apply QGIS colors)
        from modules.config import PARK_TYPE_COLORS

        fig = go.Figure(data=[go.Pie(
            labels=list(type_counts_grouped.keys()),
            values=list(type_counts_grouped.values()),
            hole=0.3,  # Donut chart
            marker=dict(
                colors=PARK_TYPE_COLORS,
                line=dict(color='#1e1e1e', width=2)
            ),
            textinfo='label+percent',
            textposition='auto',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Ratio: %{percent}<extra></extra>'
        )])

        fig.update_layout(
            title=f"Park Type Distribution (Total {total})",
            height=400,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#1e1e1e',
            font=dict(color='#FFFFFF', size=12),
            margin=dict(l=20, r=20, t=60, b=20),
            showlegend=True,
            legend=dict(
                orientation='v',
                yanchor='middle',
                y=0.5,
                xanchor='left',
                x=1.02,
                font=dict(size=11)
            )
        )

        return fig
    except Exception as e:
        print(f"Error in park type pie chart: {e}")
        import traceback
        traceback.print_exc()
        return go.Figure()


@app.callback(
    Output('park-type-contribution-pie', 'figure'),
    [Input('sigungu-select', 'value')]
)
def update_park_type_contribution(sigungu_list):
    """Park type accessibility contribution pie chart"""
    print(f"[DEBUG] update_park_type_contribution called with sigungu_list: {sigungu_list}")
    try:
        # Load multi-buffer data
        df_multi = data_loader.load_2sfca_multi_buffer()
        print(f"[DEBUG] df_multi loaded: {len(df_multi)} rows")

        # District filtering
        if sigungu_list and '전체' not in sigungu_list:
            df_multi = df_multi[df_multi['SIGUNGU_NM'].isin(sigungu_list)]

        # 500m buffer, park type data excluding All
        df_500m_types = df_multi[
            (df_multi['buffer_distance'] == 500) &
            (df_multi['park_types'] != '전체')
        ].copy()

        if len(df_500m_types) == 0:
            return go.Figure()

        # Calculate average service score by park type
        type_service_scores = df_500m_types.groupby('park_types').agg({
            'avg_service_per_capita': 'mean'
        }).reset_index()

        # Calculate accessibility contribution (ratio to total)
        type_service_scores['contribution_ratio'] = (
            type_service_scores['avg_service_per_capita'] /
            type_service_scores['avg_service_per_capita'].sum() * 100
        )

        # Sort
        type_service_scores = type_service_scores.sort_values('contribution_ratio', ascending=False)

        # Group types less than 3% as 'Other'
        threshold = 3.0
        large_contrib = type_service_scores[type_service_scores['contribution_ratio'] >= threshold]
        small_contrib = type_service_scores[type_service_scores['contribution_ratio'] < threshold]

        labels = large_contrib['park_types'].tolist()
        values = large_contrib['contribution_ratio'].tolist()

        if len(small_contrib) > 0:
            other_contribution = small_contrib['contribution_ratio'].sum()
            labels.append(f'Other ({len(small_contrib)} types)')
            values.append(other_contribution)

        # Color settings (use Spectral colormap - same as Jupyter)
        import plotly.express as px
        # Spectral is a diverging colormap
        colors_spectral = px.colors.diverging.Spectral
        # Adjust color range
        n_colors = len(labels)
        if n_colors <= len(colors_spectral):
            colors = colors_spectral[:n_colors]
        else:
            # Repeat colors if insufficient
            colors = [colors_spectral[i % len(colors_spectral)] for i in range(n_colors)]

        # Create pie chart
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.7,  # Donut chart (Jupyter: 0.70)
            marker=dict(
                colors=colors,
                line=dict(color='#1e1e1e', width=2)
            ),
            textinfo='label+percent',
            textposition='auto',
            textfont=dict(size=10, color='black'),
            hovertemplate='<b>%{label}</b><br>Accessibility Contribution: %{value:.1f}%<extra></extra>',
            pull=[0.05 if i == 0 else 0 for i in range(len(labels))]  # Emphasize maximum contribution item
        )])

        total_types = len(type_service_scores)

        fig.update_layout(
            title=dict(
                text="Park Type Accessibility Contribution (500m Buffer Standard)",
                font=dict(size=14, color='#FFFFFF')
            ),
            height=400,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#1e1e1e',
            font=dict(color='#FFFFFF', size=10),
            margin=dict(l=20, r=20, t=60, b=20),
            showlegend=True,
            legend=dict(
                orientation='v',
                yanchor='middle',
                y=0.5,
                xanchor='left',
                x=1.02,
                font=dict(size=10)
            ),
            annotations=[dict(
                text=f'Total {total_types}<br>Park Types',
                x=0.5, y=0.5,
                font=dict(size=12, color='#FFFFFF'),
                showarrow=False
            )]
        )

        return fig
    except Exception as e:
        print(f"Error in park type contribution pie chart: {e}")
        import traceback
        traceback.print_exc()
        return go.Figure()


@app.callback(
    Output('park-type-bar-chart', 'figure'),
    [Input('sigungu-select', 'value')]
)
def update_park_type_bar(sigungu_list):
    try:
        # Load park data
        gdf_parks = data_loader.load_parks()

        # District filtering
        if sigungu_list and '전체' not in sigungu_list:
            gdf_dong = data_loader.load_dong_geometry()
            gdf_filtered_dong = data_loader.filter_by_sigungu(gdf_dong, sigungu_list)
            gdf_parks = data_loader.spatial_filter_parks(gdf_parks, gdf_filtered_dong, predicate='intersects')

        # Extract park type (text before parentheses from LABEL column)
        gdf_parks['park_type'] = gdf_parks['LABEL'].str.extract(r'^([^(]+)')[0]

        # Count by park type
        type_counts = gdf_parks['park_type'].value_counts()

        # Group types less than 3% as 'Other'
        total = type_counts.sum()
        threshold = total * 0.03

        type_counts_grouped = {}
        other_count = 0

        for park_type, count in type_counts.items():
            if count >= threshold:
                type_counts_grouped[park_type] = count
            else:
                other_count += count

        if other_count > 0:
            type_counts_grouped['Other'] = other_count

        # Sort in descending order
        sorted_types = sorted(type_counts_grouped.items(), key=lambda x: x[1], reverse=True)
        labels = [item[0] for item in sorted_types]
        values = [item[1] for item in sorted_types]

        # Create bar chart (apply QGIS colors)
        from modules.config import PARK_TYPE_COLORS

        # Assign color to each bar
        bar_colors = [PARK_TYPE_COLORS[i % len(PARK_TYPE_COLORS)] for i in range(len(labels))]

        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker=dict(
                color=bar_colors,
                line=dict(color='#1e1e1e', width=1.5)
            ),
            text=values,
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Count: %{y}<br>Ratio: %{customdata:.1f}%<extra></extra>',
            customdata=[v/total*100 for v in values]
        )])

        fig.update_layout(
            title=f"Park Count by Type (Total {total})",
            xaxis_title="Park Type",
            yaxis_title="Count",
            height=400,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#2b2b2b',
            font=dict(color='#FFFFFF'),
            margin=dict(l=50, r=20, t=60, b=100),
            xaxis=dict(
                tickangle=-45,
                gridcolor='#3d3d3d'
            ),
            yaxis=dict(
                gridcolor='#3d3d3d'
            )
        )

        return fig
    except Exception as e:
        print(f"Error in park type bar chart: {e}")
        import traceback
        traceback.print_exc()
        return go.Figure()


# ========== 3 New Analysis Chart Callbacks ==========

@app.callback(
    Output('buffer-avg-accessibility-chart', 'figure'),
    [Input('sigungu-select', 'value'),
     Input('park-type-select', 'value')]
)
def update_buffer_avg_accessibility_chart(sigungu_list, selected_park_types):
    """Average accessibility change by buffer"""
    try:
        df_multi = data_loader.load_2sfca_multi_buffer()

        # Park type filtering
        if selected_park_types and len(selected_park_types) > 0:
            if '전체' in selected_park_types:
                df_filtered = df_multi[df_multi['park_types'] == '전체'].copy()
            else:
                df_filtered = df_multi[df_multi['park_types'].isin(selected_park_types)].copy()
        else:
            df_filtered = df_multi[df_multi['park_types'] == '전체'].copy()

        # District filtering
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        # Calculate average by buffer
        buffer_stats = []
        for buffer in [100, 300, 500, 1000]:
            df_buffer = df_filtered[df_filtered['buffer_distance'] == buffer]
            if len(df_buffer) > 0:
                avg_score = df_buffer['avg_service_per_capita'].mean()
                buffer_stats.append({
                    'buffer': buffer,
                    'avg_score': avg_score
                })

        df_stats = pd.DataFrame(buffer_stats)

        # Create line chart
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_stats['buffer'],
            y=df_stats['avg_score'],
            mode='lines+markers',
            line=dict(color='#64B5F6', width=3),
            marker=dict(size=12, color='#64B5F6'),
            text=df_stats['avg_score'].round(2),
            textposition='top center',
            textfont=dict(color='#FFFFFF', size=11),
            hovertemplate='<b>%{x}m</b><br>Average Score: %{y:.2f} m²/person<extra></extra>'
        ))

        fig.update_layout(
            xaxis_title="Buffer Distance (m)",
            yaxis_title="Average Accessibility (m²/person)",
            height=350,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#2b2b2b',
            font=dict(color='#FFFFFF'),
            margin=dict(l=60, r=20, t=20, b=50),
            yaxis=dict(gridcolor='#3d3d3d'),
            xaxis=dict(gridcolor='#3d3d3d'),
            showlegend=False
        )

        return fig
    except Exception as e:
        print(f"Error in buffer avg accessibility chart: {e}")
        import traceback
        traceback.print_exc()
        return go.Figure()


@app.callback(
    Output('sigungu-gini-chart', 'figure'),
    [Input('buffer-distance-select', 'value'),
     Input('park-type-select', 'value')]
)
def update_sigungu_gini_chart(buffer_distance, selected_park_types):
    """Gini coefficient comparison by district"""
    try:
        df_multi = data_loader.load_2sfca_multi_buffer()

        # Buffer and park type filtering
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()
        if selected_park_types and len(selected_park_types) > 0 and '전체' in selected_park_types:
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
        else:
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()

        # Calculate Gini coefficient by district
        gini_results = []
        for sigungu in df_filtered['SIGUNGU_NM'].unique():
            df_sigungu = df_filtered[df_filtered['SIGUNGU_NM'] == sigungu]
            scores = df_sigungu['avg_service_per_capita'].dropna().sort_values().values

            if len(scores) > 1:
                n = len(scores)
                gini = (2 * np.sum(np.arange(1, n + 1) * scores)) / (n * np.sum(scores)) - (n + 1) / n
                gini_results.append({'sigungu': sigungu, 'gini': gini})

        df_gini = pd.DataFrame(gini_results).nlargest(10, 'gini')

        # Create bar chart
        fig = go.Figure(data=[go.Bar(
            x=df_gini['sigungu'],
            y=df_gini['gini'],
            marker=dict(
                color=df_gini['gini'],
                colorscale='Reds',
                showscale=False
            ),
            text=df_gini['gini'].round(3),
            textposition='outside',
            textfont=dict(color='#FFFFFF', size=10),
            hovertemplate='<b>%{x}</b><br>Gini Coefficient: %{y:.3f}<extra></extra>'
        )])

        fig.update_layout(
            xaxis_title="",
            yaxis_title="Gini Coefficient (Inequality)",
            height=350,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#2b2b2b',
            font=dict(color='#FFFFFF'),
            margin=dict(l=60, r=20, t=20, b=80),
            xaxis=dict(gridcolor='#3d3d3d', tickangle=-45),
            yaxis=dict(gridcolor='#3d3d3d', range=[0, 1]),
            showlegend=False
        )

        return fig
    except Exception as e:
        print(f"Error in sigungu gini chart: {e}")
        import traceback
        traceback.print_exc()
        return go.Figure()


@app.callback(
    Output('top-bottom-comparison-chart', 'figure'),
    [Input('sigungu-select', 'value'),
     Input('buffer-distance-select', 'value'),
     Input('park-type-select', 'value')]
)
def update_top_bottom_comparison_chart(sigungu_list, buffer_distance, selected_park_types):
    """Top/Bottom 5 neighborhoods comparison"""
    try:
        df_multi = data_loader.load_2sfca_multi_buffer()

        # Buffer filtering
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # Park type filtering
        if selected_park_types and len(selected_park_types) > 0:
            specific_types = [pt for pt in selected_park_types if pt != '전체']
            if len(specific_types) > 0:
                df_filtered = df_filtered[df_filtered['park_types'].isin(specific_types)].copy()
                if len(specific_types) > 1:
                    grouped = df_filtered.groupby('ADM_NM').agg({
                        'SIGUNGU_NM': 'first',
                        'avg_service_per_capita': 'mean'
                    }).reset_index()
                    df_filtered = grouped
            else:
                df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
        else:
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()

        # District filtering
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        # Select top 5 and bottom 5
        top5 = df_filtered.nlargest(5, 'avg_service_per_capita')[['ADM_NM', 'avg_service_per_capita']].copy()
        bottom5 = df_filtered.nsmallest(5, 'avg_service_per_capita')[['ADM_NM', 'avg_service_per_capita']].copy()

        # Sort in reverse order (top to the top)
        top5 = top5.sort_values('avg_service_per_capita', ascending=True)
        bottom5 = bottom5.sort_values('avg_service_per_capita', ascending=True)

        # Create bar chart
        fig = go.Figure()

        # Bottom 5 (red)
        fig.add_trace(go.Bar(
            x=bottom5['avg_service_per_capita'],
            y=bottom5['ADM_NM'],
            orientation='h',
            name='Bottom 5',
            marker=dict(color='#EF5350'),
            text=bottom5['avg_service_per_capita'].round(2),
            textposition='outside',
            textfont=dict(color='#FFFFFF', size=10),
            hovertemplate='<b>%{y}</b><br>Accessibility: %{x:.2f} m²/person<extra></extra>'
        ))

        # Top 5 (blue)
        fig.add_trace(go.Bar(
            x=top5['avg_service_per_capita'],
            y=top5['ADM_NM'],
            orientation='h',
            name='Top 5',
            marker=dict(color='#42A5F5'),
            text=top5['avg_service_per_capita'].round(2),
            textposition='outside',
            textfont=dict(color='#FFFFFF', size=10),
            hovertemplate='<b>%{y}</b><br>Accessibility: %{x:.2f} m²/person<extra></extra>'
        ))

        fig.update_layout(
            title='<b>Top/Bottom 5 Neighborhoods Comparison</b>',
            xaxis_title="Service Score (m²/person)",
            yaxis_title="",
            height=400,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#2b2b2b',
            font=dict(color='#FFFFFF'),
            margin=dict(l=120, r=20, t=50, b=50),
            xaxis=dict(gridcolor='#3d3d3d'),
            yaxis=dict(gridcolor='#3d3d3d'),
            showlegend=True,
            legend=dict(x=0.7, y=0.98, bgcolor='rgba(0,0,0,0.3)', font=dict(size=11)),
            barmode='group'
        )

        return fig
    except Exception as e:
        print(f"Error in top-bottom comparison chart: {e}")
        import traceback
        traceback.print_exc()
        return go.Figure()


if __name__ == '__main__':
    print("Seoul Park Service Analysis Dashboard Started")
    print("Access at http://127.0.0.1:8051")
    print("From other devices on the same network, access at http://<서버IP>:8051")
    app.run(debug=True, host='0.0.0.0', port=8051)
