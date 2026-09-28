/* Production finite lab loop with failure injection; no hardware. */
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
/* CONFIG */
enum { SCAN_STATE_MOVING_X,SCAN_STATE_MOVING_Y,SCAN_STATE_RETURNING_X,SCAN_STATE_FINISHED };
static unsigned scan_state,scan_line,count,fail_at,led;
static bool abort_flag;
static jmp_buf failure;
static int32_t position;
static void Lab_Delay(uint32_t ms) { assert(ms==LAB_TEST_DWELL_MS); }
static bool Lab_Aborted(void) { return abort_flag; }
static void Scan_LedOn(void) { led=1; }
static void Scan_Fail(uint8_t code) { assert(code==9 || code==10); longjmp(failure,1); }
static bool Scan_MoveRelative(uint8_t axis,uint8_t dir,uint32_t distance,uint32_t timeout) {
    unsigned forward=LAB_TEST_AXIS?Y_STEP_DIRECTION:X_FIRST_PASS_DIRECTION;
    bool returning=LAB_EXPERIMENT==2 ? count%2 : count==LAB_TEST_REPEATS;
    assert(axis==(LAB_TEST_AXIS?Y_AXIS_ADDR:X_AXIS_ADDR));
    assert(dir==(returning?1-forward:forward));
    assert(distance==LAB_TEST_DISTANCE_UM*((LAB_EXPERIMENT==3 && returning)?LAB_TEST_REPEATS:1));
    assert(timeout==0U);
    assert(scan_state==(returning?SCAN_STATE_RETURNING_X:(LAB_TEST_AXIS?SCAN_STATE_MOVING_Y:SCAN_STATE_MOVING_X)));
    ++count;
    if (count==fail_at) return false;
    position+=(dir==forward?1:-1)*(int32_t)distance;
    return true;
}
/* LOOP */
int main(void) {
    Lab_AxisTest();
    unsigned total=LAB_EXPERIMENT==2?2*LAB_TEST_REPEATS:LAB_TEST_REPEATS+1;
    assert(count==total && position==0 && led && scan_state==SCAN_STATE_FINISHED);
    for (unsigned i=1;i<=total;++i) {
        count=led=0;position=0;fail_at=i;
        if (setjmp(failure)==0) { Lab_AxisTest(); assert(0); }
        assert(count==i && !led);
    }
    count=led=0;fail_at=0;abort_flag=true;
    if (setjmp(failure)==0) { Lab_AxisTest(); assert(0); }
    assert(count==1 && !led);
    puts("PASS: finite lab path, directions, endpoint, every failed leg and dwell abort");
}
