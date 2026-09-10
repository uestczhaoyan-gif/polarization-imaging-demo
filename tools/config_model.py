"""STM32 参数读取、校验和最小修改；只依赖 Python 标准库。"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    minimum: int
    maximum: int
    group: str = '扫描参数'


FIELDS = [
    Field('MASK_SCAN_WIDTH_MM', '扫描宽度 / mm（整数）', 1, 4294),
    Field('MASK_SCAN_HEIGHT_MM', '扫描高度 / mm（整数）', 1, 4294),
    Field('SCAN_LINE_STEP_MM', '行距 / mm（整数）', 1, 4294),
    Field('SCAN_SPEED_UM_PER_SEC', '线速度 / mm/s（最多3位小数）', 1, 71582788),
    Field('X_FIRST_PASS_DIRECTION', 'X 首行方向：0=CW，1=CCW', 0, 1),
    Field('Y_STEP_DIRECTION', 'Y 步进方向：0=CW，1=CCW', 0, 1),
    Field('X_AXIS_MAX_SAFE_TRAVEL_MM', 'X 可用安全行程 / mm', 1, 4294),
    Field('Y_AXIS_MAX_SAFE_TRAVEL_MM', 'Y 可用安全行程 / mm', 1, 4294),
    Field('X_AXIS_ADDR', 'X 电机地址', 1, 255, '硬件参数'),
    Field('Y_AXIS_ADDR', 'Y 电机地址', 1, 255, '硬件参数'),
    Field('MOTOR_FULL_STEPS_PER_REV', '电机整步数 / 圈', 1, 10000, '硬件参数'),
    Field('MOTOR_MICROSTEP', '驱动器细分（与电机菜单一致）', 1, 256, '硬件参数'),
    Field('LEAD_UM_PER_REV', '丝杆导程 / μm/圈', 1, 4294967295, '硬件参数'),
    Field('SCAN_ACCELERATION', '协议加速度值（0=无加减速曲线）', 0, 255, '硬件参数'),
    Field('SCAN_START_COUNTDOWN_SECONDS', '启动倒计时 / 秒', 0, 255, '硬件参数'),
]
KEYS = [f.key for f in FIELDS] + ['X_ALTERNATE_PASS_DIRECTION']


def pattern(key):
    return re.compile(r'^(#define[ \t]+' + re.escape(key) + r'[ \t]+)(\d+)(U(?:L)?)(?=[ \t\r\n]|$)', re.M)


def read_values(source):
    text = source.decode('utf-8-sig')
    values = {}
    for key in KEYS:
        found = pattern(key).findall(text)
        if len(found) != 1:
            raise ValueError(f'{key} 必须恰好出现一次，且为整数 U/UL 宏；未修改文件。')
        values[key] = int(found[0][1])
    return values


def parse_form(form):
    values = {}
    for field in FIELDS:
        try:
            value = Decimal(str(form[field.key]).strip())
            if field.key == 'SCAN_SPEED_UM_PER_SEC':
                value *= 1000  # 界面 mm/s → 固件 μm/s，不静默舍入。
            if not value.is_finite() or value != value.to_integral_value():
                raise ValueError()
            values[field.key] = int(value)
        except (InvalidOperation, ValueError, KeyError):
            raise ValueError(f'{field.label}：请输入有效数值，遵守所示精度。') from None
    values['X_ALTERNATE_PASS_DIRECTION'] = 1 - values['X_FIRST_PASS_DIRECTION']
    validate(values)
    return values


def validate(v):
    for f in FIELDS:
        if not isinstance(v[f.key], int) or not f.minimum <= v[f.key] <= f.maximum:
            raise ValueError(f'{f.label} 超出支持范围；固件单位范围 {f.minimum}～{f.maximum}。')
    w, h, step = (v[k] for k in ('MASK_SCAN_WIDTH_MM', 'MASK_SCAN_HEIGHT_MM', 'SCAN_LINE_STEP_MM'))
    if h % step:
        raise ValueError('扫描高度必须能被行距整除。')
    if w > v['X_AXIS_MAX_SAFE_TRAVEL_MM'] or h > v['Y_AXIS_MAX_SAFE_TRAVEL_MM']:
        raise ValueError('扫描范围超过填写的安全行程；请核对机械可用行程。')
    if v['X_FIRST_PASS_DIRECTION'] + v['X_ALTERNATE_PASS_DIRECTION'] != 1:
        raise ValueError('X 两次横扫必须方向相反。')
    if v['X_AXIS_ADDR'] == v['Y_AXIS_ADDR']:
        raise ValueError('X、Y 电机地址不能相同。')
    pulses = v['MOTOR_FULL_STEPS_PER_REV'] * v['MOTOR_MICROSTEP'] * 1000
    lead, speed = v['LEAD_UM_PER_REV'], v['SCAN_SPEED_UM_PER_SEC']
    if pulses > 0xffffffff or pulses % lead:
        raise ValueError('机械参数必须得到整数脉冲/mm，且换算不能溢出32位整数。')
    if max(w, step, 10) * (pulses // lead) > 0xffffffff:
        raise ValueError('运动脉冲数超出32位命令范围。')
    if speed * 60 + lead // 2 > 0xffffffff:
        raise ValueError('转速换算会溢出32位整数。')
    rpm = (speed * 60 + lead // 2) // lead
    if not 1 <= rpm <= 3000:
        raise ValueError('换算转速必须处于1～3000 RPM。')
    return dict(rows=h // step, rpm=rpm, actual_mm_s=rpm * lead / 60000,
                last_line_y_mm=h-step, final_y_mm=h,
                ideal_motion_seconds=(h // step * w + h) / (rpm * lead / 60000))


def render(source, values):
    read_values(source)
    validate(values)
    text = source.decode('utf-8-sig')
    for key in KEYS:
        text = pattern(key).sub(lambda m: m[1] + str(values[key]) + m[3], text)
    result = text.encode('utf-8')
    return (b'\xef\xbb\xbf' + result) if source.startswith(b'\xef\xbb\xbf') else result


def save_header(path, original, values, history_dir):
    """拒绝覆盖外部新改动；先备份和记录，再原子替换头文件。"""
    path, history_dir = Path(path), Path(history_dir)
    updated = render(original, values)
    if path.read_bytes() != original:
        raise ValueError('参数文件已被其他程序修改，请重新读取后再保存。')
    if updated == original:
        return None
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    backup = history_dir / (stamp + '.before.h')
    with backup.open('xb') as stream:
        stream.write(original)
    record = dict(saved_utc=stamp, parameters=values, derived=validate(values),
                  before_sha256=hashlib.sha256(original).hexdigest(),
                  after_sha256=hashlib.sha256(updated).hexdigest(), flashed=False,
                  note='已保存源代码配置；尚未证明编译、烧录或实际运行参数。')
    with (history_dir / (stamp + '.json')).open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    fd, temporary = tempfile.mkstemp(prefix='.config-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(updated)
        if path.read_bytes() != original:
            raise ValueError('保存期间文件发生变化，未覆盖。')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return backup
