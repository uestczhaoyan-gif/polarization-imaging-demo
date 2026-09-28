"""Compile the three finite stage tests into exact pulse/RPM tables and a measurement plan."""
import csv
from decimal import Decimal, ROUND_HALF_UP

KINDS={'minimum_distance':4,'minimum_speed':5,'maximum_speed':6}
DEFAULTS={
    'minimum_distance':dict(levels=['0.1','0.05','0.02','0.01','0.005','0.0025','0.00125','0.000625','0.0003125'],distance_mm='1',preload_mm='0.2'),
    'minimum_speed':dict(levels=['1','0.5','0.2','0.1','0.05','0.02'],distance_mm='1',preload_mm='0'),
    'maximum_speed':dict(levels=['1','2','3','4','5'],distance_mm='10',preload_mm='0')}

def number(value):
    v=Decimal(str(value))
    if not v.is_finite() or v<=0:raise ValueError('请输入有限正数')
    return v

def build_sweep(profile,scan,lab):
    options=profile['sweep'];kind=options['kind']
    if kind not in KINDS or lab['LAB_EXPERIMENT']!=KINDS[kind]:raise ValueError('实验种类与 LAB_EXPERIMENT 不一致')
    levels=options['levels']
    if not 1<=len(levels)<=16:raise ValueError('每次测试需 1～16 档')
    ppr=scan['MOTOR_FULL_STEPS_PER_REV']*scan['MOTOR_MICROSTEP'];lead=scan['LEAD_UM_PER_REV']
    def pulses(mm):
        result=number(mm)*1000*ppr/lead
        if result!=result.to_integral_value() or not 1<=result<=0xffffffff:
            raise ValueError(f'{mm} mm 不能精确换算为整数脉冲；当前一脉冲为 {lead/ppr/1000:.9g} mm')
        return int(result)
    def rpm(speed):
        result=int((number(speed)*60000/lead).to_integral_value(rounding=ROUND_HALF_UP))
        if not 1<=result<=3000:raise ValueError('换算转速须为 1～3000 RPM；这不是实机平稳速度保证')
        return result
    preload=pulses(options.get('preload_mm','0.2')) if kind=='minimum_distance' else 0
    pause=options.get('stage_pause_ms',5000)
    if type(pause) is not int or not 1000<=pause<=60000:raise ValueError('档间等待需 1000～60000 ms')
    table=[];last=None;plan=[];move=0;ideal=0.
    repeats=lab['LAB_TEST_REPEATS'];dwell=lab['LAB_TEST_DWELL_MS']
    if dwell<1000:raise ValueError('平台测试每次停留至少 1 秒，便于观察或录像')
    for stage,value in enumerate(levels,1):
        count=pulses(value if kind=='minimum_distance' else options.get('distance_mm','1'))
        speed=rpm(Decimal(scan['SCAN_SPEED_UM_PER_SEC'])/1000 if kind=='minimum_distance' else value)
        order=count if kind=='minimum_distance' else speed
        if last is not None and not (order>last if kind=='maximum_speed' else order<last):
            raise ValueError('位移/低速档须严格递减，高速档须严格递增；取整后重复 RPM 也不允许')
        last=order
        travel=preload+count*repeats if kind=='minimum_distance' else count
        safe=scan['Y_AXIS_MAX_SAFE_TRAVEL_UM' if lab['LAB_TEST_AXIS'] else 'X_AXIS_MAX_SAFE_TRAVEL_UM']
        if travel>0xffffffff or travel*lead>safe*ppr:raise ValueError('预走加累计位移超过当前轴的安全行程')
        nominal=(60000*travel+speed*ppr-1)//(speed*ppr)
        if nominal+20000>0xffffffff:raise ValueError('本档运动时间超出32位计时范围')
        table.append(dict(stage=stage,requested=str(value),pulses=count,rpm=speed,
                          actual_distance_mm=count*lead/ppr/1000,actual_speed_mm_s=speed*lead/60000,
                          max_offset_mm=travel*lead/ppr/1000))
        position=0
        sequence=([('preload',preload,0)]+[('step',count,i) for i in range(1,repeats+1)]+[('return',-travel,0)]) if kind=='minimum_distance' else [leg for i in range(1,repeats+1) for leg in [('forward',count,i),('return',-count,i)]]
        ideal+=pause/1000+stage*.5
        for phase,delta,repeat in sequence:
            move+=1;position+=delta
            ideal+=abs(delta)*60/(speed*ppr)+dwell/1000
            plan.append(dict(move=move,stage=stage,repeat=repeat,phase=phase,pulses=abs(delta),rpm=speed,
                             actual_speed_mm_s=speed*lead/60000,commanded_position_mm=position*lead/ppr/1000,
                             measured_position_mm='',completed_yes_no='',stable_yes_no='',notes=''))
    lines=['#ifndef LAB_SWEEP_CONFIG_H','#define LAB_SWEEP_CONFIG_H',
           '/* Generated finite table. Use the stage-test GUI to change it. */',
           f'#define LAB_SWEEP_KIND {KINDS[kind]}U',f'#define LAB_SWEEP_COUNT {len(table)}U',
           '#define LAB_SWEEP_PULSES {'+', '.join(str(r['pulses'])+'UL' for r in table)+'}',
           '#define LAB_SWEEP_RPMS {'+', '.join(str(r['rpm'])+'U' for r in table)+'}',
           f'#define LAB_SWEEP_PRELOAD_PULSES {preload}UL',f'#define LAB_SWEEP_PAUSE_MS {pause}UL',
           '#if LAB_EXPERIMENT >= 4U','#if LAB_EXPERIMENT != LAB_SWEEP_KIND',
           '#error "Regenerate sweep table for selected experiment"','#endif']
    for row in table:
        travel=preload+row['pulses']*repeats if kind=='minimum_distance' else row['pulses']
        # Recompute against current mechanics at build time: detect stale tables after manual edits.
        lines += [f'#if (1ULL * {travel}UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))',
                  '#error "Sweep exceeds declared travel"','#endif']
    lines += [f'#if (MOTOR_PULSES_PER_REV != {ppr}UL) || (LEAD_UM_PER_REV != {lead}UL) || (LAB_TEST_REPEATS != {repeats}UL)',
              '#error "Mechanics/repetitions changed: regenerate sweep table"','#endif','#endif','#endif','']
    return '\n'.join(lines),dict(kind=kind,levels=table,plan=plan,
        minimum_command_mm=lead/ppr/1000,angle_per_pulse_deg=360/ppr,
        ideal_seconds_without_controller_overhead=ideal+scan['SCAN_START_COUNTDOWN_SECONDS'],
        notice='Planned commands only. Empty observations are not measurements; automatic execution does not determine stable motion.')

def write_plan(path,plan):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(plan[0]));writer.writeheader();writer.writerows(plan)
