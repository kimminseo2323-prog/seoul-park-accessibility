"""
GIS 시각화 모듈 (QGIS/04.BI 패턴 적용)
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
from typing import Optional, Dict
from shapely.ops import unary_union

from .config import (
    MAP_CENTER, MAP_ZOOM, MAP_HEIGHT,
    CHOROPLETH_COLORSCALE, PARK_COLOR, BUFFER_COLOR, GRID_COLOR,
    CLUSTER_COLORS, CLUSTER_LABELS, PARK_TYPE_COLORS,
    SIGUNGU_POLYGON_SHP
)


def _sanitize_geojson(geojson_dict):
    """
    GeoJSON numpy 타입을 Python native 타입으로 변환
    (QGIS/04.BI 패턴 - JSON 직렬화 오류 방지)

    Args:
        geojson_dict: GeoJSON 딕셔너리

    Returns:
        dict: 변환된 GeoJSON
    """
    if isinstance(geojson_dict, dict):
        result = {}
        for key, value in geojson_dict.items():
            if key == 'coordinates':
                result[key] = _convert_coords_to_native(value)
            elif isinstance(value, (dict, list)):
                result[key] = _sanitize_geojson(value)
            elif isinstance(value, (np.floating, np.integer)):
                result[key] = float(value)
            else:
                result[key] = value
        return result
    elif isinstance(geojson_dict, list):
        return [_sanitize_geojson(item) for item in geojson_dict]
    else:
        return geojson_dict


def _convert_coords_to_native(coords):
    """좌표를 Python native float로 변환"""
    if isinstance(coords, (list, tuple)):
        return [_convert_coords_to_native(c) for c in coords]
    else:
        return float(coords)


def _simplify_geometry(gdf: gpd.GeoDataFrame, tolerance: float = 0.0001) -> gpd.GeoDataFrame:
    """
    Geometry 단순화 (ESDA 스타일 - 정확도 우선)

    Args:
        gdf: GeoDataFrame
        tolerance: 단순화 허용 오차 (기본값: 0.0001 = 매우 정확)

    Returns:
        gpd.GeoDataFrame: 단순화된 GeoDataFrame
    """
    gdf_viz = gdf.copy()
    # tolerance를 매우 작게 설정하여 원본 geometry에 가깝게 유지
    gdf_viz['geometry'] = gdf_viz['geometry'].simplify(
        tolerance=tolerance, preserve_topology=True
    )
    return gdf_viz


def create_service_map(
    gdf: gpd.GeoDataFrame,
    column: str = 'avg_service_per_capita',
    title: str = "서울시 공원 서비스 접근성",
    colorscale: str = CHOROPLETH_COLORSCALE,
    basemap_opacity: float = 1.0
) -> go.Figure:
    """
    서비스 접근성 Choropleth 지도 생성 (QGIS/04.BI 패턴)

    Args:
        gdf: GeoDataFrame (서비스 점수 포함)
        column: 시각화할 컬럼명
        title: 지도 제목
        colorscale: 색상 스케일

    Returns:
        go.Figure: Plotly Figure
    """
    # Geometry 단순화
    gdf_viz = _simplify_geometry(gdf)

    # ID 컬럼 확인
    if 'id' not in gdf_viz.columns:
        gdf_viz['id'] = gdf_viz.index.astype(str)

    # GeoJSON 생성 및 sanitize
    geojson_all = json.loads(gdf_viz.to_json())
    geojson_all = _sanitize_geojson(geojson_all)

    # Figure 생성
    fig = go.Figure()

    # 동 이름 컬럼 자동 감지
    name_col = None
    for col in ['ADM_NM', 'adm_nm', 'DONG_NM', 'dong_nm', 'id']:
        if col in gdf_viz.columns:
            name_col = col
            break

    # 백분위수 기반 색상 스케일 범위 계산
    values = gdf_viz[column].dropna()
    if len(values) > 0:
        # 10%, 25%, 50%, 75%, 90%, 100% 백분위수 계산
        p10 = np.percentile(values, 10)
        p25 = np.percentile(values, 25)
        p50 = np.percentile(values, 50)
        p75 = np.percentile(values, 75)
        p90 = np.percentile(values, 90)
        p100 = np.percentile(values, 100)

        # 색상 스케일 범위: 10%~90% 백분위수 사용 (극단값 제외)
        zmin = p10
        zmax = p90
    else:
        zmin = 0
        zmax = 100

    # Choroplethmap 추가 (ESDA 스타일 + 백분위수 기반 스케일링)
    fig.add_trace(go.Choroplethmap(
        geojson=geojson_all,
        locations=gdf_viz['id'].tolist(),
        z=gdf_viz[column].tolist(),
        featureidkey="properties.id",
        colorscale=colorscale,
        zmin=zmin,  # 10% 백분위수
        zmax=zmax,  # 90% 백분위수
        marker=dict(opacity=basemap_opacity, line=dict(width=0.5, color='#CCCCCC')),  # 투명도 조절 가능
        colorbar=dict(
            title=dict(text="접근성 점수<br>(m²/인)", font=dict(size=11, color='white')),
            thickness=20,
            len=0.7,
            x=1.02,
            tickfont=dict(size=10, color='white'),
            bgcolor='rgba(30,30,30,0.8)',
            bordercolor='#555',
            borderwidth=1,
            tickvals=[p10, p25, p50, p75, p90],  # 백분위수 눈금
            ticktext=[f'{p10:.1f}', f'{p25:.1f}', f'{p50:.1f}', f'{p75:.1f}', f'{p90:.1f}']
        ),
        hovertemplate='<b>%{customdata[0]}</b><br>' +
                      '접근성: %{z:.2f} m²/인<br>' +
                      '<extra></extra>',
        customdata=gdf_viz[[name_col]].values if name_col else gdf_viz[['id']].values,
        showscale=True
    ))

    # 레이아웃 설정 (OpenStreetMap 배경)
    fig.update_layout(
        map=dict(
            style='open-street-map',
            center=MAP_CENTER,
            zoom=MAP_ZOOM
        ),
        height=MAP_HEIGHT,
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(text=title, x=0.5, xanchor='center'),
        paper_bgcolor='#1e1e1e',
        plot_bgcolor='#1e1e1e',
        font=dict(color='#FFFFFF')
    )

    return fig


def create_service_map_enhanced(
    gdf: gpd.GeoDataFrame,
    column: str = 'avg_service_per_capita',
    title: str = "서울시 공원 서비스 접근성",
    use_discrete_colors: bool = True,
    basemap_opacity: float = 1.0
) -> go.Figure:
    """
    서비스 접근성 Choropleth 지도 생성 (개선된 버전 - 이산형 색상)

    Args:
        gdf: GeoDataFrame (서비스 점수 포함)
        column: 시각화할 컬럼명
        title: 지도 제목
        use_discrete_colors: 이산형 색상 사용 여부

    Returns:
        go.Figure: Plotly Figure
    """
    import pandas as pd
    from .config import SERVICE_SCORE_BREAKS, SERVICE_LABELS

    # Geometry 단순화
    gdf_viz = _simplify_geometry(gdf)

    # ID 컬럼 확인
    if 'id' not in gdf_viz.columns:
        gdf_viz['id'] = gdf_viz.index.astype(str)

    # 동 이름 컬럼 자동 감지
    name_col = None
    for col in ['ADM_NM', 'adm_nm', 'DONG_NM', 'dong_nm', 'SIGUNGU_NM', 'sigungu_nm', 'id']:
        if col in gdf_viz.columns:
            name_col = col
            break

    if use_discrete_colors:
        # 백분위수 기반 이산형 색상 적용
        gdf_viz = gdf_viz.copy()

        # 백분위수 계산
        percentiles = gdf_viz[column].rank(pct=True) * 100

        # 카테고리 분류
        bins = [0, 20, 40, 60, 80, 100]
        labels_discrete = ['매우 낮음', '낮음', '보통', '높음', '매우 높음']
        gdf_viz['score_category'] = pd.cut(percentiles, bins=bins, labels=labels_discrete, include_lowest=True)

        # 이산형 colorscale (Red-Yellow-Green 발산형)
        discrete_colors = [
            '#d73027',  # 매우 낮음 - 빨강
            '#fc8d59',  # 낮음 - 주황
            '#fee08b',  # 보통 - 노랑
            '#91cf60',  # 높음 - 연두
            '#1a9850'   # 매우 높음 - 초록
        ]

        # 카테고리를 숫자로 매핑 (0-4)
        category_map = {cat: i for i, cat in enumerate(labels_discrete)}
        gdf_viz['z_discrete'] = gdf_viz['score_category'].map(category_map)

        # GeoJSON 생성 및 sanitize
        geojson_all = json.loads(gdf_viz.to_json())
        geojson_all = _sanitize_geojson(geojson_all)

        # Figure 생성
        fig = go.Figure()

        # Choroplethmapbox 추가 (이산형)
        # colorscale 올바른 형식: [[0, color0], [0.25, color1], [0.5, color2], [0.75, color3], [1, color4]]
        colorscale_discrete = [
            [0.0, discrete_colors[0]],
            [0.25, discrete_colors[1]],
            [0.5, discrete_colors[2]],
            [0.75, discrete_colors[3]],
            [1.0, discrete_colors[4]]
        ]

        fig.add_trace(go.Choroplethmap(
            geojson=geojson_all,
            locations=gdf_viz['id'].tolist(),
            z=gdf_viz['z_discrete'].tolist(),
            featureidkey="properties.id",
            colorscale=colorscale_discrete,
            zmin=0,
            zmax=4,
            marker=dict(opacity=basemap_opacity, line=dict(width=0.5, color='#CCCCCC')),  # 투명도 조절 가능
            colorbar=dict(
                title=dict(text="접근성<br>수준", font=dict(size=11, color='white')),
                thickness=20,
                len=0.7,
                x=1.02,
                tickmode='array',
                tickvals=[0, 1, 2, 3, 4],
                ticktext=labels_discrete,
                tickfont=dict(size=10, color='white'),
                bgcolor='rgba(30,30,30,0.8)',
                bordercolor='#555',
                borderwidth=1
            ),
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                          f'{column}: %{{customdata[1]:.2f}} m²/인<br>' +
                          '수준: %{customdata[2]}<br>' +
                          '<extra></extra>',
            customdata=gdf_viz[[name_col, column, 'score_category']].values if name_col else gdf_viz[[column, 'score_category']].values,
            showscale=True
        ))

    else:
        # 연속형 색상 (백분위수 기반 스케일링)
        geojson_all = json.loads(gdf_viz.to_json())
        geojson_all = _sanitize_geojson(geojson_all)

        # 백분위수 기반 색상 스케일 범위 계산
        values = gdf_viz[column].dropna()
        if len(values) > 0:
            # 10%, 25%, 50%, 75%, 90% 백분위수 계산
            p10 = np.percentile(values, 10)
            p25 = np.percentile(values, 25)
            p50 = np.percentile(values, 50)
            p75 = np.percentile(values, 75)
            p90 = np.percentile(values, 90)

            # 색상 스케일 범위: 10%~90% 백분위수 사용 (극단값 제외)
            zmin = p10
            zmax = p90
        else:
            zmin = 0
            zmax = 100

        fig = go.Figure()

        fig.add_trace(go.Choroplethmap(
            geojson=geojson_all,
            locations=gdf_viz['id'].tolist(),
            z=gdf_viz[column].tolist(),
            featureidkey="properties.id",
            colorscale=CHOROPLETH_COLORSCALE,
            zmin=zmin,  # 10% 백분위수
            zmax=zmax,  # 90% 백분위수
            reversescale=False,  # config.py의 색상 순서 그대로 사용
            marker=dict(opacity=basemap_opacity, line=dict(width=0.5, color='#CCCCCC')),  # 투명도 조절 가능
            colorbar=dict(
                title=dict(text="접근성 점수<br>(m²/인)", font=dict(size=11, color='white')),
                thickness=20,
                len=0.7,
                x=1.02,
                tickfont=dict(size=10, color='white'),
                bgcolor='rgba(30,30,30,0.8)',
                bordercolor='#555',
                borderwidth=1,
                tickvals=[p10, p25, p50, p75, p90],  # 백분위수 눈금
                ticktext=[f'{p10:.1f}', f'{p25:.1f}', f'{p50:.1f}', f'{p75:.1f}', f'{p90:.1f}']
            ),
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                          '접근성: %{z:.2f} m²/인<br>' +
                          '<extra></extra>',
            customdata=gdf_viz[[name_col]].values if name_col else gdf_viz[['id']].values,
            showscale=True
        ))

    # 레이아웃 설정 (OpenStreetMap 배경)
    fig.update_layout(
        map=dict(
            style='open-street-map',
            center=MAP_CENTER,
            zoom=MAP_ZOOM
        ),
        height=MAP_HEIGHT,
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(text=title, x=0.5, xanchor='center', font=dict(size=16)),
        paper_bgcolor='#1e1e1e',
        plot_bgcolor='#1e1e1e',
        font=dict(color='#FFFFFF')
    )

    return fig


def add_park_polygons(
    fig: go.Figure,
    gdf_parks: gpd.GeoDataFrame,
    name: str = "공원",
    color: str = PARK_COLOR,
    opacity: float = 0.6
) -> go.Figure:
    """
    공원 면적(Polygon) 레이어 추가 - 실제 공원 경계 표시

    Args:
        fig: 기존 Plotly Figure
        gdf_parks: 공원 GeoDataFrame
        name: 레이어 이름
        color: 채우기 색상
        opacity: 투명도

    Returns:
        go.Figure: 업데이트된 Figure
    """
    # EPSG:4326 변환
    gdf_viz = gdf_parks.copy()
    if gdf_viz.crs != 'EPSG:4326':
        gdf_viz = gdf_viz.to_crs('EPSG:4326')

    # ID 컬럼 확인
    if 'id' not in gdf_viz.columns:
        gdf_viz['id'] = gdf_viz.index.astype(str)

    # GeoJSON 생성 및 sanitize
    geojson_parks = json.loads(gdf_viz.to_json())
    geojson_parks = _sanitize_geojson(geojson_parks)

    # 공원명 및 면적 컬럼 자동 감지
    name_col = None
    for col in ['park_name', 'ENT_NAME', 'LABEL', 'name', 'PARK_NM']:
        if col in gdf_viz.columns:
            name_col = col
            break

    area_col = None
    for col in ['area', 'df_park_area_m2', 'AREA', 'area_m2', 'df_park_area_km2']:
        if col in gdf_viz.columns:
            area_col = col
            break

    # 공원 유형 추출 (LABEL 컬럼에서)
    if 'LABEL' in gdf_viz.columns:
        import re
        gdf_viz['park_type'] = gdf_viz['LABEL'].str.extract(r'^([^(]+)')[0]
        gdf_viz['park_name'] = gdf_viz['LABEL'].str.extract(r'\(([^)]+)\)')[0]
    else:
        gdf_viz['park_type'] = None
        gdf_viz['park_name'] = None

    # customdata 및 hovertemplate 준비
    if name_col and area_col:
        # 면적이 km2인 경우 m2로 변환
        if 'km2' in area_col.lower():
            area_values = (gdf_viz[area_col] * 1_000_000).values
        else:
            area_values = gdf_viz[area_col].values

        # 유형, 이름, 면적 포함
        customdata = list(zip(
            gdf_viz['park_type'].fillna('').values,
            gdf_viz['park_name'].fillna('').values,
            area_values
        ))
        hovertemplate = '<b>%{customdata[0]}</b><br>이름: %{customdata[1]}<br>면적: %{customdata[2]:.0f} m²<br><extra></extra>'
    elif name_col:
        customdata = list(zip(
            gdf_viz['park_type'].fillna('').values,
            gdf_viz['park_name'].fillna('').values
        ))
        hovertemplate = '<b>%{customdata[0]}</b><br>이름: %{customdata[1]}<br><extra></extra>'
    else:
        customdata = None
        hovertemplate = '<b>공원</b><br><extra></extra>'

    # Choroplethmap으로 공원 면적 표시
    fig.add_trace(go.Choroplethmap(
        geojson=geojson_parks,
        locations=gdf_viz['id'].tolist(),
        z=[1] * len(gdf_viz),  # 동일한 색상
        featureidkey="properties.id",
        colorscale=[[0, color], [1, color]],
        marker=dict(opacity=opacity, line=dict(width=1, color='#FFFFFF')),
        hovertemplate=hovertemplate,
        customdata=customdata,
        showscale=False,
        name=name
    ))

    # 공원 이름 및 유형 텍스트 라벨 추가 (centroid에 표시)
    if name_col:
        label_lons = []
        label_lats = []
        label_texts = []

        for idx, row in gdf_viz.iterrows():
            centroid = row.geometry.centroid
            park_label = row.get('LABEL', '')  # LABEL 컬럼 사용

            if park_label and pd.notna(park_label):
                # LABEL에서 유형과 이름 추출 (예: "어린이공원(정릉)" → 유형: 어린이공원, 이름: 정릉)
                import re
                match = re.match(r'^([^(]+)\(([^)]+)\)', str(park_label))
                if match:
                    park_type = match.group(1).strip()
                    park_name = match.group(2).strip()
                    display_text = f"{park_type}\n{park_name}"
                else:
                    # 괄호가 없는 경우 LABEL 전체 사용
                    display_text = str(park_label)

                label_lons.append(centroid.x)
                label_lats.append(centroid.y)
                label_texts.append(display_text)

        if label_lons:
            # 배경용 하얀 텍스트 (테두리 효과)
            for offset_x, offset_y in [(0.0001, 0), (-0.0001, 0), (0, 0.0001), (0, -0.0001)]:
                fig.add_trace(go.Scattermap(
                    lon=[lon + offset_x for lon in label_lons],
                    lat=[lat + offset_y for lat in label_lats],
                    mode='text',
                    text=label_texts,
                    textfont=dict(size=8, color='#000000', family='NanumGothic'),
                    hoverinfo='skip',
                    showlegend=False
                ))

            # 전경용 하얀 텍스트
            fig.add_trace(go.Scattermap(
                lon=label_lons,
                lat=label_lats,
                mode='text',
                text=label_texts,
                textfont=dict(size=8, color='#FFFFFF', family='NanumGothic', weight='bold'),
                hoverinfo='skip',
                showlegend=False
            ))

    return fig


def add_park_markers(
    fig: go.Figure,
    gdf_parks: gpd.GeoDataFrame,
    name: str = "공원 위치",
    color: str = PARK_COLOR
) -> go.Figure:
    """
    공원 마커 레이어 추가 (중심점)

    Args:
        fig: 기존 Plotly Figure
        gdf_parks: 공원 GeoDataFrame
        name: 레이어 이름
        color: 마커 색상

    Returns:
        go.Figure: 업데이트된 Figure
    """
    # Centroid 계산
    gdf_parks = gdf_parks.copy()
    gdf_parks['centroid'] = gdf_parks.geometry.centroid
    gdf_parks['lon'] = gdf_parks['centroid'].x
    gdf_parks['lat'] = gdf_parks['centroid'].y

    # 공원명 컬럼 자동 감지
    name_col = None
    for col in ['park_name', 'ENT_NAME', 'LABEL', 'name']:
        if col in gdf_parks.columns:
            name_col = col
            break

    # 면적 컬럼 자동 감지
    area_col = None
    for col in ['area', 'df_park_area_m2', 'AREA', 'area_m2']:
        if col in gdf_parks.columns:
            area_col = col
            break

    # 마커 크기 계산 (면적 기반)
    marker_sizes = 8
    if area_col:
        areas = gdf_parks[area_col].values
        # 면적을 로그 스케일로 변환
        import numpy as np
        log_areas = np.log10(areas + 1)
        # 5~20 범위로 정규화
        min_size, max_size = 5, 20
        if log_areas.max() > log_areas.min():
            marker_sizes = min_size + (log_areas - log_areas.min()) / (log_areas.max() - log_areas.min()) * (max_size - min_size)
        else:
            marker_sizes = 10

    # customdata 준비
    if name_col and area_col:
        customdata = gdf_parks[[name_col, area_col]].values
        hovertemplate = '<b>%{customdata[0]}</b><br>면적: %{customdata[1]:.0f} m²<br><extra></extra>'
    elif name_col:
        customdata = gdf_parks[[name_col]].values
        hovertemplate = '<b>%{customdata[0]}</b><br><extra></extra>'
    else:
        customdata = None
        hovertemplate = '<b>공원</b><br><extra></extra>'

    fig.add_trace(go.Scattermap(
        lon=gdf_parks['lon'],
        lat=gdf_parks['lat'],
        mode='markers',
        marker=dict(
            size=marker_sizes,
            color=color,
            opacity=0.9
        ),
        name=name,
        hovertemplate=hovertemplate,
        customdata=customdata
    ))

    return fig


def add_park_buffers(
    fig: go.Figure,
    gdf_buffers: gpd.GeoDataFrame,
    name: str = "공원 버퍼",
    color: str = BUFFER_COLOR,
    show_fill: bool = True
) -> go.Figure:
    """
    공원 버퍼 레이어 추가 (개별 버퍼 원형 표시)

    Args:
        fig: 기존 Plotly Figure
        gdf_buffers: 버퍼 GeoDataFrame
        name: 레이어 이름
        color: 색상 (선/채우기)
        show_fill: 채우기 표시 여부

    Returns:
        go.Figure: 업데이트된 Figure
    """
    # EPSG:4326 변환
    gdf_viz = gdf_buffers.copy()
    if gdf_viz.crs != 'EPSG:4326':
        gdf_viz = gdf_viz.to_crs('EPSG:4326')

    # ID 컬럼 확인
    if 'id' not in gdf_viz.columns:
        gdf_viz['id'] = gdf_viz.index.astype(str)

    # 버퍼를 반투명 polygon으로 표시 (Choroplethmapbox 사용)
    if show_fill:
        # GeoJSON 생성 및 sanitize
        geojson_buffers = json.loads(gdf_viz.to_json())
        geojson_buffers = _sanitize_geojson(geojson_buffers)

        # 공원명 컬럼 찾기
        park_name_col = None
        for col in ['PARK_NM', 'park_nm', 'name', 'NAME']:
            if col in gdf_viz.columns:
                park_name_col = col
                break

        fig.add_trace(go.Choroplethmap(
            geojson=geojson_buffers,
            locations=gdf_viz['id'].tolist(),
            z=[1] * len(gdf_viz),  # 동일한 값
            featureidkey="properties.id",
            colorscale=[[0, color], [1, color]],
            marker=dict(opacity=0.25, line=dict(width=0.5, color=color)),  # 더 연하게, 경계선 얇게
            hovertemplate='<b>%{customdata}</b><br>서비스 범위<br><extra></extra>' if park_name_col else '서비스 범위<br><extra></extra>',
            customdata=gdf_viz[park_name_col].tolist() if park_name_col else None,
            showscale=False,
            name=name
        ))
    else:
        # 경계선만 표시
        all_lons = []
        all_lats = []

        for idx, row in gdf_viz.iterrows():
            geom = row.geometry

            if geom.geom_type == 'Polygon':
                coords = list(geom.exterior.coords)
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                all_lons.extend(lons + [None])
                all_lats.extend(lats + [None])

            elif geom.geom_type == 'MultiPolygon':
                for poly in geom.geoms:
                    coords = list(poly.exterior.coords)
                    lons = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    all_lons.extend(lons + [None])
                    all_lats.extend(lats + [None])

        if all_lons:
            fig.add_trace(go.Scattermap(
                lon=all_lons,
                lat=all_lats,
                mode='lines',
                line=dict(width=2, color=color),  # 좀 더 굵게
                name=name,
                hoverinfo='skip',
                showlegend=True
            ))

    return fig


def add_grid_layer(
    fig: go.Figure,
    gdf_grid: gpd.GeoDataFrame,
    column: str = 'val',
    name: str = "인구 격자",
    colorscale: str = None
) -> go.Figure:
    """
    격자 인구 레이어 추가 (정확한 100m 격자 표시)

    Args:
        fig: 기존 Plotly Figure
        gdf_grid: 격자 GeoDataFrame
        column: 시각화할 컬럼
        name: 레이어 이름
        colorscale: 색상 스케일

    Returns:
        go.Figure: 업데이트된 Figure
    """
    # 격자는 단순화하지 않음 (정확한 100m 격자 유지)
    gdf_viz = gdf_grid.copy()

    # ID 컬럼 확인
    if 'id' not in gdf_viz.columns:
        gdf_viz['id'] = gdf_viz.index.astype(str)

    # GeoJSON 생성 및 sanitize
    geojson_grid = json.loads(gdf_viz.to_json())
    geojson_grid = _sanitize_geojson(geojson_grid)

    # 색상 스케일 설정 (QGIS 스타일 - 보라색 계열)
    if colorscale is None:
        colorscale = [
            [0.0, '#f7f7f7'],   # 연한 회색
            [0.2, '#d9d9f3'],   # 연한 보라
            [0.4, '#bcbddc'],   # 중간 보라
            [0.6, '#9e9ac8'],   # 보라
            [0.8, '#807dba'],   # 진한 보라
            [1.0, '#6a51a3']    # 매우 진한 보라
        ]

    # Choroplethmapbox 추가 (단일 trace로 성능 향상)
    fig.add_trace(go.Choroplethmap(
        geojson=geojson_grid,
        locations=gdf_viz['id'].tolist(),
        z=gdf_viz[column].tolist(),
        featureidkey="properties.id",
        colorscale=colorscale,
        marker=dict(opacity=0.6, line=dict(width=0.2, color='#404040')),  # 투명도 증가, 경계선 추가
        name=name,
        colorbar=dict(
            title=dict(text="인구수", font=dict(size=12, color='#E0E0E0')),
            thickness=15,
            len=0.7,
            x=1.1,
            tickfont=dict(color='#E0E0E0')
        ),
        hovertemplate='인구: %{z:.0f}명<br><extra></extra>',
        showscale=False  # 서비스 맵과 중복 방지
    ))

    return fig


def create_lisa_map(
    gdf: gpd.GeoDataFrame,
    cluster_col: str = 'cluster',
    title: str = "LISA 클러스터 지도"
) -> go.Figure:
    """
    LISA 클러스터 지도 생성 (QGIS/04.BI 패턴)

    Args:
        gdf: GeoDataFrame (cluster 컬럼 포함)
        cluster_col: 클러스터 컬럼명
        title: 지도 제목

    Returns:
        go.Figure: Plotly Figure
    """
    # Geometry 단순화
    gdf_viz = _simplify_geometry(gdf)

    # ID 컬럼 확인
    if 'id' not in gdf_viz.columns:
        gdf_viz['id'] = gdf_viz.index.astype(str)

    # GeoJSON 생성 및 sanitize (한 번만)
    geojson_all = json.loads(gdf_viz.to_json())
    geojson_all = _sanitize_geojson(geojson_all)

    # 동 이름 컬럼 자동 감지
    name_col = None
    for col in ['ADM_NM', 'adm_nm', 'DONG_NM', 'dong_nm', 'id']:
        if col in gdf_viz.columns:
            name_col = col
            break

    # Figure 생성
    fig = go.Figure()

    # 클러스터별 trace 추가 (NS → LL → LH → HL → HH 순서)
    for cluster in ['NS', 'LL', 'LH', 'HL', 'HH']:
        df_cluster = gdf_viz[gdf_viz[cluster_col] == cluster]

        if len(df_cluster) == 0:
            continue

        fig.add_trace(go.Choroplethmap(
            geojson=geojson_all,
            locations=df_cluster['id'].tolist(),
            z=[1] * len(df_cluster),  # 동일한 값 (색상만 구분)
            featureidkey="properties.id",
            colorscale=[[0, CLUSTER_COLORS[cluster]], [1, CLUSTER_COLORS[cluster]]],
            marker=dict(opacity=0.7, line=dict(width=0.5, color='white')),
            name=CLUSTER_LABELS[cluster],
            showscale=False,
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                          f'{CLUSTER_LABELS[cluster]}<br>' +
                          '<extra></extra>',
            customdata=df_cluster[[name_col]].values if name_col else df_cluster[['id']].values
        ))

    # 레이아웃 설정 (QGIS 스타일)
    fig.update_layout(
        map=dict(
            style='open-street-map',
            center=MAP_CENTER,
            zoom=MAP_ZOOM
        ),
        height=MAP_HEIGHT,
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(text=title, x=0.5, xanchor='center'),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.1,
            xanchor='center',
            x=0.5
        ),
        paper_bgcolor='#1e1e1e',
        plot_bgcolor='#1e1e1e',
        font=dict(color='#FFFFFF')
    )

    return fig


def add_boundary_lines(
    fig: go.Figure,
    gdf_boundary: gpd.GeoDataFrame,
    name: str = "경계",
    color: str = '#666666',
    width: float = 1.5
) -> go.Figure:
    """
    행정구역 경계선만 추가 (각 행정구역별 개별 경계, 메모리 효율적)

    Args:
        fig: 기존 Figure
        gdf_boundary: 경계 GeoDataFrame
        name: 레이어 이름
        color: 선 색상
        width: 선 두께

    Returns:
        go.Figure: 업데이트된 Figure
    """
    # EPSG:4326 변환
    gdf_viz = gdf_boundary.copy()
    if gdf_viz.crs != 'EPSG:4326':
        gdf_viz = gdf_viz.to_crs('EPSG:4326')

    # 각 행정구역의 경계선을 개별적으로 추가
    all_lons = []
    all_lats = []

    for idx, row in gdf_viz.iterrows():
        geom = row.geometry

        # Polygon or MultiPolygon 처리
        if geom.geom_type == 'Polygon':
            # Exterior 경계만 추출
            coords = list(geom.exterior.coords)
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]

            # None으로 구분 (연결 끊기)
            all_lons.extend(lons + [None])
            all_lats.extend(lats + [None])

        elif geom.geom_type == 'MultiPolygon':
            # 각 Polygon의 exterior 추출
            for poly in geom.geoms:
                coords = list(poly.exterior.coords)
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]

                all_lons.extend(lons + [None])
                all_lats.extend(lats + [None])

    # 단일 trace로 모든 경계선 추가 (성능 최적화, 정확한 경계)
    if all_lons:
        fig.add_trace(go.Scattermap(
            lon=all_lons,
            lat=all_lats,
            mode='lines',
            line=dict(width=width, color=color),
            name=name,
            hoverinfo='skip',
            showlegend=False  # 경계선은 범례에 표시 안 함
        ))

    return fig


def create_moran_scatter(
    y: np.ndarray,
    y_lag: np.ndarray,
    clusters: np.ndarray,
    moran_i: float,
    p_value: float,
    title: str = "Moran Scatter Plot"
) -> go.Figure:
    """
    Moran Scatter Plot 생성 (QGIS/04.BI 패턴)

    Args:
        y: 표준화된 변수값
        y_lag: 공간 지연 변수값
        clusters: 클러스터 분류 배열
        moran_i: Moran's I 값
        p_value: p-value
        title: 그래프 제목

    Returns:
        go.Figure: Plotly Figure
    """
    fig = go.Figure()

    # 클러스터별 scatter 추가
    cluster_order = ['NS', 'LL', 'LH', 'HL', 'HH']
    for cluster in cluster_order:
        mask = clusters == cluster
        if mask.sum() == 0:
            continue

        fig.add_trace(go.Scatter(
            x=y[mask],
            y=y_lag[mask],
            mode='markers',
            name=CLUSTER_LABELS[cluster],
            marker=dict(
                size=8,
                color=CLUSTER_COLORS[cluster],
                opacity=0.6,
                line=dict(width=0.5, color='white')
            )
        ))

    # 회귀선 추가
    z = np.polyfit(y, y_lag, 1)
    p = np.poly1d(z)
    x_line = np.linspace(y.min(), y.max(), 100)

    fig.add_trace(go.Scatter(
        x=x_line,
        y=p(x_line),
        mode='lines',
        name='Regression Line',
        line=dict(color='red', width=2, dash='dash'),
        showlegend=False
    ))

    # 레이아웃 설정
    fig.update_layout(
        title=dict(
            text=f"{title}<br>Moran's I = {moran_i:.4f} (p = {p_value:.4f})",
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(title="Standardized Value", zeroline=True, zerolinewidth=1),
        yaxis=dict(title="Spatial Lag", zeroline=True, zerolinewidth=1),
        height=500,
        hovermode='closest',
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02
        )
    )

    return fig


def add_sigungu_boundaries(
    fig: go.Figure,
    show_labels: bool = True,
    line_color: str = '#000000',  # 검정색으로 변경
    line_width: float = 3.0  # 더 굵게 변경
) -> go.Figure:
    """
    서울시 시군구 경계선 추가 (QGIS/04.BI 스타일)

    Args:
        fig: 기존 Plotly Figure
        show_labels: 시군구명 라벨 표시 여부
        line_color: 경계선 색상 (기본: 빨강)
        line_width: 경계선 두께

    Returns:
        go.Figure: 업데이트된 Figure
    """
    try:
        # 시군구 shapefile 로드
        gdf_sigungu = gpd.read_file(SIGUNGU_POLYGON_SHP, encoding='cp949')

        # EPSG:4326 변환
        if gdf_sigungu.crs != 'EPSG:4326':
            gdf_sigungu = gdf_sigungu.to_crs('EPSG:4326')

        # 서울시만 필터링 (시군구 코드 앞 2자리가 11인 것)
        gdf_sigungu['_sido_cd'] = gdf_sigungu['SIGUNGU_CD'].astype(str).str[:2]
        gdf_sigungu = gdf_sigungu[gdf_sigungu['_sido_cd'] == '11'].copy()

        # 경계선 좌표 추출
        all_lons = []
        all_lats = []

        for idx, row in gdf_sigungu.iterrows():
            geom = row.geometry

            if geom.geom_type == 'Polygon':
                coords = list(geom.exterior.coords)
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                all_lons.extend(lons + [None])
                all_lats.extend(lats + [None])

            elif geom.geom_type == 'MultiPolygon':
                for poly in geom.geoms:
                    coords = list(poly.exterior.coords)
                    lons = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    all_lons.extend(lons + [None])
                    all_lats.extend(lats + [None])

        # 경계선 추가
        if all_lons:
            fig.add_trace(go.Scattermap(
                lon=all_lons,
                lat=all_lats,
                mode='lines',
                line=dict(width=line_width, color=line_color),
                name='시군구 경계',
                hoverinfo='skip',
                showlegend=False
            ))

        # 라벨 추가
        if show_labels:
            label_lons = []
            label_lats = []
            label_texts = []

            for idx, row in gdf_sigungu.iterrows():
                centroid = row.geometry.centroid
                sigungu_nm = row.get('SIGUNGU_NM', '') or row.get('SIG_KOR_NM', '') or ''

                if sigungu_nm:
                    label_lons.append(centroid.x)
                    label_lats.append(centroid.y)
                    label_texts.append(sigungu_nm)

            if label_lons:
                # 배경용 하얀 텍스트 (테두리 효과)
                for offset_x, offset_y in [(-0.003, 0), (0.003, 0), (0, -0.003), (0, 0.003)]:
                    fig.add_trace(go.Scattermap(
                        lon=[lon + offset_x for lon in label_lons],
                        lat=[lat + offset_y for lat in label_lats],
                        mode='text',
                        text=label_texts,
                        textfont=dict(size=16, color='#FFFFFF', family='NanumGothic'),
                        hoverinfo='skip',
                        showlegend=False
                    ))

                # 전경용 검정 텍스트
                fig.add_trace(go.Scattermap(
                    lon=label_lons,
                    lat=label_lats,
                    mode='text',
                    text=label_texts,
                    textfont=dict(size=16, color='#000000', family='NanumGothic', weight='bold'),
                    hoverinfo='skip',
                    showlegend=False
                ))

        print(f"시군구 경계선 추가 완료: {len(gdf_sigungu)}개 구역")

    except Exception as e:
        print(f"시군구 경계선 로드 실패: {e}")
        import traceback
        traceback.print_exc()

    return fig
