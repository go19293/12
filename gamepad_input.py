"""게임패드(컨트롤러) 입력 지원 모듈.

pygame 의 joystick API 를 사용하여 Xbox / PlayStation / Lenovo Legion Go 2 등
대부분의 PC 호환 컨트롤러(Windows 에서는 XInput/DirectInput)를 지원한다.

dia_mc 본체에서 키보드/마우스와 동일한 핫키 체계로 게임패드 버튼을 쓸 수 있도록
버튼/D-Pad/트리거/스틱 입력을 'Gamepad.XXX' 형태의 문자열로 정규화한다.

pygame 이 설치되어 있지 않으면 AVAILABLE = False 가 되며 본체는 게임패드 없이
정상 동작한다.
"""

import threading
import time

try:
    import os as _os
    # 콘솔/창 없이도 조이스틱만 쓰도록 (오디오/비디오 서브시스템 불필요)
    _os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    _os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    import pygame
    AVAILABLE = True
except Exception:
    pygame = None
    AVAILABLE = False


# XInput(Xbox/Legion Go 2 등) 표준 버튼 인덱스 → 친숙한 이름
_XINPUT_BUTTON_NAMES = {
    0: 'A',
    1: 'B',
    2: 'X',
    3: 'Y',
    4: 'LB',
    5: 'RB',
    6: 'Back',
    7: 'Start',
    8: 'Guide',
    9: 'LStick',
    10: 'RStick',
}

# 사람이 읽기 좋은 표시 이름
_DISPLAY_NAMES = {
    'A': 'A', 'B': 'B', 'X': 'X', 'Y': 'Y',
    'LB': 'LB', 'RB': 'RB', 'LT': 'LT', 'RT': 'RT',
    'Back': 'Back', 'Start': 'Start', 'Guide': '가이드',
    'LStick': 'L스틱(누름)', 'RStick': 'R스틱(누름)',
    'DPadUp': '방향↑', 'DPadDown': '방향↓', 'DPadLeft': '방향←', 'DPadRight': '방향→',
    'LStickUp': 'L스틱↑', 'LStickDown': 'L스틱↓', 'LStickLeft': 'L스틱←', 'LStickRight': 'L스틱→',
    'RStickUp': 'R스틱↑', 'RStickDown': 'R스틱↓', 'RStickLeft': 'R스틱←', 'RStickRight': 'R스틱→',
}

GAMEPAD_PREFIX = 'Gamepad.'

# 스틱/트리거를 버튼처럼 다룰 때의 임계값
_AXIS_THRESHOLD = 0.6
_TRIGGER_THRESHOLD = 0.5


def display_text(name):
    """'Gamepad.A' → '게임패드 A' 형태의 표시 문자열."""
    if not name or not str(name).startswith(GAMEPAD_PREFIX):
        return name
    short = str(name)[len(GAMEPAD_PREFIX):]
    return '게임패드 ' + _DISPLAY_NAMES.get(short, short)


def is_gamepad_hotkey(value):
    return bool(value) and str(value).startswith(GAMEPAD_PREFIX)


