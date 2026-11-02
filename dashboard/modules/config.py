"""
서울시 공원 서비스 분석 대시보드 설정
"""
from pathlib import Path

# 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
S1_DATA_PATH = PROJECT_ROOT.parent / 's1_data' / 's2_processed_data'

# 행정경계 shapefile 경로
BOUNDARY_ROOT = PROJECT_ROOT.parent / "s1_data" / "s1_org_data" / "브이월드" / "센서스경계"
SIGUNGU_POLYGON_SHP = BOUNDARY_ROOT / "BND_SIGUNGU_PG" / "BND_SIGUNGU_PG.shp"
SIDO_POLYGON_SHP = BOUNDARY_ROOT / "BND_SIDO_PG" / "BND_SIDO_PG.shp"

# GeoJSON 및 데이터 파일 경로
GEOJSON_DONG = S1_DATA_PATH / 'seoul_dong_with_pop.geojson'
GEOJSON_DONG_SERVICE = S1_DATA_PATH / 'dong_service_score.geojson'  # 2SFCA 결과가 포함된 GeoJSON
GEOJSON_PARKS = S1_DATA_PATH / 'seoul_parks.geojson'
SHAPEFILE_GRID = S1_DATA_PATH / 'seoul_100m_grid_population.shp'
CSV_2SFCA = S1_DATA_PATH / 'dong_service_score_fixed.csv'
CSV_2SFCA_MULTI = S1_DATA_PATH / 'dong_service_score_multi_buffer_parktype.csv'  # 다중 버퍼 및 공원유형별
CSV_PARK_COVERAGE = S1_DATA_PATH / 'park_service_coverage.csv'
CSV_SIGUNGU_COMPARISON = S1_DATA_PATH / 'sigungu_service_comparison.csv'

# 분석 파라미터
BUFFER_DISTANCES = [100, 300, 500, 1000]  # 버퍼 거리 (미터)
DEFAULT_BUFFER = 500  # 기본 버퍼 500m (공원 유형별 데이터 사용 가능)

# 지도 설정
MAP_CENTER = {'lat': 37.5665, 'lon': 126.9780}  # 서울시청
MAP_ZOOM = 10
MAP_HEIGHT = 800

# 색상 설정 (QGIS/04.BI 스타일 적용)
# 서비스 접근성 지도 - 하얀색(낮음) → 파랑(높음) 스케일
CHOROPLETH_COLORSCALE = [
    [0.0, '#ffffff'],   # 하얀색 (매우 낮음)
    [0.2, '#deebf7'],   # 매우 연한 파랑
    [0.4, '#c6dbef'],   # 연한 파랑
    [0.6, '#9ecae1'],   # 파랑
    [0.8, '#6baed6'],   # 진한 파랑
    [1.0, '#08519c']    # 매우 진한 파랑 (매우 높음)
]

PARK_COLOR = '#11998e'  # 공원 색상 (청록색 - QGIS 스타일)
BUFFER_COLOR = '#fdae61'  # 버퍼 색상 (주황색 - 눈에 잘 띄도록)
GRID_COLOR = '#9970ab'  # 격자 인구 색상 (보라색)

# LISA 클러스터 색상 (QGIS/04.BI 동일)
CLUSTER_COLORS = {
    'HH': '#d7191c',  # 빨강 - 핫스팟 (High-High)
    'LL': '#2c7bb6',  # 파랑 - 콜드스팟 (Low-Low)
    'LH': '#9970ab',  # 보라 - 저값 이상치 (Low-High)
    'HL': '#fdae61',  # 주황 - 고값 이상치 (High-Low)
    'NS': '#e0e0e0'   # 연한 회색 - Not Significant (QGIS visualizations.py 스타일)
}

# 공원 유형별 차트 색상 (QGIS 다크모드 친화적)
PARK_TYPE_COLORS = [
    '#11998e',  # 청록 (primary)
    '#2c7bb6',  # 파랑
    '#9970ab',  # 보라
    '#fdae61',  # 주황
    '#d7191c',  # 빨강
    '#64B5F6',  # 밝은 파랑
    '#f093fb',  # 분홍
    '#FFD700'   # 금색
]

CLUSTER_LABELS = {
    'HH': 'HH (핫스팟)',
    'LL': 'LL (콜드스팟)',
    'LH': 'LH (저값 이상치)',
    'HL': 'HL (고값 이상치)',
    'NS': 'Not Significant'
}

# K값 설정 (K-nearest neighbors)
K_VALUES = [3, 4, 5, 6, 7, 8]
DEFAULT_K = 5

# 필터링 설정
MIN_POPULATION_THRESHOLD = 100  # 최소 인구수 (격자 필터링용)

# 서비스 점수 기준
SERVICE_SCORE_BREAKS = [0, 0.2, 0.4, 0.6, 0.8, 1.0]  # 점수 구간
SERVICE_LABELS = ['매우 낮음', '낮음', '보통', '높음', '매우 높음']
