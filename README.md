# kiwoom_static_scanner

Kiwoom REST API 기반 순환식 종목 스캐너 MVP v2.

## 주요 기능

- Kiwoom REST 토큰 발급/캐시
- 종목 자동 수집 인터페이스
- 일봉 OHLCV fetch
- MA5, MA20, MA60, MA120 실계산
- 조건 분석
  - 조건 1: `MA5 > MA20 > MA60 AND PER < 5.0 AND PBR < 0.5`
  - 조건 2: `MA5 > MA120`
- 429 발생 시 자동 감속
- 1분 단위 Telegram batch 발송
- SQLite 저장

## 실행

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

copy config.example.yaml config.yaml   # Windows
# cp config.example.yaml config.yaml   # macOS/Linux

python main.py
```

## 중요

`config.yaml`은 Git에 올리지 마세요.  
AppKey, SecretKey, Telegram Bot Token은 반드시 개인 로컬 설정에만 저장하세요.

## Kiwoom API 설정

Kiwoom REST API는 요청별 `api-id`가 중요합니다.  
본 프로젝트는 아래 값을 `config.yaml`에서 바꿔 끼울 수 있게 만들었습니다.

```yaml
kiwoom:
  endpoints:
    token: "/oauth2/token"
    stock_info: "/api/dostk/stkinfo"
    daily_chart: "/api/dostk/chart"
    stock_list: "/api/dostk/stkinfo"
  api_ids:
    daily_chart: "ka10081"
    stock_info: "ka10001"
    stock_list_kospi: "ka10099"
    stock_list_kosdaq: "ka10100"
```

실제 사용 전 Kiwoom OpenAPI REST 가이드에서 `api-id`, 요청 body key, 응답 field명을 확인하세요.  
필드명이 다르면 `app/kiwoom/response_parser.py`에서 매핑만 수정하면 됩니다.


## v2.1 수정 사항

- mock 날짜 생성 오류 수정
  - 기존: 임시 `2026xxxx` 날짜
  - 수정: 실행일 기준 최근 영업일 YYYYMMDD 생성
- mock OHLCV 값을 종목별 deterministic random으로 변경
- MA 조건 테스트가 가능하도록 일부 샘플 종목에 상승 추세 적용
- `scripts/check_mock_data.py` 추가

```bash
python scripts/check_mock_data.py
```


## GUI 실행

```bash
pip install -r requirements.txt
copy config.example.yaml config.yaml
python gui_main.py
```

## GUI 개선안

1. 스캐너는 QThread에서 실행하고 GUI는 Signal로 상태만 받습니다.
2. Start/Stop 버튼으로 안전하게 제어합니다.
3. 현재 종목, 진행률, 호출 속도, MA/PER/PBR, 조건 감지 상태를 실시간 표시합니다.
4. 조건 감지 종목은 테이블에 누적 표시합니다.
5. 로그창에서 429 감속, 오류, 텔레그램 발송 상태를 확인할 수 있습니다.
6. 다음 개선 후보:
   - 설정값을 GUI에서 직접 수정하고 config.yaml 저장
   - 종목 필터/검색 기능
   - 조건 Builder UI
   - SQLite 결과 조회 탭
   - 관심종목 빠른 스캐너 별도 스레드
   - 시스템 트레이 상주 모드


## v2 GUI Patch

- `ka10099` KOSPI, `ka10100` KOSDAQ 종목 수집 분리
- 시작 시 `symbols` 테이블 전체 교체로 mock 잔존 종목 제거
- GUI 로그에 KOSPI/KOSDAQ/TOTAL 종목 수 표시
- `QThread: Destroyed while thread is still running` 방지
  - Stop/Close 시 worker stop 요청
  - interruptible sleep
  - thread wait 후 종료
- 종목 수 확인 스크립트 추가

```bash
python scripts/check_symbols.py
```

## v3 Patch

- `ka10081` 일봉 요청 body에 필수값 추가:
  - `stk_cd`
  - `base_dt`
  - `upd_stkpc_tp`
- `ka10100` 종목리스트 호출 제거
  - KOSPI/KOSDAQ 모두 `ka10099 + mrkt_tp` 사용
- 잘못 파싱된 `00010` 같은 비정상 종목코드 방지
  - 6자리 숫자 종목코드만 symbols에 저장
- 일봉 데이터 확인 스크립트 추가

```bash
python scripts/check_symbols.py
python scripts/check_daily.py
```

## v4 Patch - GUI 조건식 메뉴

메뉴바에 조건식 편집 기능을 추가했습니다.

- `Conditions > Edit Alert Conditions`
  - 조건명
  - 사용 여부
  - MA 정배열: 예) `5>20>60`
  - MA 비교: 예) `5>120`
  - PER <
  - PBR <
- `Conditions > Reset Default Conditions`
- 저장 시 `config.yaml`의 `analysis.custom_conditions`와 `alert.include_conditions`를 업데이트합니다.
- 스캐너는 `custom_conditions`가 있으면 해당 조건을 우선 사용합니다.

테스트:

```bash
python scripts/check_conditions.py
python gui_main.py
```