class GamepadManager:
    """백그라운드 폴링으로 게임패드 입력을 감지한다.

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
        """마지막 폴링 이후 새로 눌린 게임패드 입력 이름 하나를 반환(없으면 None)."""
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
            # 너무 쌓이지 않도록 제한
            if len(self._capture_buffer) > 16:
                self._capture_buffer = self._capture_buffer[-16:]

    # ---- 내부 폴링 루프 ----
    def _run(self):
        try:
            pygame.init()
            pygame.joystick.init()
        except Exception as exc:
            self.last_error = exc
            self.available = False
            self._running = False
            return
        joysticks = {}
        axis_state = {}
        hat_state = {}
        while self._running:
            try:
                pygame.event.pump()
                count = pygame.joystick.get_count()
                # 새 조이스틱 초기화
                for idx in range(count):
                    if idx not in joysticks:
                        try:
                            js = pygame.joystick.Joystick(idx)
                            js.init()
                            joysticks[idx] = js
                        except Exception:
                            continue
                # 사라진 조이스틱 정리
                for idx in list(joysticks.keys()):
                    if idx >= count:
                        joysticks.pop(idx, None)
                for idx, js in list(joysticks.items()):
                    self._poll_joystick(idx, js, axis_state, hat_state)
            except Exception as exc:
                self.last_error = exc
            time.sleep(self._poll_interval)

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

    def _button_name(self, index):
        short = _XINPUT_BUTTON_NAMES.get(index, 'Btn%d' % index)
        return GAMEPAD_PREFIX + short

    def _poll_joystick(self, idx, js, axis_state, hat_state):
        # 버튼
        try:
            nbtn = js.get_numbuttons()
        except Exception:
            nbtn = 0
        for b in range(nbtn):
            try:
                pressed = bool(js.get_button(b))
            except Exception:
                continue
            self._emit(self._button_name(b), pressed)

        # 트리거/스틱(축)
        try:
            naxes = js.get_numaxes()
        except Exception:
            naxes = 0
        for ax in range(naxes):
            try:
                val = js.get_axis(ax)
            except Exception:
                continue
            self._poll_axis(idx, ax, val, axis_state)

        # D-Pad(햇)
        try:
            nhats = js.get_numhats()
        except Exception:
            nhats = 0
        for h in range(nhats):
            try:
                hx, hy = js.get_hat(h)
            except Exception:
                continue
            key = (idx, h)
            prev = hat_state.get(key, (0, 0))
            self._emit(GAMEPAD_PREFIX + 'DPadLeft', hx < 0)
            self._emit(GAMEPAD_PREFIX + 'DPadRight', hx > 0)
            self._emit(GAMEPAD_PREFIX + 'DPadDown', hy < 0)
            self._emit(GAMEPAD_PREFIX + 'DPadUp', hy > 0)
            hat_state[key] = (hx, hy)

    def _poll_axis(self, idx, ax, val, axis_state):
        # 일반적인 XInput 축 배치:
        #   0: 왼쪽 스틱 X, 1: 왼쪽 스틱 Y
        #   2: (SDL2) 왼쪽 스틱? 또는 트리거 / 3,4: 오른쪽 스틱
        #   트리거는 환경에 따라 별도 축. 임계값 기반으로 버튼화한다.
        names = None
        is_trigger = False
        if ax == 0:
            names = (GAMEPAD_PREFIX + 'LStickLeft', GAMEPAD_PREFIX + 'LStickRight')
        elif ax == 1:
            names = (GAMEPAD_PREFIX + 'LStickUp', GAMEPAD_PREFIX + 'LStickDown')
        elif ax == 3:
            names = (GAMEPAD_PREFIX + 'RStickLeft', GAMEPAD_PREFIX + 'RStickRight')
        elif ax == 4:
            names = (GAMEPAD_PREFIX + 'RStickUp', GAMEPAD_PREFIX + 'RStickDown')
        elif ax == 2:
            # SDL2 의 trigger: -1(미입력) ~ +1(완전히 당김)인 경우가 많다
            is_trigger = True
            self._emit(GAMEPAD_PREFIX + 'LT', val > _TRIGGER_THRESHOLD)
            return
        elif ax == 5:
            is_trigger = True
            self._emit(GAMEPAD_PREFIX + 'RT', val > _TRIGGER_THRESHOLD)
            return
        else:
            return
        if names is None or is_trigger:
            return
        neg_name, pos_name = names
        # Y축은 위가 음수인 경우가 많으므로 위/아래 의미를 보정:
        if ax in (1, 4):
            # names=(Up, Down): val<0 → Up, val>0 → Down
            self._emit(neg_name, val < -_AXIS_THRESHOLD)
            self._emit(pos_name, val > _AXIS_THRESHOLD)
        else:
            self._emit(neg_name, val < -_AXIS_THRESHOLD)
            self._emit(pos_name, val > _AXIS_THRESHOLD)
