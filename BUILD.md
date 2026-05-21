# DIA_MC 빌드 방법 (게임패드 지원 추가본)

이 저장소는 원래 `dia_mc.exe`(PyInstaller로 패키징된 Windows용 Python 3.12 매크로
프로그램)의 **소스를 복원하고, 게임패드(컨트롤러) 입력 지원을 추가**한 것입니다.

- `dia_mc.py` — 메인 프로그램(복원 + 게임패드 통합)
- `gamepad_input.py` — 게임패드 입력 모듈(pygame 기반, 신규)
- `dia_logo.ico`, `dia_logo.png` — 아이콘/로고
- `예시참고매크로.json` — 예시 설정
- `dia_mc.spec`, `requirements.txt` — 빌드용

> 참고: 이 프로그램은 Windows 전용입니다(win32 API/ctypes 사용). 빌드도 **Windows
> 에서** 진행해야 합니다.

## 1. 준비물
- Windows 10/11
- Python 3.12 (원본과 동일 버전 권장)

## 2. 의존성 설치
```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```
`requirements.txt` 에는 다음이 포함됩니다.
- `pynput` — 키보드/마우스 입력(기존 기능)
- `pygame` — **게임패드 입력(신규)**

## 3. 그냥 실행해서 테스트 (빌드 없이)
```bat
python dia_mc.py
```
게임패드를 연결하고, 설정 창에서 시작키/종료키/일시정지키/트리거 등을 지정할 때
**"게임패드" 탭**(또는 키 캡처 중 게임패드 버튼 누르기)으로 컨트롤러 버튼을
할당할 수 있습니다.

## 4. exe 빌드
```bat
pyinstaller dia_mc.spec
```
- 결과물: `dist\DIA_MC\dia_mc.exe` (와 `_internal` 폴더)
- 빌드 후 **`dia_logo.ico` 와 `dia_logo.png` 를 `dist\DIA_MC\` 폴더(=exe 와 같은
  위치)에 복사**하세요. 앱이 실행파일 위치에서 로고/설정 파일을 찾습니다.

배포할 때는 `dist\DIA_MC` 폴더 전체를 압축해서 전달하면 됩니다.

## 5. 게임패드 지원 안내
- **Xbox / Xbox 호환 패드** → Windows 표준 XInput 으로 인식되어 바로 동작합니다.
- **PlayStation(DualShock/DualSense) 등 기타 패드** → pygame 의 joystick 으로
  인식되어 동작합니다(필요 시 Steam 입력/드라이버로 XInput 변환 권장).
- **레노버 리전 고2(Lenovo Legion Go 2)** → 내장 컨트롤러가 Windows 에서 표준
  XInput 게임패드로 보고되므로 별도 설정 없이 지원됩니다.

게임패드 버튼은 키보드/마우스 핫키와 **완전히 동일하게** 다음 용도로 지정할 수
있습니다.
- 시작키 / 종료키
- 일시정지키 (홀드/토글)
- 빨리줍기키(루팅) / 빠른우클릭키
- 자동 순차 실행(트리거) 키

지원 입력: A/B/X/Y, LB/RB, LT/RT, Back/Start, 스틱 누름(L/R), 방향패드(D-Pad),
좌/우 스틱 방향. (`gamepad_input.py` 에서 매핑/임계값 조정 가능)

> pygame 이 설치되어 있지 않으면 게임패드 기능만 비활성화되고 나머지(키보드/마우스)
> 는 정상 동작합니다.
