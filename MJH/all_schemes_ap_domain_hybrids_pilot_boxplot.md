all_schemes_ap_domain_hybrids_pilot_boxplot.py 실행법

python all_schemes_ap_domain_hybrids_pilot_boxplot.py --mode all --setups 10 --power-control full --plot  --w-aa 2 --w-ai 1 --w-ia 1 --edge-threshold 10 --schemes random greedy wgf gc topap-bisect h2 h3 h4 proposed matching-fixed matching-adaptive --pilot-boxplot --pilot-boxplot-schemes topap-bisect h3 h4 proposed matching-adaptive --outdir result_boxplot_ap_domain_weighted_2_1_1_10_full

--mode all : eCDF, 안테나 수에 따른 SE & EE, 사용자 수에 따른 SE & EE 모두 출력
--setups 10 : 우선 10번만 realization -> 200으로 바꾸는게 정석
--power-control full : 최대 전력 사용
--w-aa, w-ai, w-ia : 빔 간섭 행렬 B 생성 시의 가중치
--edge-threshold 10 : 가중치 합산이 10 이어야 edge 생성 (새로운 pilot 배정)

이외에는 출력할 scheme 들을 설정하고, boxplot 출력에 대한 설정이며, 이들은 크게 바꿀 필요는 없어 보인다.
