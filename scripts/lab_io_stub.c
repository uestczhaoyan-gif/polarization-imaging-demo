/* Execute production logging code with fake registers, time and UART. */
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define HAL_OK 0
#define GPIO_PIN_10 10
#define GPIO_PIN_11 11
#define GPIO_MODE_AF_PP 1
#define GPIO_MODE_INPUT 2
#define GPIO_SPEED_FREQ_HIGH 3
#define GPIO_PULLUP 4
#define GPIOB 0
#define UART_WORDLENGTH_8B 8
#define UART_STOPBITS_1 1
#define UART_PARITY_NONE 0
#define UART_MODE_TX_RX 3
#define UART_HWCONTROL_NONE 0
#define UART_OVERSAMPLING_16 16
#define UART_FLAG_ORE 1
#define UART_FLAG_RXNE 2
typedef struct { unsigned DR; } Registers;
static Registers reg;
#define USART3 (&reg)
typedef struct { unsigned BaudRate,WordLength,StopBits,Parity,Mode,HwFlowCtl,OverSampling; } Init;
typedef struct { Registers *Instance; Init Init; } UART_HandleTypeDef;
typedef struct { unsigned Pin,Mode,Speed,Pull; } GPIO_InitTypeDef;
static uint32_t tick;
static unsigned flags,tx_count,irq_depth,fail_tx;
static bool auto_start;
static char output[32768];
#define __HAL_RCC_GPIOB_CLK_ENABLE() ((void)0)
#define __HAL_RCC_USART3_CLK_ENABLE() ((void)0)
#define __disable_irq() (++irq_depth)
#define __enable_irq() (--irq_depth)
#define __HAL_UART_CLEAR_OREFLAG(p) (flags=0)
static bool flag(unsigned f) { bool set=(flags&f)!=0; if(f==UART_FLAG_RXNE)flags&=~f; return set; }
#define __HAL_UART_GET_FLAG(p,f) flag(f)
static void HAL_GPIO_Init(unsigned g,GPIO_InitTypeDef *p) { (void)g;(void)p; }
static int HAL_UART_Init(UART_HandleTypeDef *p) { assert(p->Instance==USART3);return HAL_OK; }
static uint32_t HAL_GetTick(void) { return tick; }
static void HAL_Delay(uint32_t ms) { tick+=ms;if(auto_start){reg.DR='G';flags|=UART_FLAG_RXNE;auto_start=false;} }
static int HAL_UART_Transmit(UART_HandleTypeDef *p,uint8_t *data,uint16_t count,uint32_t timeout) {
    (void)p;(void)timeout;assert(!irq_depth);assert(strlen(output)+count<sizeof(output));
    strncat(output,(char *)data,count);++tx_count;return fail_tx?1:HAL_OK;
}
/* CONFIG */
/* CODE */
int main(int argc,char **argv) {
    (void)argc;
    Lab_Init();assert(strstr(output,",BOOT,") && !Lab_Aborted());
    Lab_Context(1,1,5,2,1,1000);
    unsigned before=tx_count;
    uint8_t arrival_frame[]={2,0xFD,0x9F,0x6B};
    Lab_MotorRx(arrival_frame,4,123);
    assert(tx_count==before); /* absolutely no serial output from motor RX ISR */
    tick=200;Lab_Service();assert(strstr(output,",123,DRIVER_REACHED_RX,1,1,5,2,1,1000,0"));
    if (strcmp(argv[1],"queue")==0) {
        for(unsigned i=0;i<8;++i)Lab_MotorRx(arrival_frame,4,300+i);
        Lab_Service();assert(Lab_Aborted() && strstr(output,",LOG_LOST,"));
    } else if(strcmp(argv[1],"tx")==0) {
        fail_tx=1;Lab_Event("TEST",0);assert(Lab_Aborted());
    } else if(strcmp(argv[1],"ore")==0) {
        flags=UART_FLAG_ORE;Lab_Service();assert(Lab_Aborted());
    } else {
        auto_start=true;assert(Lab_WaitStart());
        reg.DR='?';flags=UART_FLAG_RXNE;Lab_Service();assert(strstr(output,",SYNC,"));
        reg.DR='!';flags=UART_FLAG_RXNE;Lab_Service();assert(Lab_Aborted() && strstr(output,",ABORT_REQUEST,"));
    }
    puts("PASS: production lab logger timestamps, ISR isolation, start gate and faults");
}
