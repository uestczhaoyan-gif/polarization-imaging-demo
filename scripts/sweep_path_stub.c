#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
/* CONFIG */
enum { SCAN_STATE_MOVING_X,SCAN_STATE_MOVING_Y,SCAN_STATE_RETURNING_X,SCAN_STATE_FINISHED };
typedef struct { uint32_t stage,pulses,rpm,returning; } Expected;
/* EXPECTED */
static uint32_t scan_state,scan_line,count,fail_at,led;
static jmp_buf failure;
static void Lab_Event(const char *event,uint32_t value) { (void)event;(void)value; }
static void Lab_Delay(uint32_t ms) { (void)ms; }
static bool Lab_Aborted(void) { return false; }
static void Scan_LedOn(void) { led=1; }
static void Scan_LedOff(void) { led=0; }
static void Scan_Fail(uint8_t code) { assert(code==10);longjmp(failure,1); }
static bool Scan_MoveCommand(uint8_t axis,uint8_t direction,uint32_t pulses,uint16_t rpm,uint32_t timeout) {
    assert(count<sizeof(expected)/sizeof(expected[0]));
    Expected e=expected[count];
    unsigned forward=LAB_TEST_AXIS?Y_STEP_DIRECTION:X_FIRST_PASS_DIRECTION;
    assert(axis==(LAB_TEST_AXIS?Y_AXIS_ADDR:X_AXIS_ADDR));
    assert(direction==(e.returning?1-forward:forward));
    assert(scan_line==e.stage && pulses==e.pulses && rpm==e.rpm && timeout==0);
    assert(scan_state==(e.returning?SCAN_STATE_RETURNING_X:(LAB_TEST_AXIS?SCAN_STATE_MOVING_Y:SCAN_STATE_MOVING_X)));
    ++count;return count!=fail_at;
}
/* CODE */
int main(void) {
    Lab_SweepTest();
    unsigned total=sizeof(expected)/sizeof(expected[0]);
    assert(count==total && led && scan_state==SCAN_STATE_FINISHED);
    for(unsigned i=1;i<=total;++i) {
        count=led=0;fail_at=i;
        if(setjmp(failure)==0) { Lab_SweepTest();assert(0); }
        assert(count==i && scan_state!=SCAN_STATE_FINISHED);
    }
    puts("PASS: production sweep exact pulse/RPM order, axes, directions and every failed leg");
}
