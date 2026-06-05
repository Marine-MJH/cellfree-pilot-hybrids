# Note for proposing beam domain with threshold

def parse_args() -> argparse.Namespace: 에 있는 args 값들을 설정하여 실행한다.

Ex. python .\Beam_domain_all_schemes_with_weighted_threshold.py --mode sweep-k --setups 10 --power-control maxmin --proposed-graph weighted-count --w-aa 2 --w-am 1 --weight-threshold 10 --plot --outdir test_figure_test

- mode :

1. fig1 : eCDF
2. sweep-n : antennas
3. sweep-k : users

- setups :
  number of montecarlo iterations
- power-control :

1. full : 모든 파일럿 전력 최대값 동일 할당
2. maxmin : 논문과 같이 maxmin으로 할당

- proposed-graph-weighted-count :

1. w-aa : active-active beam interference 에 대한 가중치
2. w-am : active-moderate “” 에 대한 가중치

- weight-threshold :
  위에서 설정한 weight를 이용해 구한 가중 빔간 간섭 수 matrix 에서 새로운 color(pilot)를 배정하게 되는 임계값. Vertex 간 edge가 해당 임계값을 넘지 못하면 새로운 color를 배정하지 않아도 된다.
- outdir :
  figure 저장 위치
