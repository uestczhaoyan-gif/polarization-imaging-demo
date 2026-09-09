/* Host-only harness; never added to a Keil project. */
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#define __IO volatile
#define __disable_irq() ((void)0)
#define __enable_irq() ((void)0)
#define __HAL_UART_CLEAR_OREFLAG(x) ((void)0)
#define __HAL_UART_CLEAR_IDLEFLAG(x) ((void)0)
#define HAL_OK 0
#define MOTOR_STATUS_REACHED_MASK 2U
#define EMM_REPLY_OK 2U
#define EMM_REPLY_REACHED 0x9FU
#define EMM_CHECK_BYTE 0x6BU
/* CONFIG */
int huart1;
volatile uint8_t rxCmd[255], rxCount;
volatile bool rxFrameFlag;
static uint32_t tick, due, finish;
static unsigned moves, queries, fault;
static uint8_t pending[4], last_move[13];
static bool scheduled;
static void deliver(void) {
    if (scheduled && tick >= due) {
        memcpy((void *)rxCmd, pending, 4);
        rxCount=4; rxFrameFlag=true; scheduled=false;
    }
}
static uint32_t HAL_GetTick(void) { ++tick; deliver(); return tick; }
static void HAL_Delay(uint32_t ms) { tick+=ms; deliver(); }
static int HAL_UART_AbortReceive(int *h) { (void)h; return HAL_OK; }
static int UART1_StartReceiveToIdle(void) { return HAL_OK; }
static int HAL_UART_Transmit_DMA(int *h, uint8_t *cmd, uint16_t size) {
    (void)h;
    uint8_t value=2;
    if (cmd[1]==0xFD) {
        assert(size==13); ++moves; memcpy(last_move,cmd,13); finish=tick+50000;
        if (fault==1) return HAL_OK; /* missing acknowledgement */
        if (fault==2) value=0x9F; /* late/stale reached response */
    } else {
        assert(cmd[1]==0x3A && size==3); ++queries;
        value=tick >= finish ? 2 : 0;
        if (fault==3 && queries==2) value=2; /* spurious reached status */
        if (fault==4) return HAL_OK; /* all state queries lost */
    }
    pending[0]=cmd[0]; pending[1]=cmd[1]; pending[2]=value; pending[3]=0x6B;
    due=tick+2; scheduled=true; return HAL_OK;
}
/* DRIVER */
/* SCAN */
static void reset(unsigned scenario) {
    tick=due=finish=moves=queries=0; scheduled=false; rxFrameFlag=false;
    rxCount=0; fault=scenario;
}
int main(void) {
    const uint8_t expected[13]={2,0xFD,1,0,0x78,0,0,4,0xE2,0,2,0,0x6B};
    reset(0);
    assert(Scan_MoveRelative(2,1,100,70000));
    assert(moves==1 && queries>80 && tick>=finish);
    assert(memcmp(last_move,expected,13)==0);
    puts("PASS: 2 mm/s = 120 RPM; one 100 mm command; no midline speed command.");
    reset(1);
    assert(Scan_MoveRelative(2,1,100,70000)); assert(moves==1 && tick>=finish);
    puts("PASS: missing acknowledgement does not resend the movement.");
    reset(4);
    assert(!Scan_MoveRelative(2,1,100,70000)); assert(moves==1);
    puts("PASS: lost status replies time out without resending movement.");
    reset(2);
    assert(Scan_MoveRelative(2,1,100,70000)); assert(tick<finish && queries==0);
    puts("REPRODUCED: stale FD/9F response can finish the wait prematurely (not fixed).");
    reset(3);
    assert(Scan_MoveRelative(2,1,100,70000)); assert(tick<finish && queries==2);
    puts("REPRODUCED: false reached bit after moving can finish the wait prematurely (not fixed).");
    puts("Scope: host functions with simulated HAL/replies; no Keil build, DMA timing or motor test.");
    return 0;
}
