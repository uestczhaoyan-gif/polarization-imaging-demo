/* Test the production scan loop with simulated moves, including failure stops. */
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
/* CONFIG */
enum { SCAN_STATE_MOVING_X, SCAN_STATE_MOVING_Y, SCAN_STATE_RETURNING_X, SCAN_STATE_FINISHED };
static unsigned scan_state, scan_line, scan_x_offset_um, scan_y_offset_um;
static unsigned count, fail_at, error_code, led;
static jmp_buf failure;
static void HAL_Delay(uint32_t ms) { (void)ms; }
static void Scan_LedOn(void) { led=1; }
static void Scan_Fail(uint8_t code) { error_code=code; longjmp(failure,1); }
static bool Scan_MoveRelative(uint8_t axis,uint8_t direction,uint32_t distance,uint32_t timeout) {
    unsigned row=count/(SCAN_MODE ? 3 : 2);
    unsigned leg=count%(SCAN_MODE ? 3 : 2);
    (void)timeout;
    assert(scan_line==row+1);
    if (leg==0) {
        assert(axis==X_AXIS_ADDR && distance==ACTIVE_SCAN_WIDTH_UM);
        assert(direction==((SCAN_MODE || row%2==0)?X_FIRST_PASS_DIRECTION:X_ALTERNATE_PASS_DIRECTION));
        assert(scan_state==SCAN_STATE_MOVING_X);
    } else if (SCAN_MODE && leg==1) {
        assert(axis==X_AXIS_ADDR && direction==X_ALTERNATE_PASS_DIRECTION);
        assert(distance==ACTIVE_SCAN_WIDTH_UM && scan_state==SCAN_STATE_RETURNING_X);
    } else {
        assert(axis==Y_AXIS_ADDR && direction==Y_STEP_DIRECTION);
        assert(distance==ACTIVE_LINE_STEP_UM && scan_state==SCAN_STATE_MOVING_Y);
    }
    ++count;
    return count!=fail_at;
}
/* LOOP */
int main(void) {
    SnakeScan();
    assert(count==ACTIVE_HORIZONTAL_PASS_COUNT*(SCAN_MODE?3:2));
    assert(scan_y_offset_um==ACTIVE_SCAN_HEIGHT_UM);
    assert(scan_x_offset_um==((SCAN_MODE || ACTIVE_HORIZONTAL_PASS_COUNT%2==0)?0:ACTIVE_SCAN_WIDTH_UM));
    assert(scan_state==SCAN_STATE_FINISHED && led);
    unsigned total=count;
    for (unsigned stop=1;stop<=total;++stop) {
        count=led=scan_line=scan_x_offset_um=scan_y_offset_um=error_code=0;
        fail_at=stop;
        if (setjmp(failure)==0) { SnakeScan(); assert(0); }
        assert(count==stop && !led);
        unsigned leg=(stop-1)%(SCAN_MODE?3:2);
        assert(error_code==(leg==0?3:(SCAN_MODE && leg==1?8:4)));
    }
    puts("PASS: production scan loop directions, distances, endpoints and stop on every failed leg.");
}
