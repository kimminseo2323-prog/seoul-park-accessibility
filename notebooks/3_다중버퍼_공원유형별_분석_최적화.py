"""
다중 버퍼 거리 및 공원 유형별 2SFCA 분석 (최적화 버전)
- 버퍼: 100m, 300m, 500m, 1000m
- 공원 유형: 전체, 어린이공원, 근린공원, 소공원 등
- 최적화: 공간 인덱스 사용, 버퍼 사전 계산
"""
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point
import warnings
import time
warnings.filterwarnings('ignore')

def gini_coefficient(x):
    """Gini 계수 계산"""
    x = np.array(x)
    x = x[x > 0]
    if len(x) == 0:
        return 0
    x = np.sort(x)
    n = len(x)
    index = np.arange(1, n + 1)
    return (2 * np.sum(index * x)) / (n * np.sum(x)) - (n + 1) / n

def calculate_2sfca_optimized(grid_gdf, park_gdf, dong_gdf, buffer_distance, park_type_filter=None):
    """
    2SFCA 분석 수행 (최적화 버전)

    최적화 사항:
    1. 버퍼를 미리 계산하여 재사용
    2. 공간 인덱스(spatial index) 활용
    3. NumPy 벡터화 연산 사용
    """
    print(f"\n{'='*80}")
    print(f"분석 시작: 버퍼={buffer_distance}m, 공원유형={park_type_filter or '전체'}")
    print(f"{'='*80}")
    start_time = time.time()

    # 공원 유형 필터링
    if park_type_filter:
        park_gdf_filtered = park_gdf[park_gdf['park_type'].isin(park_type_filter)].copy()
        print(f"  필터링된 공원 수: {len(park_gdf_filtered)} / {len(park_gdf)}")
    else:
        park_gdf_filtered = park_gdf.copy()
        print(f"  전체 공원 수: {len(park_gdf_filtered)}")

    # Step 1: 공원별 버퍼와 공급-수요 비율 계산
    print("\nStep 1: 공원별 버퍼 및 공급-수요 비율 계산 중...")
    park_supply_demand_ratio = {}
    park_buffers = {}

    for idx, park in park_gdf_filtered.iterrows():
        park_area_m2 = park['df_park_area_km2'] * 1_000_000

        # 버퍼 미리 계산 (재사용)
        buffer_geom = park.geometry.buffer(buffer_distance)
        park_buffers[idx] = buffer_geom

        # 버퍼 내 격자 찾기 (공간 인덱스 활용)
        possible_matches_idx = list(grid_gdf.sindex.intersection(buffer_geom.bounds))
        possible_matches = grid_gdf.iloc[possible_matches_idx]

        # 실제 교차 확인
        grids_in_buffer = possible_matches[possible_matches.geometry.centroid.within(buffer_geom)]
        total_demand = grids_in_buffer['val'].sum()

        if total_demand > 0:
            R_j = park_area_m2 / total_demand
        else:
            R_j = 0

        park_supply_demand_ratio[idx] = R_j

    print(f"  완료: {len(park_gdf_filtered)}개 공원 (소요시간: {time.time()-start_time:.1f}초)")

    # Step 2: 격자-행정동 매칭
    print("\nStep 2: 격자-행정동 매칭 중...")
    step2_start = time.time()
    grid_with_dong = gpd.sjoin(
        grid_gdf,
        dong_gdf[['ADM_NM', 'SIGUNGU_NM', 'geometry']],
        how='left',
        predicate='within'
    )
    print(f"  완료: {len(grid_with_dong):,}개 격자 매칭 (소요시간: {time.time()-step2_start:.1f}초)")

    # Step 3: 행정동별 서비스 점수 집계 (최적화)
    print("\nStep 3: 행정동별 서비스 점수 집계 중...")
    step3_start = time.time()
    dong_results = []

    dong_names = dong_gdf['ADM_NM'].unique()
    total_dongs = len(dong_names)

    for dong_idx, dong_name in enumerate(dong_names):
        # 진행률 표시 (10개마다)
        if dong_idx % 10 == 0 or dong_idx == total_dongs - 1:
            elapsed = time.time() - step3_start
            progress = (dong_idx + 1) / total_dongs * 100
            eta = (elapsed / (dong_idx + 1)) * (total_dongs - dong_idx - 1) if dong_idx > 0 else 0
            print(f"  진행: {dong_idx+1}/{total_dongs} ({progress:.1f}%) | "
                  f"소요시간: {elapsed:.1f}초 | 예상 남은시간: {eta:.1f}초")

        dong_grids = grid_with_dong[grid_with_dong['ADM_NM'] == dong_name]
        total_pop = dong_grids['val'].sum()

        if total_pop == 0:
            continue

        service_score = 0
        covered_grids = set()

        # 격자별 처리
        for _, grid in dong_grids.iterrows():
            grid_centroid = grid.geometry.centroid
            grid_pop = grid['val']
            grid_id = grid['gid']

            # 격자 주변 공원 찾기 (공간 인덱스 활용)
            for park_idx in park_buffers.keys():
                buffer_geom = park_buffers[park_idx]

                if grid_centroid.within(buffer_geom):
                    R_j = park_supply_demand_ratio[park_idx]
                    service_score += R_j * grid_pop
                    covered_grids.add(grid_id)
                    break  # 하나라도 커버되면 다음 격자로

        # 커버된 인구
        covered_pop = dong_grids[dong_grids['gid'].isin(covered_grids)]['val'].sum()

        # 1인당 평균
        avg_service = service_score / total_pop if total_pop > 0 else 0
        coverage_ratio = (covered_pop / total_pop) * 100 if total_pop > 0 else 0

        dong_results.append({
            'ADM_NM': dong_name,
            'SIGUNGU_NM': dong_grids['SIGUNGU_NM'].iloc[0] if len(dong_grids) > 0 else '',
            'buffer_distance': buffer_distance,
            'park_types': ','.join(park_type_filter) if park_type_filter else '전체',
            'total_population': int(total_pop),
            'covered_population': int(covered_pop),
            'coverage_ratio': round(coverage_ratio, 2),
            'total_service_score': round(service_score, 2),
            'avg_service_per_capita': round(avg_service, 2)
        })

    print(f"\n  완료: {len(dong_results)}개 행정동 (소요시간: {time.time()-step3_start:.1f}초)")

    # DataFrame 생성
    dong_service_df = pd.DataFrame(dong_results)

    # 통계 계산
    avg_score = dong_service_df['avg_service_per_capita'].mean()
    avg_coverage = dong_service_df['coverage_ratio'].mean()
    gini = gini_coefficient(dong_service_df['avg_service_per_capita'].values)

    print(f"\n분석 결과:")
    print(f"  평균 서비스 점수: {avg_score:.4f} m²/인")
    print(f"  평균 커버리지: {avg_coverage:.2f}%")
    print(f"  Gini 계수: {gini:.4f}")
    print(f"  총 소요시간: {time.time()-start_time:.1f}초")

    return {
        'data': dong_service_df,
        'stats': {
            'buffer_distance': buffer_distance,
            'park_types': ','.join(park_type_filter) if park_type_filter else '전체',
            'total_dongs': len(dong_results),
            'avg_service': round(avg_score, 4),
            'gini_coefficient': round(gini, 4),
            'avg_coverage': round(avg_coverage, 2),
            'processing_time_sec': round(time.time()-start_time, 1)
        }
    }

