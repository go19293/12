"""게임패드(컨트롤러) 입력 지원 모듈 - Windows XInput(ctypes) 기반.

추가 라이브러리 없이 Windows 내장 XInput DLL 만으로 동작한다.
Xbox / Xbox 호환 패드 / Lenovo Legion Go 2 등 XInput 컨트롤러를 지원한다.
(PlayStation 등은 Steam 입력 또는 DS4Windows 로 XInput 모드일 때 동작)

dia_mc 본체에서 키보드/마우스와 동일한 핫키 체계로 게임패드 버튼을 쓸 수 있도록
버튼/D-Pad/트리거/스틱 입력을 'Gamepad.XXX' 형태의 문자열로 정규화한다.

XInput DLL 을 찾을 수 없으면(비 Windows 등) AVAILABLE = False 가 되며 본체는
게임패드 없이 정상 동작한다.
"""

import ctypes
import threading
import time

GAMEPAD_PREFIX = 'Gamepad.'

# ---- XInput 로드 ----
_xinput = None
for _dll in ('XInput1_4.dll', 'XInput1_3.dll', 'xinput9_1_0.dll', 'XInput9_1_0.dll'):
    try:
        _xinput = ctypes.windll.LoadLibrary(_dll)
        break
    except Exception:
        _xinput = None
AVAILABLE = _xinput is not None


class _XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ('wButtons', ctypes.c_ushort),
        ('bLeftTrigger', ctypes.c_ubyte),
        ('bRightTrigger', ctypes.c_ubyte),
        ('sThumbLX', ctypes.c_short),
        ('sThumbLY', ctypes.c_short),
        ('sThumbRX', ctypes.c_short),
        ('sThumbRY', ctypes.c_short),
    ]


class _XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ('dwPacketNumber', ctypes.c_uint),
        ('Gamepad', _XINPUT_GAMEPAD),
    ]


# 버튼 비트마스크 → 이름
_BUTTON_BITS = [
    (0x0001, 'DPadUp'),
    (0x0002, 'DPadDown'),
    (0x0004, 'DPadLeft'),
    (0x0008, 'DPadRight'),
    (0x0010, 'Start'),
    (0x0020, 'Back'),
    (0x0040, 'LStick'),
    (0x0080, 'RStick'),
    (0x0100, 'LB'),
    (0x0200, 'RB'),
    (0x1000, 'A'),
    (0x2000, 'B'),
    (0x4000, 'X'),
    (0x8000, 'Y'),
]

_TRIGGER_THRESHOLD = 60      # 0~255
_STICK_THRESHOLD = 20000     # -32768~32767

_DISPLAY_NAMES = {
    'A': 'A', 'B': 'B', 'X': 'X', 'Y': 'Y',
    'LB': 'LB', 'RB': 'RB', 'LT': 'LT', 'RT': 'RT',
    'Back': 'Back', 'Start': 'Start',
    'LStick': 'L스틱(누름)', 'RStick': 'R스틱(누름)',
    'DPadUp': '방향↑', 'DPadDown': '방향↓', 'DPadLeft': '방향←', 'DPadRight': '방향→',
    'LStickUp': 'L스틱↑', 'LStickDown': 'L스틱↓', 'LStickLeft': 'L스틱←', 'LStickRight': 'L스틱→',
    'RStickUp': 'R스틱↑', 'RStickDown': 'R스틱↓', 'RStickLeft': 'R스틱←', 'RStickRight': 'R스틱→',
}


def display_text(name):
    """'Gamepad.A' → '게임패드 A' 형태의 표시 문자열."""
    if not name or not str(name).startswith(GAMEPAD_PREFIX):
        return name
    short = str(name)[len(GAMEPAD_PREFIX):]
    return '게임패드 ' + _DISPLAY_NAMES.get(short, short)


def is_gamepad_hotkey(value):
    return bool(value) and str(value).startswith(GAMEPAD_PREFIX)


