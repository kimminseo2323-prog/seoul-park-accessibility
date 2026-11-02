"""
데이터 로더 모듈 (QGIS/04.BI 패턴 적용)
"""
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, Tuple, Optional
from .config import (
    GEOJSON_DONG, GEOJSON_DONG_SERVICE, GEOJSON_PARKS, SHAPEFILE_GRID,
    CSV_2SFCA, CSV_2SFCA_MULTI, CSV_PARK_COVERAGE, CSV_SIGUNGU_COMPARISON
)


class DataLoader:
    """데이터 로딩 및 전처리 클래스"""

    def __init__(self):
        self._cache = {}

    def load_dong_geometry(self) -> gpd.GeoDataFrame:
        """
        행정동 경계 GeoDataFrame 로드

        Returns:
            gpd.GeoDataFrame: 행정동 경계 데이터
        """
        if 'dong_geometry' not in self._cache:
            gdf = gpd.read_file(GEOJSON_DONG)

            # CRS 확인 및 설정
            if gdf.crs is None:
                gdf = gdf.set_crs('EPSG:4326')
            elif gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')

            self._cache['dong_geometry'] = gdf

        return self._cache['dong_geometry'].copy()

    def load_parks(self) -> gpd.GeoDataFrame:
        """
        공원 데이터 로드

        Returns:
            gpd.GeoDataFrame: 공원 위치 및 속성 데이터
        """
        if 'parks' not in self._cache:
            gdf = gpd.read_file(GEOJSON_PARKS)

            # CRS 확인 및 설정
            if gdf.crs is None:
                gdf = gdf.set_crs('EPSG:4326')
            elif gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')

            self._cache['parks'] = gdf

        return self._cache['parks'].copy()

    def load_grid(self) -> gpd.GeoDataFrame:
        """
        100m 격자 인구 데이터 로드

        Returns:
            gpd.GeoDataFrame: 격자 인구 데이터
        """
        if 'grid' not in self._cache:
            gdf = gpd.read_file(SHAPEFILE_GRID)

            # CRS 확인 및 설정
            if gdf.crs is None:
                gdf = gdf.set_crs('EPSG:5179')

            # EPSG:4326으로 변환 (지도 표시용)
            if gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')

            self._cache['grid'] = gdf

        return self._cache['grid'].copy()

    def load_2sfca_results(self) -> pd.DataFrame:
        """
        2SFCA 분석 결과 로드

        Returns:
            pd.DataFrame: 동별 서비스 접근성 점수
        """
        if '2sfca' not in self._cache:
            df = pd.read_csv(CSV_2SFCA, encoding='utf-8-sig')
            self._cache['2sfca'] = df

        return self._cache['2sfca'].copy()

    def load_2sfca_multi_buffer(self) -> pd.DataFrame:
        """
        다중 버퍼 및 공원 유형별 2SFCA 분석 결과 로드

        Returns:
            pd.DataFrame: 버퍼별/공원유형별 서비스 접근성 점수
        """
        if '2sfca_multi' not in self._cache:
            df = pd.read_csv(CSV_2SFCA_MULTI, encoding='utf-8-sig')
            self._cache['2sfca_multi'] = df

        return self._cache['2sfca_multi'].copy()

    def load_park_coverage(self) -> pd.DataFrame:
        """
        공원별 서비스 커버리지 데이터 로드

        Returns:
            pd.DataFrame: 공원별 커버리지 통계
        """
        if 'park_coverage' not in self._cache:
            df = pd.read_csv(CSV_PARK_COVERAGE, encoding='utf-8-sig')
            self._cache['park_coverage'] = df

        return self._cache['park_coverage'].copy()

    def load_sigungu_comparison(self) -> pd.DataFrame:
        """
        시군구별 비교 데이터 로드

        Returns:
            pd.DataFrame: 시군구별 서비스 통계
        """
        if 'sigungu_comparison' not in self._cache:
            df = pd.read_csv(CSV_SIGUNGU_COMPARISON, encoding='utf-8-sig')
            self._cache['sigungu_comparison'] = df

        return self._cache['sigungu_comparison'].copy()

    def merge_2sfca_with_geometry(self) -> gpd.GeoDataFrame:
        """
        2SFCA 결과와 행정동 경계 병합 (v2 방식 - 이미 병합된 GeoJSON 로드)

        Returns:
            gpd.GeoDataFrame: 서비스 점수가 포함된 행정동 GeoDataFrame
        """
        if 'merged_2sfca' not in self._cache:
            # dong_service_score.geojson 직접 로드 (v2 방식 - 데이터 무결성 보장)
            gdf = gpd.read_file(GEOJSON_DONG_SERVICE)

            # CRS 확인 및 설정
            if gdf.crs is None:
                gdf = gdf.set_crs('EPSG:4326')
            elif gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')

            self._cache['merged_2sfca'] = gdf

        return self._cache['merged_2sfca'].copy()

    def filter_by_sigungu(
        self,
        gdf: gpd.GeoDataFrame,
        sigungu_list: list
    ) -> gpd.GeoDataFrame:
        """
        시군구 필터링 (QGIS/04.BI 패턴)

        Args:
            gdf: 필터링할 GeoDataFrame
            sigungu_list: 시군구 이름 리스트

        Returns:
            gpd.GeoDataFrame: 필터링된 GeoDataFrame
        """
        if not sigungu_list or '전체' in sigungu_list:
            return gdf

        # 시군구 컬럼 자동 감지
        sigungu_col = None
        for col in ['SIGUNGU_NM', 'sigungu_nm', 'SGG_NM', 'sgg_nm']:
            if col in gdf.columns:
                sigungu_col = col
                break

        if sigungu_col is None:
            return gdf

        return gdf[gdf[sigungu_col].isin(sigungu_list)].copy()

    def spatial_filter_parks(
        self,
        gdf_parks: gpd.GeoDataFrame,
        gdf_boundary: gpd.GeoDataFrame,
        predicate: str = 'intersects'
    ) -> gpd.GeoDataFrame:
        """
        경계 기준으로 공원 필터링 (공간 조인 사용)

        Args:
            gdf_parks: 공원 GeoDataFrame
            gdf_boundary: 경계 GeoDataFrame
            predicate: 공간 관계 조건 ('intersects', 'within' 등)

        Returns:
            gpd.GeoDataFrame: 필터링된 공원 데이터
        """
        # 공간 조인으로 100배 이상 빠른 필터링
        gdf_filtered = gpd.sjoin(
            gdf_parks,
            gdf_boundary[['geometry']],
            how='inner',
            predicate=predicate
        )

        # 중복 제거 (여러 경계와 교차하는 경우)
        gdf_filtered = gdf_filtered.drop_duplicates(subset=['geometry'])

        return gdf_filtered

    def spatial_filter_grid(
        self,
        gdf_grid: gpd.GeoDataFrame,
        gdf_boundary: gpd.GeoDataFrame,
        predicate: str = 'intersects',
        min_population: int = 100
    ) -> gpd.GeoDataFrame:
        """
        경계 기준으로 격자 필터링 + 인구 임계값 적용

        Args:
            gdf_grid: 격자 GeoDataFrame
            gdf_boundary: 경계 GeoDataFrame
            predicate: 공간 관계 조건
            min_population: 최소 인구 임계값

        Returns:
            gpd.GeoDataFrame: 필터링된 격자 데이터
        """
        # 공간 조인
        gdf_filtered = gpd.sjoin(
            gdf_grid,
            gdf_boundary[['geometry']],
            how='inner',
            predicate=predicate
        )

        # 인구 임계값 필터링 (있는 경우)
        if 'pop' in gdf_filtered.columns:
            gdf_filtered = gdf_filtered[gdf_filtered['pop'] >= min_population]
        elif 'val' in gdf_filtered.columns:
            gdf_filtered = gdf_filtered[gdf_filtered['val'] >= min_population]

        return gdf_filtered

    def create_park_buffers(
        self,
        gdf_parks: gpd.GeoDataFrame,
        buffer_distance: int = 500
    ) -> gpd.GeoDataFrame:
        """
        공원 버퍼 생성 (EPSG:5179에서 버퍼 → EPSG:4326 변환)

        Args:
            gdf_parks: 공원 GeoDataFrame (EPSG:4326)
            buffer_distance: 버퍼 거리 (미터)

        Returns:
            gpd.GeoDataFrame: 버퍼가 적용된 GeoDataFrame (EPSG:4326)
        """
        # EPSG:5179로 변환 (미터 단위)
        gdf_5179 = gdf_parks.to_crs('EPSG:5179')

        # 버퍼 적용
        gdf_5179['geometry'] = gdf_5179.geometry.buffer(buffer_distance)

        # EPSG:4326으로 다시 변환
        gdf_buffered = gdf_5179.to_crs('EPSG:4326')

        return gdf_buffered

    def get_sigungu_list(self) -> list:
        """
        고유한 시군구 리스트 반환

        Returns:
            list: 시군구 이름 리스트
        """
        gdf_dong = self.load_dong_geometry()

        sigungu_col = None
        for col in ['sigungu_nm', 'SIGUNGU_NM', 'sgg_nm', 'SGG_NM']:
            if col in gdf_dong.columns:
                sigungu_col = col
                break

        if sigungu_col is None:
            return []

        sigungu_list = sorted(gdf_dong[sigungu_col].unique().tolist())
        return ['전체'] + sigungu_list

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