def main():
    print("="*80)
    print("다중 버퍼 거리 및 공원 유형별 2SFCA 분석 (최적화 버전)")
    print("="*80)
    overall_start = time.time()

    # 경로 설정
    base_path = Path('c:/Users/user/Desktop/Project_skku/s1_data/s2_processed_data')
    output_path = Path('c:/Users/user/Desktop/Project_skku/s1_data/s2_processed_data')

    # 데이터 로드
    print("\n1. 데이터 로드 중...")
    load_start = time.time()
    grid_gdf = gpd.read_file(base_path / 'seoul_100m_grid_population.shp')
    park_gdf = gpd.read_file(base_path / 'seoul_parks.geojson')
    dong_gdf = gpd.read_file(base_path / 'seoul_dong_with_pop.geojson')

    print(f"  격자 수: {len(grid_gdf):,}개")
    print(f"  공원 수: {len(park_gdf):,}개")
    print(f"  행정동 수: {len(dong_gdf):,}개")
    print(f"  로드 완료 (소요시간: {time.time()-load_start:.1f}초)")

    # 좌표계 통일
    print("\n2. 좌표계 통일 중...")
    crs_start = time.time()
    if grid_gdf.crs != 'EPSG:5179':
        grid_gdf = grid_gdf.to_crs('EPSG:5179')
    if park_gdf.crs != 'EPSG:5179':
        park_gdf = park_gdf.to_crs('EPSG:5179')
    if dong_gdf.crs != 'EPSG:5179':
        dong_gdf = dong_gdf.to_crs('EPSG:5179')
    print(f"  완료: EPSG:5179 (소요시간: {time.time()-crs_start:.1f}초)")

    # 공원 유형 추출
    print("\n3. 공원 유형 추출 중...")
    park_gdf['park_type'] = park_gdf['LABEL'].str.extract(r'^([^(]+)')[0].str.strip()
    park_types = sorted(park_gdf['park_type'].unique().tolist())
    print(f"  공원 유형 ({len(park_types)}개): {park_types}")

    # 버퍼 거리 설정
    buffer_distances = [100, 300, 500, 1000]

    # 분석 실행
    all_results = []
    all_stats = []

    print("\n4. 분석 실행 중...")
    print(f"  전체 작업: {len(buffer_distances)}개 버퍼 + {len(park_types)}개 공원유형")

    # 전체 공원 분석 (모든 버퍼)
    print("\n" + "="*80)
    print("전체 공원 분석 (4개 버퍼)")
    print("="*80)
    for buffer_dist in buffer_distances:
        result = calculate_2sfca_optimized(grid_gdf, park_gdf, dong_gdf, buffer_dist, park_type_filter=None)
        if result:
            all_results.append(result['data'])
            all_stats.append(result['stats'])

    # 공원 유형별 분석 (500m만)
    print("\n\n" + "="*80)
    print(f"공원 유형별 분석 ({len(park_types)}개 유형, 버퍼 500m)")
    print("="*80)
    for park_type in park_types:
        result = calculate_2sfca_optimized(grid_gdf, park_gdf, dong_gdf, 500, park_type_filter=[park_type])
        if result:
            all_results.append(result['data'])
            all_stats.append(result['stats'])

    # 결과 저장
    print("\n5. 결과 저장 중...")
    save_start = time.time()

    # 통합 데이터
    combined_df = pd.concat(all_results, ignore_index=True)
    output_file = output_path / 'dong_service_score_multi_buffer_parktype.csv'
    combined_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"  저장 완료: {output_file.name} ({len(combined_df):,}행)")

    # 통계 요약
    stats_df = pd.DataFrame(all_stats)
    output_stats = output_path / 'analysis_stats_summary.csv'
    stats_df.to_csv(output_stats, index=False, encoding='utf-8-sig')
    print(f"  저장 완료: {output_stats.name} ({len(stats_df)}개 조합)")

    # GeoJSON 생성 (기본 버퍼별)
    print("\n6. GeoJSON 생성 중...")
    for buffer_dist in buffer_distances:
        buffer_data = combined_df[
            (combined_df['buffer_distance'] == buffer_dist) &
            (combined_df['park_types'] == '전체')
        ]

        if len(buffer_data) > 0:
            dong_service_gdf = dong_gdf.merge(
                buffer_data[['ADM_NM', 'avg_service_per_capita', 'coverage_ratio']],
                on='ADM_NM',
                how='left'
            )

            # EPSG:4326 변환
            dong_service_gdf = dong_service_gdf.to_crs('EPSG:4326')

            output_geo = output_path / f'dong_service_score_{buffer_dist}m.geojson'
            dong_service_gdf.to_file(output_geo, driver='GeoJSON', encoding='utf-8')
            print(f"  저장 완료: {output_geo.name}")

    print(f"\n  저장 완료 (소요시간: {time.time()-save_start:.1f}초)")

    # 최종 요약
    total_time = time.time() - overall_start
    print("\n" + "="*80)
    print("분석 완료!")
    print("="*80)
    print(f"\n생성된 파일:")
    print(f"  1. dong_service_score_multi_buffer_parktype.csv - 전체 분석 결과 ({len(combined_df):,}행)")
    print(f"  2. analysis_stats_summary.csv - 통계 요약 ({len(stats_df)}개 조합)")
    print(f"  3. dong_service_score_[버퍼]m.geojson - 버퍼별 GeoJSON (4개)")
    print(f"\n총 소요시간: {total_time/60:.1f}분 ({total_time:.1f}초)")
    print("="*80)

if __name__ == '__main__':
    main()
