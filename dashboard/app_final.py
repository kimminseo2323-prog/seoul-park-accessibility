"""
서울시 공원 서비스 분석 대시보드 (완전판)
- QGIS 04.BI 스타일 UI
- s2_module의 모든 분석 기능 포함
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

# 프로젝트 경로 설정
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

# Dash 앱 초기화
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True
)

app.title = "서울시 공원 서비스 분석"

# 다크모드 CSS 스타일
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* ========== QGIS 다크모드 스타일 ========== */

            /* 전체 배경 */
            body {
                background-color: #121212 !important;
                color: #E0E0E0 !important;
            }

            /* 드롭다운 컨트롤 */
            .Select-control,
            div[class*="control"] {
                background-color: #1E1E1E !important;
                border-color: #404040 !important;
                color: #E0E0E0 !important;
            }

            /* 드롭다운 메뉴 */
            .Select-menu-outer,
            .Select-menu,
            div[class*="menu"] {
                background-color: #1E1E1E !important;
                border-color: #404040 !important;
            }

            /* 드롭다운 옵션 - 기본 */
            .Select-option,
            div[class*="option"] {
                background-color: #1E1E1E !important;
                color: #E0E0E0 !important;
            }

            /* Hover 옵션 */
            .Select-option.is-focused,
            .Select-option:hover,
            div[class*="option"]:hover {
                background-color: #3A3A3A !important;
                color: #FFFFFF !important;
            }

            /* 선택된 옵션 */
            .Select-option.is-selected,
            div[class*="option"][aria-selected="true"] {
                background-color: #64B5F6 !important;
                color: #121212 !important;
            }

            /* 선택된 값 레이블 */
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

            /* 카드 */
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

            /* 통계 카드 강조 */
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

            /* 버튼 */
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

            /* 스크롤바 (QGIS 스타일) */
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

            /* 테이블 */
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

# 데이터 로더
data_loader = DataLoader()

# 전역 데이터 로드
GDF_DONG = None
try:
    GDF_DONG = data_loader.load_dong_geometry()
    print(f"행정동 경계 로드: {len(GDF_DONG)}개")
except Exception as e:
    print(f"행정동 경계 로드 실패: {e}")

# ============================================================================
# 레이아웃
# ============================================================================

sidebar = html.Div([
    html.Div([
        html.I(className="fas fa-tree", style={'fontSize': '24px', 'color': '#4CAF50'}),
        html.Span(" 공원 분석", style={'fontSize': '18px', 'fontWeight': '600', 'marginLeft': '10px'})
    ], style={'marginBottom': '30px', 'textAlign': 'center'}),

    html.Div([
        html.Div("분석 설정", className="filter-label"),

        # 시군구 선택
        html.Label("지역 선택", style={'color': '#B0B0B0', 'fontSize': '13px', 'marginTop': '15px'}),
        dcc.Dropdown(
            id='sigungu-select',
            options=[{'label': s, 'value': s} for s in data_loader.get_sigungu_list()],
            value=['전체'],  # 초기값 '전체'
            multi=True,
            className='dark-dropdown'
        ),

        # 버퍼 거리
        html.Label("서비스 범위", style={'color': '#B0B0B0', 'fontSize': '13px', 'marginTop': '15px'}),
        dcc.Dropdown(
            id='buffer-distance-select',
            options=[{'label': f'{d}m', 'value': d} for d in BUFFER_DISTANCES],
            value=DEFAULT_BUFFER,
            className='dark-dropdown',
            clearable=False
        ),

        # 지도 레이어
        html.Label("지도 레이어", style={'color': '#B0B0B0', 'fontSize': '13px', 'marginTop': '15px'}),
        dcc.Checklist(
            id='map-layers-select',
            options=[
                {'label': ' 행정구역', 'value': 'boundary'},
                {'label': ' 공원', 'value': 'parks'},
                {'label': ' 버퍼', 'value': 'buffers'},
                {'label': ' 격자', 'value': 'grid'},
            ],
            value=['boundary'],  # v2처럼 기본값은 행정구역만 표시
            className='checklist-items',
            labelStyle={'display': 'block', 'marginBottom': '8px', 'color': '#E0E0E0'}
        ),

        # 공원 유형 선택
        html.Label("공원 유형 선택", style={'color': '#B0B0B0', 'fontSize': '13px', 'marginTop': '15px'}),
        dcc.Checklist(
            id='park-type-select',
            options=[{'label': ' 전체', 'value': '전체'}],  # 초기 옵션
            value=['전체'],  # 기본값: 전체 선택
            className='checklist-items',
            labelStyle={'display': 'block', 'marginBottom': '8px', 'color': '#E0E0E0'}
        ),
    ], style={'background': '#2b2b2b', 'padding': '20px', 'borderRadius': '8px'}),

    dbc.Button([
        html.I(className="fas fa-sync-alt", style={'marginRight': '8px'}),
        "새로고침"
    ], id='refresh-button', color='success', className='w-100', style={'marginTop': '20px'}),

], style={
    'position': 'fixed', 'top': '0', 'left': '0', 'width': '280px', 'height': '100vh',
    'backgroundColor': '#1e1e1e', 'padding': '30px 20px', 'overflowY': 'auto', 'zIndex': '1000'
})

main_content = html.Div([
    html.Div([
        html.H4("서울시 공원 서비스 접근성 분석", style={'margin': '0', 'color': '#FFFFFF'}),
        html.P("2SFCA(Two-Step Floating Catchment Area) 분석", style={'margin': '5px 0 0 0', 'color': '#B0B0B0', 'fontSize': '14px'})
    ], style={'marginBottom': '30px'}),

    # 요약 통계 카드
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([html.I(className="fas fa-map-marked-alt", style={'fontSize': '24px', 'color': '#2196F3'})], style={'marginBottom': '10px'}),
                    html.H6("분석 지역", className="text-muted", style={'fontSize': '12px'}),
                    html.H3(id='stat-area-count', children="0", className="text-primary", style={'margin': '0'})
                ])
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([html.I(className="fas fa-chart-line", style={'fontSize': '24px', 'color': '#4CAF50'})], style={'marginBottom': '10px'}),
                    html.H6("평균 서비스 점수", className="text-muted", style={'fontSize': '12px'}),
                    html.H3(id='stat-avg-score', children="0.0000", className="text-success", style={'margin': '0'})
                ])
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([html.I(className="fas fa-shield-alt", style={'fontSize': '24px', 'color': '#FF9800'})], style={'marginBottom': '10px'}),
                    html.H6("커버리지", className="text-muted", style={'fontSize': '12px'}),
                    html.H3(id='stat-coverage', children="0.0%", className="text-warning", style={'margin': '0'})
                ])
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([html.I(className="fas fa-balance-scale", style={'fontSize': '24px', 'color': '#9C27B0'})], style={'marginBottom': '10px'}),
                    html.H6("Gini 계수", className="text-muted", style={'fontSize': '12px'}),
                    html.H3(id='stat-gini', children="0.000", style={'margin': '0', 'color': '#9C27B0'})
                ])
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=3)
    ], className="mb-4"),

    # 지도
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-map", style={'marginRight': '10px'}),
            "서비스 접근성 지도"
        ], style={'backgroundColor': '#2b2b2b', 'border': 'none', 'fontSize': '16px', 'fontWeight': '600'}),
        dbc.CardBody([
            # 투명도 슬라이더 (상단 배치)
            html.Div([
                html.Label("행정동 레이어 투명도", style={
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

    # 차트 섹션 - 서비스 수혜도 TOP 10 (좌우 배치)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-bar", style={'marginRight': '10px'}),
                    "서비스 수혜도 TOP 10 - 시군구"
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
                    "서비스 수혜도 TOP 10 - 행정동"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='top10-dong-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=6)
    ], className="mb-4"),

    # 로렌츠 곡선 섹션 (좌우 배치)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-area", style={'marginRight': '10px'}),
                    "로렌츠 곡선 - 시군구"
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
                    "로렌츠 곡선 - 행정동"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='lorenz-dong-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=6)
    ], className="mb-4"),

    # 공원 유형별 분석 차트
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-pie", style={'marginRight': '10px'}),
                    "공원 유형별 분포"
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
                    "공원 유형별 접근성 기여도"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='park-type-contribution-pie', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=6)
    ], className="mb-4"),

    # 추가 분석 차트 (3개 차트 배치)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-line", style={'marginRight': '10px'}),
                    "버퍼별 평균 접근성 변화"
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
                    "시군구별 지니계수 비교"
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
                    "상위/하위 5개 동 비교"
                ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}),
                dbc.CardBody([
                    dcc.Graph(id='top-bottom-comparison-chart', config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'backgroundColor': '#2b2b2b', 'border': 'none'})
        ], md=4)
    ], className="mb-4"),

    # 지표 설명 섹션
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-book", style={'marginRight': '10px'}),
            "대시보드 지표 상세 설명"
        ], style={'backgroundColor': '#2b2b2b', 'border': 'none', 'fontSize': '18px', 'fontWeight': '600'}),
        dbc.CardBody([
            dbc.Accordion([
                # 1. 서비스 접근성 점수
                dbc.AccordionItem([
                    html.Div([
                        html.H5("개념 및 의의", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.P("서비스 접근성 점수는 각 지역(행정동 또는 시군구)의 주민들이 공원 서비스를 얼마나 잘 이용할 수 있는지를 정량적으로 측정한 지표입니다. 이 점수가 높을수록 해당 지역 주민들이 공원에 더 쉽게 접근할 수 있으며, 1인당 이용 가능한 공원 면적이 크다는 것을 의미합니다.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("계산 과정 (2SFCA 방법론)", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P([
                            html.Strong("Step 1: 각 공원의 1인당 서비스 용량 계산"), html.Br(),
                            "R_j = 공원_면적_j / 버퍼_내_총인구_j", html.Br(), html.Br(),
                            "예시: 공원 A(10,000㎡), 500m 버퍼 내 인구 5,000명 → R_A = 2.0 (1인당 2㎡)"
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8', 'backgroundColor': '#2b2b2b', 'padding': '15px', 'borderRadius': '5px'}),

                        html.P([
                            html.Strong("Step 2: 각 인구 격자의 접근성 점수 계산"), html.Br(),
                            "접근성_점수_i = Σ(해당_격자에서_접근가능한_모든_공원의_R값)", html.Br(), html.Br(),
                            "예시: 격자 X에서 공원 A(R=2.0), 공원 B(R=1.5) 접근 가능 → 접근성 점수 = 3.5"
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8', 'backgroundColor': '#2b2b2b', 'padding': '15px', 'borderRadius': '5px', 'marginTop': '10px'}),

                        html.H5("해석 기준", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("0~1점: 매우 낮은 접근성 - 공원 부족 또는 과밀 이용 상태", style={'marginBottom': '8px'}),
                            html.Li("1~3점: 낮은 접근성 - 공원 서비스 개선 필요", style={'marginBottom': '8px'}),
                            html.Li("3~5점: 보통 접근성 - 일반적인 서비스 수준", style={'marginBottom': '8px'}),
                            html.Li("5~10점: 높은 접근성 - 양호한 서비스", style={'marginBottom': '8px'}),
                            html.Li("10점 이상: 매우 높은 접근성 - 우수한 서비스 환경", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'})
                    ])
                ], title="1. 서비스 접근성 점수 (Service Accessibility Score)"),

                # 2. 지니 계수
                dbc.AccordionItem([
                    html.Div([
                        html.H5("개념 및 의의", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.P("지니 계수는 공원 서비스 접근성의 지역 간 불평등 정도를 0~1 사이의 값으로 나타낸 지표입니다. 원래 소득 불평등 측정에 사용되던 지표를 공간 분석에 적용하여, 서울시 전역의 공원 서비스가 얼마나 공평하게 분포되어 있는지를 평가합니다.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("로렌츠 곡선과의 관계", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P("로렌츠 곡선은 지니 계수를 시각적으로 표현한 것으로, X축은 누적 인구 비율(또는 지역 수), Y축은 누적 서비스 점수 비율을 나타냅니다.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),
                        html.Ul([
                            html.Li("완전 평등선(45도 대각선): 모든 지역이 동일한 서비스를 받는 이상적인 상태", style={'marginBottom': '8px'}),
                            html.Li("로렌츠 곡선: 실제 서비스 점수의 누적 분포. 완전 평등선 아래에 위치", style={'marginBottom': '8px'}),
                            html.Li("지니 계수 = 2 × (완전 평등선과 로렌츠 곡선 사이 면적)", style={'marginBottom': '8px'}),
                            html.Li("곡선이 완전 평등선에서 멀어질수록 불평등도가 증가", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("시군구 vs 행정동 비교", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P([
                            html.Strong("시군구 로렌츠 곡선"), ": 25개 자치구의 평균 서비스 점수 분포. 행정구역 간 정책 우선순위 파악에 유용", html.Br(),
                            html.Strong("행정동 로렌츠 곡선"), ": 426개 행정동의 세밀한 서비스 점수 분포. 지역 내 미시적 격차 파악에 유용"
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8', 'backgroundColor': '#2b2b2b', 'padding': '15px', 'borderRadius': '5px'}),

                        html.H5("해석 기준", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("0.00 ~ 0.20: 매우 평등 - 서비스가 고르게 분포", style={'marginBottom': '8px'}),
                            html.Li("0.20 ~ 0.30: 평등 - 양호한 분포", style={'marginBottom': '8px'}),
                            html.Li("0.30 ~ 0.40: 보통 - 일부 지역 격차 존재", style={'marginBottom': '8px'}),
                            html.Li("0.40 ~ 0.50: 불평등 - 심각한 지역 격차, 정책 개입 필요", style={'marginBottom': '8px'}),
                            html.Li("0.50 이상: 매우 불평등 - 극심한 불균형, 긴급 조치 필요", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'})
                    ])
                ], title="2. 지니 계수 (Gini Coefficient)"),

                # 3. 커버리지 비율
                dbc.AccordionItem([
                    html.Div([
                        html.H5("개념 및 의의", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.P("커버리지 비율은 행정동 또는 시군구 내 전체 인구 중 몇 %가 공원 서비스 범위 내에 거주하는지를 나타냅니다. 접근성 점수가 '얼마나 좋은 서비스를 받는가'를 측정한다면, 커버리지 비율은 '몇 명이나 서비스를 받는가'를 측정합니다.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("계산 공식", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P("커버리지_비율 = (서비스_범위_내_인구 / 전체_인구) × 100", style={'color': '#E0E0E0', 'backgroundColor': '#2b2b2b', 'padding': '15px', 'borderRadius': '5px'}),

                        html.H5("버퍼 거리 설정", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("100m: 도보 1~2분 - 어린이/노약자 접근성 (엄격한 기준)", style={'marginBottom': '8px'}),
                            html.Li("300m: 도보 3~5분 - 생활권공원 기준", style={'marginBottom': '8px'}),
                            html.Li("500m: 도보 5~7분 - 도시공원 법정 기준 (권장)", style={'marginBottom': '8px'}),
                            html.Li("1000m: 도보 10~15분 - 대형공원 접근성", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.P("버퍼 거리가 커질수록 커버리지 비율은 증가하지만, 실제 이용 가능성은 감소합니다.", style={'color': '#FF9800', 'fontStyle': 'italic', 'marginTop': '15px'})
                    ])
                ], title="3. 커버리지 비율 (Coverage Ratio)"),

                # 4. 공원 유형별 분석
                dbc.AccordionItem([
                    html.Div([
                        html.H5("공원 유형 분류 (도시공원법 기준)", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.Ul([
                            html.Li("어린이공원: 소규모, 근린 생활권, 놀이시설 중심 (평균 1,500㎡, 250m 이내)", style={'marginBottom': '8px'}),
                            html.Li("근린공원: 중규모, 일상적 휴식 및 운동 (평균 10,000㎡, 500m 이내)", style={'marginBottom': '8px'}),
                            html.Li("도시자연공원: 대규모 산림형, 자연 보전 (평균 100,000㎡, 1000m+)", style={'marginBottom': '8px'}),
                            html.Li("문화공원: 문화·역사 시설 중심", style={'marginBottom': '8px'}),
                            html.Li("체육공원: 운동 시설 중심 (평균 50,000㎡, 1000m)", style={'marginBottom': '8px'}),
                            html.Li("기타공원: 특수 목적 공원 (묘지공원, 소공원 등)", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("3% 그룹화 규칙", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.P("대시보드는 가독성을 위해 전체 공원 수 대비 3% 미만인 유형은 '기타'로 통합하여 표시합니다.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("해석 방법", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("어린이공원 비중이 높음: 신도시, 주거지역 - 가족 친화적 환경", style={'marginBottom': '8px'}),
                            html.Li("도시자연공원 비중이 높음: 산지 인접 지역 - 대규모 녹지 보유", style={'marginBottom': '8px'}),
                            html.Li("특정 유형 편중: 공원 서비스 다양성 부족 - 다른 유형 보완 필요", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'})
                    ])
                ], title="4. 공원 유형별 분석"),

                # 5. 행정동 레이어 투명도
                dbc.AccordionItem([
                    html.Div([
                        html.H5("개념 및 의의", style={'color': '#64B5F6', 'marginTop': '15px'}),
                        html.P("행정동 레이어 투명도는 choropleth 지도(색상으로 표현된 행정동 경계)의 불투명도를 조절하여, 하부의 OpenStreetMap 배경 지도를 얼마나 보이게 할 것인지 결정합니다.", style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("활용 시나리오", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("투명도 100% (불투명): 서비스 점수 색상에만 집중", style={'marginBottom': '8px'}),
                            html.Li("투명도 80% (기본값): 색상과 배경 지도 균형있게 확인", style={'marginBottom': '8px'}),
                            html.Li("투명도 50%: 도로망, 건물 등 공간 컨텍스트 중시", style={'marginBottom': '8px'}),
                            html.Li("투명도 0% (완전 투명): 배경 지도만 보이며 공원 위치, 버퍼 등 레이어만 확인", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'}),

                        html.H5("권장 설정", style={'color': '#64B5F6', 'marginTop': '20px'}),
                        html.Ul([
                            html.Li("정책 보고서용: 80~100% (색상 명확히 표현)", style={'marginBottom': '8px'}),
                            html.Li("현장 조사용: 50~70% (도로, 지형 확인 필요)", style={'marginBottom': '8px'}),
                            html.Li("교육/발표용: 70~90% (시각적 균형)", style={'marginBottom': '8px'}),
                        ], style={'color': '#E0E0E0', 'lineHeight': '1.8'})
                    ])
                ], title="5. 행정동 레이어 투명도 조절"),

            ], start_collapsed=True, flush=True, style={'backgroundColor': '#2b2b2b'})
        ], style={'padding': '20px', 'backgroundColor': '#2b2b2b'})
    ], style={'backgroundColor': '#2b2b2b', 'border': 'none'}, className="mb-4"),

    dcc.Store(id='analysis-data-store'),

], style={'marginLeft': '300px', 'padding': '30px', 'backgroundColor': '#1e1e1e', 'minHeight': '100vh'})

app.layout = html.Div([sidebar, main_content], style={'backgroundColor': '#1e1e1e'})

# ============================================================================
# 콜백
# ============================================================================

@app.callback(
    [Output('park-type-select', 'options'),
     Output('park-type-select', 'value')],
    [Input('sigungu-select', 'value')],
    prevent_initial_call=False  # 초기 호출 허용
)
def load_park_type_options(sigungu_list):
    try:
        # 공원 데이터 로드
        gdf_parks = data_loader.load_parks()

        # 시군구 필터링
        if sigungu_list and '전체' not in sigungu_list:
            gdf_dong = data_loader.load_dong_geometry()
            gdf_filtered_dong = data_loader.filter_by_sigungu(gdf_dong, sigungu_list)
            gdf_parks = data_loader.spatial_filter_parks(gdf_parks, gdf_filtered_dong, predicate='intersects')

        # 공원 유형 추출 (LABEL 컬럼에서 괄호 앞 텍스트 추출)
        gdf_parks['park_type'] = gdf_parks['LABEL'].str.extract(r'^([^(]+)')[0]
        park_types = sorted(gdf_parks['park_type'].unique().tolist())

        # 옵션 생성 ('전체' 추가)
        options = [{'label': ' 전체', 'value': '전체'}] + [{'label': f' {pt}', 'value': pt} for pt in park_types]

        # 기본값: 전체 선택
        return options, ['전체']
    except Exception as e:
        print(f"Error loading park types: {e}")
        return [{'label': ' 전체', 'value': '전체'}], ['전체']


@app.callback(
    Output('analysis-data-store', 'data'),
    [Input('sigungu-select', 'value'),
     Input('buffer-distance-select', 'value'),
     Input('park-type-select', 'value')],
    prevent_initial_call=False  # 초기 호출 허용
)
def update_analysis_data(sigungu_list, buffer_distance, selected_park_types):
    analysis_mode = 'dong'  # 기본값: 행정동 단위
    try:
        print(f"\n=== update_analysis_data 호출 ===")
        print(f"  buffer_distance: {buffer_distance}")
        print(f"  selected_park_types: {selected_park_types}")
        print(f"  sigungu_list: {sigungu_list}")

        # 다중 버퍼 데이터 로드
        df_multi = data_loader.load_2sfca_multi_buffer()
        print(f"  로드된 데이터: {len(df_multi)}행")

        # 버퍼 거리 필터링
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()
        print(f"  버퍼 필터링 후: {len(df_filtered)}행")

        # 공원 유형 필터링
        if selected_park_types and len(selected_park_types) > 0:
            # '전체'만 선택되거나, '전체'와 다른 유형이 함께 선택된 경우 처리
            specific_types = [pt for pt in selected_park_types if pt != '전체']

            if len(specific_types) > 0:
                # 특정 공원 유형이 선택된 경우 (전체 제외)
                df_filtered = df_filtered[df_filtered['park_types'].isin(specific_types)].copy()
                print(f"  선택된 공원 유형 {specific_types} 필터링 후: {len(df_filtered)}행")

                # 여러 유형 선택 시 행정동별로 집계
                if len(specific_types) > 1:
                    grouped = df_filtered.groupby('ADM_NM').agg({
                        'SIGUNGU_NM': 'first',
                        'total_population': 'first',
                        'covered_population': 'sum',  # 합산 (여러 공원 유형의 커버 인구 합계)
                        'coverage_ratio': 'mean',      # 평균
                        'avg_service_per_capita': 'mean'  # 평균
                    }).reset_index()
                    # 커버리지 비율 재계산
                    grouped['coverage_ratio'] = (grouped['covered_population'] / grouped['total_population'] * 100).clip(upper=100)
                    df_filtered = grouped
                    print(f"  다중 유형 집계 후: {len(df_filtered)}행")
            else:
                # '전체'만 선택된 경우
                df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
                print(f"  공원 유형 '전체' 필터링 후: {len(df_filtered)}행")
        else:
            # 선택 안 했으면 "전체" 유형 사용
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
            print(f"  공원 유형 '전체' 필터링 후: {len(df_filtered)}행")

        # 시군구 필터링
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()
            print(f"  시군구 필터링 후: {len(df_filtered)}행")
        else:
            print(f"  시군구 필터링 안함 (전체 또는 None)")

        if analysis_mode == 'sigungu':
            # 시군구별 집계
            df_grouped = df_filtered.groupby('SIGUNGU_NM').agg({
                'total_population': 'sum',
                'covered_population': 'sum',
                'avg_service_per_capita': 'mean'  # 단순 평균 (각 행정동의 1인당 평균)
            }).reset_index()
            df_grouped['coverage_ratio'] = (df_grouped['covered_population'] / df_grouped['total_population'] * 100)
            df_filtered = df_grouped.rename(columns={'SIGUNGU_NM': 'area_name'})
        else:
            # 행정동
            df_filtered['area_name'] = df_filtered['ADM_NM']

        # 통계 계산
        avg_score = float(df_filtered['avg_service_per_capita'].mean())
        avg_coverage = float(df_filtered['coverage_ratio'].mean()) if 'coverage_ratio' in df_filtered.columns else 0

        # Gini 계수
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
        print(f"  최종 결과: {result}")
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
    print(f"\n=== update_stats 호출 ===")
    print(f"  받은 데이터: {data}")

    if not data:
        print("  데이터가 None이므로 기본값 반환")
        return "0", "0.0000", "0.0%", "0.000"

    # None 값 처리
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
    analysis_mode = 'dong'  # 기본값: 행정동 단위
    try:
        from modules.config import MIN_POPULATION_THRESHOLD

        gdf_merged = data_loader.merge_2sfca_with_geometry()
        gdf_filtered = data_loader.filter_by_sigungu(gdf_merged, sigungu_list)

        if len(gdf_filtered) == 0:
            raise ValueError("선택된 지역에 데이터가 없습니다.")

        # 시군구 분석 모드일 경우 시군구 단위로 집계
        if analysis_mode == 'sigungu':
            import geopandas as gpd
            from modules.config import SIGUNGU_POLYGON_SHP

            # 시군구 경계 shapefile 로드
            gdf_sigungu = gpd.read_file(SIGUNGU_POLYGON_SHP, encoding='cp949')
            if gdf_sigungu.crs != 'EPSG:4326':
                gdf_sigungu = gdf_sigungu.to_crs('EPSG:4326')

            # 서울시만 필터링
            gdf_sigungu['_sido_cd'] = gdf_sigungu['SIGUNGU_CD'].astype(str).str[:2]
            gdf_sigungu = gdf_sigungu[gdf_sigungu['_sido_cd'] == '11'].copy()

            # 시군구명 컬럼 확인
            sigungu_col = None
            for col in ['SIGUNGU_NM', 'sigungu_nm']:
                if col in gdf_filtered.columns:
                    sigungu_col = col
                    break

            if sigungu_col:
                # 시군구별 집계
                gdf_agg = gdf_filtered.groupby(sigungu_col).agg({
                    'total_population': 'sum',
                    'covered_population': 'sum',
                    'avg_service_per_capita': 'mean'
                }).reset_index()
                gdf_agg['coverage_ratio'] = (gdf_agg['covered_population'] / gdf_agg['total_population'] * 100)

                # 시군구 경계와 결합 (geometry 추가)
                gdf_filtered = gdf_sigungu.merge(
                    gdf_agg,
                    left_on='SIGUNGU_NM',
                    right_on=sigungu_col,
                    how='inner'
                )
                gdf_filtered['ADM_NM'] = gdf_filtered['SIGUNGU_NM']
                gdf_filtered['id'] = gdf_filtered.index.astype(str)

        # 선택한 지역에 맞게 지도 중심과 줌 계산 (EPSG:4326 필요)
        if gdf_filtered.crs != 'EPSG:4326':
            gdf_temp = gdf_filtered.to_crs('EPSG:4326')
        else:
            gdf_temp = gdf_filtered

        bounds = gdf_temp.total_bounds  # [minx, miny, maxx, maxy]
        center_lon = (bounds[0] + bounds[2]) / 2
        center_lat = (bounds[1] + bounds[3]) / 2

        # 경계 범위에 따라 줌 레벨 자동 조정
        lon_range = bounds[2] - bounds[0]
        lat_range = bounds[3] - bounds[1]
        max_range = max(lon_range, lat_range)

        if max_range > 0.5:  # 서울 전체
            zoom = 10
        elif max_range > 0.2:  # 여러 구
            zoom = 11
        elif max_range > 0.1:  # 한 구
            zoom = 12
        else:  # 한 동
            zoom = 13

        # 향상된 서비스 지도 생성 (이산형 색상)
        # basemap_opacity가 None이면 기본값 1.0 사용
        if basemap_opacity is None:
            basemap_opacity = 1.0

        fig = create_service_map_enhanced(
            gdf_filtered,
            column='avg_service_per_capita',
            title=f"공원 서비스 접근성 ({analysis_mode} 단위, 버퍼: {buffer_distance}m)",
            use_discrete_colors=False,  # 일단 연속형으로 테스트
            basemap_opacity=basemap_opacity
        )

        # 지도 중심과 줌 업데이트
        fig.update_layout(
            map=dict(
                center={'lat': center_lat, 'lon': center_lon},
                zoom=zoom
            )
        )

        # 시군구 경계선 추가 (서울시 전체 시군구 - 굵은 검정색)
        fig = add_sigungu_boundaries(fig, show_labels=True)  # 기본값 사용: 검정색, 3.0px

        # 행정구역 경계선 추가 (원본 geometry 유지)
        if layers and 'boundary' in layers:
            # 행정동 경계만 표시 (v2 방식 - geometry 단순화 없음)
            fig = add_boundary_lines(fig, gdf_filtered, name="행정동 경계", color='#666666', width=1.0)

        # 공원/버퍼 레이어
        if layers and ('parks' in layers or 'buffers' in layers):
            gdf_parks = data_loader.load_parks()
            print(f"[DEBUG] 전체 공원 수: {len(gdf_parks)}")

            gdf_parks_filtered = data_loader.spatial_filter_parks(gdf_parks, gdf_filtered, predicate='intersects')
            print(f"[DEBUG] 공간 필터링 후 공원 수: {len(gdf_parks_filtered)}")

            # 공원 유형 필터링
            if selected_park_types and '전체' not in selected_park_types:
                gdf_parks_filtered['park_type'] = gdf_parks_filtered['LABEL'].str.extract(r'^([^(]+)')[0]
                print(f"[DEBUG] 선택된 공원 유형: {selected_park_types}")
                print(f"[DEBUG] 유형 필터링 전 공원 수: {len(gdf_parks_filtered)}")
                gdf_parks_filtered = gdf_parks_filtered[gdf_parks_filtered['park_type'].isin(selected_park_types)]
                print(f"[DEBUG] 유형 필터링 후 공원 수: {len(gdf_parks_filtered)}")

            if 'parks' in layers:
                print(f"[DEBUG] 공원 레이어 추가 시도: {len(gdf_parks_filtered)}개 공원")
                if len(gdf_parks_filtered) > 0:
                    # 공원 면적(Polygon)으로 표시
                    fig = add_park_polygons(fig, gdf_parks_filtered, name="공원", color='#2ecc71', opacity=0.5)
                    print(f"[DEBUG] 공원 레이어 추가 완료")
                else:
                    print(f"[DEBUG] 공원 데이터 없음 - 레이어 추가 스킵")

            if 'buffers' in layers and len(gdf_parks_filtered) > 0:
                gdf_buffers = data_loader.create_park_buffers(gdf_parks_filtered, buffer_distance=buffer_distance)
                # 버퍼도 면적으로 표시 (반투명)
                fig = add_park_buffers(fig, gdf_buffers, show_fill=True)

        # 격자 레이어
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
            title=dict(text=f"오류: {str(e)}", x=0.5, xanchor='center'),
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
    """시군구별 TOP 10 차트"""
    try:
        # 다중 버퍼 데이터 로드
        df_multi = data_loader.load_2sfca_multi_buffer()

        # 버퍼 거리 필터링
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # 공원 유형 필터링
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

        # 시군구 필터링
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        # 시군구별 집계
        df_agg = df_filtered.groupby('SIGUNGU_NM').agg({
            'avg_service_per_capita': 'mean'
        }).reset_index()
        df_agg.columns = ['area_name', 'avg_service_per_capita']

        df_sorted = df_agg.nlargest(10, 'avg_service_per_capita')

        # Blues 색상 그라데이션
        colors = ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6',
                  '#4292c6', '#2171b5', '#08519c', '#08306b', '#041f4a'][:len(df_sorted)]

        fig = go.Figure(go.Bar(
            x=df_sorted['avg_service_per_capita'],
            y=df_sorted['area_name'],
            orientation='h',
            marker=dict(color=colors[::-1])  # 상위일수록 진한 색
        ))
        fig.update_layout(
            xaxis_title="평균 서비스 점수 (m²/인)",
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
    """행정동별 TOP 10 차트"""
    try:
        # 다중 버퍼 데이터 로드
        df_multi = data_loader.load_2sfca_multi_buffer()

        # 버퍼 거리 필터링
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # 공원 유형 필터링
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

        # 시군구 필터링
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        df_sorted = df_filtered.nlargest(10, 'avg_service_per_capita')[['ADM_NM', 'avg_service_per_capita']]

        # Blues 색상 그라데이션
        colors = ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6',
                  '#4292c6', '#2171b5', '#08519c', '#08306b', '#041f4a'][:len(df_sorted)]

        fig = go.Figure(go.Bar(
            x=df_sorted['avg_service_per_capita'],
            y=df_sorted['ADM_NM'],
            orientation='h',
            marker=dict(color=colors[::-1])  # 상위일수록 진한 색
        ))
        fig.update_layout(
            xaxis_title="평균 서비스 점수 (m²/인)",
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
    """시군구별 로렌츠 곡선"""
    try:
        # 다중 버퍼 데이터 로드
        df_multi = data_loader.load_2sfca_multi_buffer()

        # 버퍼 거리 필터링
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # 공원 유형 필터링
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

        # 시군구 필터링
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        # 시군구별 집계
        df_agg = df_filtered.groupby('SIGUNGU_NM').agg({
            'avg_service_per_capita': 'mean'
        }).reset_index()
        scores = df_agg['avg_service_per_capita'].dropna().sort_values().values

        n = len(scores)
        if n == 0:
            return go.Figure()
        cum_scores = np.cumsum(scores) / np.sum(scores)
        cum_pop = np.arange(1, n + 1) / n

        # Gini 계수 계산
        gini = (2 * np.sum(np.arange(1, n + 1) * scores)) / (n * np.sum(scores)) - (n + 1) / n

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cum_pop, y=cum_scores,
            mode='lines',
            name='로렌츠 곡선',
            line=dict(color='#2196F3', width=2),
            fill='tonexty',
            fillcolor='rgba(33, 150, 243, 0.2)'
        ))
        fig.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode='lines',
            name='완전 평등선',
            line=dict(color='#FF9800', dash='dash', width=2)
        ))

        fig.update_layout(
            title=f"로렌츠 곡선 - 시군구 (Gini: {gini:.3f})",
            xaxis_title="누적 인구 비율",
            yaxis_title="누적 서비스 점수 비율",
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
    """행정동별 로렌츠 곡선"""
    try:
        # 다중 버퍼 데이터 로드
        df_multi = data_loader.load_2sfca_multi_buffer()

        # 버퍼 거리 필터링
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # 공원 유형 필터링
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

        # 시군구 필터링
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        scores = df_filtered['avg_service_per_capita'].dropna().sort_values().values
        n = len(scores)
        if n == 0:
            return go.Figure()
        cum_scores = np.cumsum(scores) / np.sum(scores)
        cum_pop = np.arange(1, n + 1) / n

        # Gini 계수 계산
        gini = (2 * np.sum(np.arange(1, n + 1) * scores)) / (n * np.sum(scores)) - (n + 1) / n

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cum_pop, y=cum_scores,
            mode='lines',
            name='로렌츠 곡선',
            line=dict(color='#4CAF50', width=2),
            fill='tonexty',
            fillcolor='rgba(76, 175, 80, 0.2)'
        ))
        fig.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode='lines',
            name='완전 평등선',
            line=dict(color='#FF9800', dash='dash', width=2)
        ))

        fig.update_layout(
            title=f"로렌츠 곡선 - 행정동 (Gini: {gini:.3f})",
            xaxis_title="누적 인구 비율",
            yaxis_title="누적 서비스 점수 비율",
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
        # 공원 데이터 로드
        gdf_parks = data_loader.load_parks()

        # 시군구 필터링 (공원의 위치를 기준으로)
        if sigungu_list and '전체' not in sigungu_list:
            # 행정동 경계 로드
            gdf_dong = data_loader.load_dong_geometry()
            gdf_filtered_dong = data_loader.filter_by_sigungu(gdf_dong, sigungu_list)

            # 공원 필터링 (공간 조인)
            gdf_parks = data_loader.spatial_filter_parks(gdf_parks, gdf_filtered_dong, predicate='intersects')

        # LABEL에서 공원 유형 추출 (예: "기타공원(정릉)" -> "기타공원")
        gdf_parks['park_type'] = gdf_parks['LABEL'].str.extract(r'^([^(]+)')[0]

        # 공원 유형별 개수 집계
        type_counts = gdf_parks['park_type'].value_counts()

        # 3% 미만은 '기타'로 묶기
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
            type_counts_grouped['기타'] = other_count

        # 원형 차트 생성 (QGIS 색상 적용)
        from modules.config import PARK_TYPE_COLORS

        fig = go.Figure(data=[go.Pie(
            labels=list(type_counts_grouped.keys()),
            values=list(type_counts_grouped.values()),
            hole=0.3,  # 도넛 차트
            marker=dict(
                colors=PARK_TYPE_COLORS,
                line=dict(color='#1e1e1e', width=2)
            ),
            textinfo='label+percent',
            textposition='auto',
            hovertemplate='<b>%{label}</b><br>개수: %{value}개<br>비율: %{percent}<extra></extra>'
        )])

        fig.update_layout(
            title=f"공원 유형별 분포 (총 {total}개)",
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
    """공원 유형별 접근성 기여도 파이차트"""
    print(f"[DEBUG] update_park_type_contribution called with sigungu_list: {sigungu_list}")
    try:
        # 다중 버퍼 데이터 로드
        df_multi = data_loader.load_2sfca_multi_buffer()
        print(f"[DEBUG] df_multi loaded: {len(df_multi)} rows")

        # 시군구 필터링
        if sigungu_list and '전체' not in sigungu_list:
            df_multi = df_multi[df_multi['SIGUNGU_NM'].isin(sigungu_list)]

        # 500m 버퍼, 전체 제외한 공원 유형별 데이터
        df_500m_types = df_multi[
            (df_multi['buffer_distance'] == 500) &
            (df_multi['park_types'] != '전체')
        ].copy()

        if len(df_500m_types) == 0:
            return go.Figure()

        # 공원 유형별 평균 서비스 점수 계산
        type_service_scores = df_500m_types.groupby('park_types').agg({
            'avg_service_per_capita': 'mean'
        }).reset_index()

        # 접근성 기여도 계산 (전체 대비 비율)
        type_service_scores['contribution_ratio'] = (
            type_service_scores['avg_service_per_capita'] /
            type_service_scores['avg_service_per_capita'].sum() * 100
        )

        # 정렬
        type_service_scores = type_service_scores.sort_values('contribution_ratio', ascending=False)

        # 3% 미만은 '기타'로 묶기
        threshold = 3.0
        large_contrib = type_service_scores[type_service_scores['contribution_ratio'] >= threshold]
        small_contrib = type_service_scores[type_service_scores['contribution_ratio'] < threshold]

        labels = large_contrib['park_types'].tolist()
        values = large_contrib['contribution_ratio'].tolist()

        if len(small_contrib) > 0:
            other_contribution = small_contrib['contribution_ratio'].sum()
            labels.append(f'기타 ({len(small_contrib)}개 유형)')
            values.append(other_contribution)

        # 색상 설정 (Spectral 컬러맵 사용 - 주피터와 동일)
        import plotly.express as px
        # Spectral은 diverging 컬러맵
        colors_spectral = px.colors.diverging.Spectral
        # 색상 범위 조정
        n_colors = len(labels)
        if n_colors <= len(colors_spectral):
            colors = colors_spectral[:n_colors]
        else:
            # 색상이 부족하면 반복
            colors = [colors_spectral[i % len(colors_spectral)] for i in range(n_colors)]

        # 파이차트 생성
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.7,  # 도넛 차트 (주피터: 0.70)
            marker=dict(
                colors=colors,
                line=dict(color='#1e1e1e', width=2)
            ),
            textinfo='label+percent',
            textposition='auto',
            textfont=dict(size=10, color='black'),
            hovertemplate='<b>%{label}</b><br>접근성 기여도: %{value:.1f}%<extra></extra>',
            pull=[0.05 if i == 0 else 0 for i in range(len(labels))]  # 최대 기여도 항목 강조
        )])

        total_types = len(type_service_scores)

        fig.update_layout(
            title=dict(
                text="공원 유형별 접근성 기여도 (500m 버퍼 기준)",
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
                text=f'총 {total_types}개<br>공원 유형',
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
        # 공원 데이터 로드
        gdf_parks = data_loader.load_parks()

        # 시군구 필터링
        if sigungu_list and '전체' not in sigungu_list:
            gdf_dong = data_loader.load_dong_geometry()
            gdf_filtered_dong = data_loader.filter_by_sigungu(gdf_dong, sigungu_list)
            gdf_parks = data_loader.spatial_filter_parks(gdf_parks, gdf_filtered_dong, predicate='intersects')

        # 공원 유형 추출 (LABEL 컬럼에서 괄호 앞 텍스트 추출)
        gdf_parks['park_type'] = gdf_parks['LABEL'].str.extract(r'^([^(]+)')[0]

        # 공원 유형별 개수 집계
        type_counts = gdf_parks['park_type'].value_counts()

        # 3% 미만은 '기타'로 묶기
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
            type_counts_grouped['기타'] = other_count

        # 내림차순 정렬
        sorted_types = sorted(type_counts_grouped.items(), key=lambda x: x[1], reverse=True)
        labels = [item[0] for item in sorted_types]
        values = [item[1] for item in sorted_types]

        # 막대 차트 생성 (QGIS 색상 적용)
        from modules.config import PARK_TYPE_COLORS

        # 각 막대에 색상 할당
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
            hovertemplate='<b>%{x}</b><br>개수: %{y}개<br>비율: %{customdata:.1f}%<extra></extra>',
            customdata=[v/total*100 for v in values]
        )])

        fig.update_layout(
            title=f"공원 유형별 개수 (총 {total}개)",
            xaxis_title="공원 유형",
            yaxis_title="개수",
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


# ========== 3개의 새로운 분석 차트 콜백 ==========

@app.callback(
    Output('buffer-avg-accessibility-chart', 'figure'),
    [Input('sigungu-select', 'value'),
     Input('park-type-select', 'value')]
)
def update_buffer_avg_accessibility_chart(sigungu_list, selected_park_types):
    """버퍼별 평균 접근성 변화"""
    try:
        df_multi = data_loader.load_2sfca_multi_buffer()

        # 공원 유형 필터링
        if selected_park_types and len(selected_park_types) > 0:
            if '전체' in selected_park_types:
                df_filtered = df_multi[df_multi['park_types'] == '전체'].copy()
            else:
                df_filtered = df_multi[df_multi['park_types'].isin(selected_park_types)].copy()
        else:
            df_filtered = df_multi[df_multi['park_types'] == '전체'].copy()

        # 시군구 필터링
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        # 버퍼별 평균 계산
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

        # 라인 차트 생성
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
            hovertemplate='<b>%{x}m</b><br>평균 점수: %{y:.2f} m²/인<extra></extra>'
        ))

        fig.update_layout(
            xaxis_title="버퍼 거리 (m)",
            yaxis_title="평균 접근성 (m²/인)",
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
    """시군구별 지니계수 비교"""
    try:
        df_multi = data_loader.load_2sfca_multi_buffer()

        # 버퍼와 공원 유형 필터링
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()
        if selected_park_types and len(selected_park_types) > 0 and '전체' in selected_park_types:
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()
        else:
            df_filtered = df_filtered[df_filtered['park_types'] == '전체'].copy()

        # 시군구별 지니계수 계산
        gini_results = []
        for sigungu in df_filtered['SIGUNGU_NM'].unique():
            df_sigungu = df_filtered[df_filtered['SIGUNGU_NM'] == sigungu]
            scores = df_sigungu['avg_service_per_capita'].dropna().sort_values().values

            if len(scores) > 1:
                n = len(scores)
                gini = (2 * np.sum(np.arange(1, n + 1) * scores)) / (n * np.sum(scores)) - (n + 1) / n
                gini_results.append({'sigungu': sigungu, 'gini': gini})

        df_gini = pd.DataFrame(gini_results).nlargest(10, 'gini')

        # 바 차트 생성
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
            hovertemplate='<b>%{x}</b><br>지니계수: %{y:.3f}<extra></extra>'
        )])

        fig.update_layout(
            xaxis_title="",
            yaxis_title="지니계수 (불평등도)",
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
    """상위/하위 5개 동 비교"""
    try:
        df_multi = data_loader.load_2sfca_multi_buffer()

        # 버퍼 필터링
        df_filtered = df_multi[df_multi['buffer_distance'] == buffer_distance].copy()

        # 공원 유형 필터링
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

        # 시군구 필터링
        if sigungu_list and len(sigungu_list) > 0 and '전체' not in sigungu_list:
            df_filtered = df_filtered[df_filtered['SIGUNGU_NM'].isin(sigungu_list)].copy()

        # 상위 5개와 하위 5개 선택
        top5 = df_filtered.nlargest(5, 'avg_service_per_capita')[['ADM_NM', 'avg_service_per_capita']].copy()
        bottom5 = df_filtered.nsmallest(5, 'avg_service_per_capita')[['ADM_NM', 'avg_service_per_capita']].copy()

        # 역순으로 정렬 (상위가 위로 오도록)
        top5 = top5.sort_values('avg_service_per_capita', ascending=True)
        bottom5 = bottom5.sort_values('avg_service_per_capita', ascending=True)

        # 바 차트 생성
        fig = go.Figure()

        # 하위 5개 (빨강)
        fig.add_trace(go.Bar(
            x=bottom5['avg_service_per_capita'],
            y=bottom5['ADM_NM'],
            orientation='h',
            name='하위 5',
            marker=dict(color='#EF5350'),
            text=bottom5['avg_service_per_capita'].round(2),
            textposition='outside',
            textfont=dict(color='#FFFFFF', size=10),
            hovertemplate='<b>%{y}</b><br>접근성: %{x:.2f} m²/인<extra></extra>'
        ))

        # 상위 5개 (파랑)
        fig.add_trace(go.Bar(
            x=top5['avg_service_per_capita'],
            y=top5['ADM_NM'],
            orientation='h',
            name='상위 5',
            marker=dict(color='#42A5F5'),
            text=top5['avg_service_per_capita'].round(2),
            textposition='outside',
            textfont=dict(color='#FFFFFF', size=10),
            hovertemplate='<b>%{y}</b><br>접근성: %{x:.2f} m²/인<extra></extra>'
        ))

        fig.update_layout(
            title='<b>상위/하위 5개 동 비교</b>',
            xaxis_title="서비스 점수 (m²/인)",
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
    print("서울시 공원 서비스 분석 대시보드 시작")
    print("http://127.0.0.1:8050 에서 접속하세요")
    print("같은 네트워크의 다른 기기에서는 http://<서버IP>:8050 으로 접속하세요")
    app.run(debug=True, host='0.0.0.0', port=8050)