class GamepadManager:
    """백그라운드 폴링으로 XInput 게임패드 입력을 감지한다.

    on_press(name) / on_release(name) 콜백을 호출하며, 동시에 캡처용 큐에도
    눌린 버튼 이름을 쌓아 핫키 설정 창에서 가져갈 수 있게 한다.
    """

    def __init__(self, poll_interval=0.02):
        self._poll_interval = poll_interval
        self._thread = None
        self._running = False
        self._on_press = None
        self._on_release = None
        self._pressed = set()
        self._capture_lock = threading.Lock()
        self._capture_buffer = []
        self.available = AVAILABLE
        self.last_error = None

    # ---- 수명주기 ----
    def start(self, on_press=None, on_release=None):
        if not AVAILABLE:
            self.available = False
            return False
        self._on_press = on_press
        self._on_release = on_release
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._run, name='GamepadPoll', daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._running = False
        t = self._thread
        if t is not None:
            try:
                t.join(timeout=1.0)
            except Exception:
                pass
        self._thread = None

    # ---- 캡처(핫키 설정용) ----
    def poll_captured(self):
        with self._capture_lock:
            if self._capture_buffer:
                return self._capture_buffer.pop(0)
        return None

    def clear_captured(self):
        with self._capture_lock:
            self._capture_buffer = []

    def _buffer_capture(self, name):
        with self._capture_lock:
            self._capture_buffer.append(name)
            if len(self._capture_buffer) > 16:
                self._capture_buffer = self._capture_buffer[-16:]

    # ---- 내부 ----
    def _emit(self, name, pressed):
        if pressed:
            if name in self._pressed:
                return
            self._pressed.add(name)
            self._buffer_capture(name)
            cb = self._on_press
            if cb is not None:
                try:
                    cb(name)
                except Exception:
                    pass
        else:
            if name not in self._pressed:
                return
            self._pressed.discard(name)
            cb = self._on_release
            if cb is not None:
                try:
                    cb(name)
                except Exception:
                    pass

    def _run(self):
        if not AVAILABLE:
            return
        XInputGetState = _xinput.XInputGetState
        state = _XINPUT_STATE()
        prev_connected = [False, False, False, False]
        while self._running:
            try:
                for idx in range(4):
                    res = XInputGetState(idx, ctypes.byref(state))
                    if res != 0:
                        # 연결 해제됨: 눌려있던 입력 해제
                        if prev_connected[idx]:
                            self._release_all_for(idx)
                            prev_connected[idx] = False
                        continue
                    prev_connected[idx] = True
                    self._process(idx, state.Gamepad)
            except Exception as exc:
                self.last_error = exc
            time.sleep(self._poll_interval)

    def _release_all_for(self, idx):
        for name in list(self._pressed):
            self._emit(name, False)

    def _process(self, idx, gp):
        buttons = gp.wButtons
        for bit, short in _BUTTON_BITS:
            self._emit(GAMEPAD_PREFIX + short, bool(buttons & bit))
        # 트리거
        self._emit(GAMEPAD_PREFIX + 'LT', gp.bLeftTrigger > _TRIGGER_THRESHOLD)
        self._emit(GAMEPAD_PREFIX + 'RT', gp.bRightTrigger > _TRIGGER_THRESHOLD)
        # 왼쪽 스틱
        self._emit(GAMEPAD_PREFIX + 'LStickLeft', gp.sThumbLX < -_STICK_THRESHOLD)
        self._emit(GAMEPAD_PREFIX + 'LStickRight', gp.sThumbLX > _STICK_THRESHOLD)
        self._emit(GAMEPAD_PREFIX + 'LStickUp', gp.sThumbLY > _STICK_THRESHOLD)
        self._emit(GAMEPAD_PREFIX + 'LStickDown', gp.sThumbLY < -_STICK_THRESHOLD)
        # 오른쪽 스틱
        self._emit(GAMEPAD_PREFIX + 'RStickLeft', gp.sThumbRX < -_STICK_THRESHOLD)
        self._emit(GAMEPAD_PREFIX + 'RStickRight', gp.sThumbRX > _STICK_THRESHOLD)
        self._emit(GAMEPAD_PREFIX + 'RStickUp', gp.sThumbRY > _STICK_THRESHOLD)
        self._emit(GAMEPAD_PREFIX + 'RStickDown', gp.sThumbRY < -_STICK_THRESHOLD)
