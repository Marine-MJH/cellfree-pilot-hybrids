# 안테나별 Sweep

우선 아래 그림과 같이 안테나 값은 `1, 2, 4, 8`에서만 값을 그리되, x축의 `N` 인덱스는 `1~8`까지 다 나오게 한다. 그리고 그래프가 길기 때문에 `4:3` 비율로 변환한다.

<img width="1125" height="742" alt="image" src="https://github.com/user-attachments/assets/ded1a49b-bd62-49de-86e1-c94e766c4c4b" />

Mussbah는 들어가도 상관 없을 것 같다.

## 1. eCDF

<img width="2208" height="1152" alt="image" src="https://github.com/user-attachments/assets/041f141d-b45e-484c-857c-40f2b9d05aba" />

## 2. SE와 EE 비교

여기서는 빔 도메인 기법들이 SE와 달리 EE에서 안테나가 커질수록 AP 기반 기법들보다 상대적으로 더 좋아지는 모습을 보임.

→ Active beam 선택으로 인한 active RF chain이 적게 선택되는 것. 또한 안테나가 많아질수록 RF chain on/off의 효과가 커짐을 보임.

<img width="1820" height="1222" alt="image" src="https://github.com/user-attachments/assets/befb5d2a-efea-4add-a37e-b7b6e6577489" />

<img width="1820" height="1222" alt="image" src="https://github.com/user-attachments/assets/79a09068-5b85-46ff-af0d-3531744d4e3e" />

## 3. SE와 Pilot Count 비교

SE와 Pilot count를 비교하여서 Random과 Beam Weighted 방식이 crossover하는 곳이 정확히 pilot 수가 crossover하는 곳임을 보이기.

---

# 사용자별 Sweep - 25 ~ 50의 낮은 구간 부분

마찬가지로 Mussbah가 들어가도 상관 없을 것 같다.
마찬가지로 `4:3` 정도로 줄이기.

## 1. eCDF

## 2. SE와 EE 비교

여기서는 빔 도메인 기법들이 EE에서 더 좋은 모습을 보임.

SE에서는 비슷한 성능이었던 Beam Resource Matching과 AP Top-N이 EE에서는 차이를 보이고, Random보다도 SE가 낮아졌던 Beam Weighted는 EE에서는 더 높아지고 Top-N과 비슷해지는 모습을 보임.

반면에 Mussbah는 pilot을 거의 사용자 수인 50개까지 사용하면서 data transmission rate을 0.5 정도로 낮게 떨어뜨리며 EE가 매우 낮아지는 모습을 보임.

또한 이 경우 Active beam이 너무 많아지면서 RF chain on/off의 효과도 떨어짐.

## 3. SE와 Pilot Count 비교

여기서도 마찬가지로 사용하는 Pilot 수에 따라 SE 성능이 동일하게 반영되는 것을 보임.

---

# 사용자별 Sweep - 25~50 부분과 50~300 부분 같이 확인

우선 `50~300`의 high K 그래프는 `K=300`인 값을 지우고 `50~250` 부분만 사용한다.

이유는 EE 그래프에서 빔이든 AP 기반이든 성능이 떨어지는 건 설명할 수 있으나, Random은 떨어지지 않고 Beam Resource Matching보다 높아지는 것은 아직 설명할 방법이 없다.

## 1. Low K, High K끼리 SE 비교

Low K의 SE에서 Random의 성능 저하 기울기보다 Top-N과 Beam Resource Matching의 성능 저하 기울기가 높았다.

실제 High K 실험 결과 Random과 Top-N은 교차하였고, 다만 Beam Resource Matching은 Random과 붙는 모습을 보였다.

Mussbah는 이미 `τ_c`에 해당하는 pilot을 전부 사용하여 정보 전송을 못하는 상태라 `SE = 0`이 된다.

## 2. High K끼리 SE, EE 비교

SE에서는 Top-N과 Random이 crossover가 발생하고, Beam Resource Matching은 Random과 붙어 가는 것을 보임.

EE에서는 어느 순간 유지하지 못하고 떨어지기 시작하는 점이 존재. 이는 결국 Pilot을 많이 사용하면서 data transmission rate이 떨어지기 때문이다.

반면 Pilot 수에 상한이 있는 Beam Resource Matching 방식은 점점 Random과 붙는 모습을 보임.

## 3. High K끼리 SE, Pilot Count 비교

마찬가지로 Pilot 수가 겹치는 곳에서 crossover 발생.

Beam Resource Matching은 `τ_p` 상한인 15로 Random과 같은 pilot 수로 점근해 나아감.

Mussbah는 이미 `τ_c` 상한인 150을 넘겨서 `data transmission rate = 0`이 되어 `SE = 0`이 된 상황.
