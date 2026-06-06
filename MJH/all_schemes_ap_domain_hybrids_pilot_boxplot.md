# `all_schemes_ap_domain_hybrids_pilot_boxplot.py` 실행법

## 실행 명령어

```bash
python all_schemes_ap_domain_hybrids_pilot_boxplot.py --mode all --setups 10 --power-control full --plot --w-aa 2 --w-ai 1 --w-ia 1 --edge-threshold 10 --schemes random greedy wgf gc topap-bisect h2 h3 h4 proposed matching-fixed matching-adaptive --pilot-boxplot --pilot-boxplot-schemes topap-bisect h3 h4 proposed matching-adaptive --outdir result_boxplot_ap_domain_weighted_2_1_1_10_full
```

---

## 주요 옵션 설명

| 옵션 | 설명 |
|---|---|
| `--mode all` | eCDF, 안테나 수에 따른 SE & EE, 사용자 수에 따른 SE & EE 모두 출력 |
| `--setups 10` | 우선 10번만 realization 수행. 정식 실험에서는 `200`으로 바꾸는 것이 적절 |
| `--power-control full` | 최대 전력 사용 |
| `--w-aa 2` | 빔 간섭 행렬 `B` 생성 시 AP-AP 간섭 가중치 |
| `--w-ai 1` | 빔 간섭 행렬 `B` 생성 시 AP-Interference 간섭 가중치 |
| `--w-ia 1` | 빔 간섭 행렬 `B` 생성 시 Interference-AP 간섭 가중치 |
| `--edge-threshold 10` | 가중치 합산이 `10` 이상일 때 edge 생성 후 새로운 pilot 배정 |
| `--schemes ...` | 비교할 pilot assignment scheme 목록 |
| `--pilot-boxplot` | pilot 사용량 비교를 위한 boxplot 출력 |
| `--pilot-boxplot-schemes ...` | boxplot에 포함할 scheme 목록 |
| `--outdir ...` | 결과 파일 및 그래프가 저장될 폴더 경로 |

---

## 참고 사항

- `--setups 10`은 빠른 실행 확인을 위한 설정이다.
- 정식 실험 또는 보고서용 결과를 얻기 위해서는 `--setups 200` 정도로 설정하는 것이 적절하다.
- `--power-control full`은 모든 사용자가 최대 전력을 사용하는 방식이다.
- `--w-aa`, `--w-ai`, `--w-ia`는 빔 간섭 행렬 `B`를 생성할 때 사용되는 가중치이다.
- `--edge-threshold 10`은 가중치 합산 값이 `10` 이상일 때 edge를 생성하고, 이를 기반으로 새로운 pilot을 배정한다.
- 이외의 옵션들은 출력할 scheme 목록과 boxplot 출력 설정에 해당하며, 일반적인 실험에서는 크게 바꿀 필요가 없어 보인다.
