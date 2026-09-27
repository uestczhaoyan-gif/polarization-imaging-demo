#include "main.h"
#include "snake_scan_config.h"
#include "lab_config.h"
#include "lab_io.h"
#include <stdio.h>

#if LAB_LOG_ENABLE
static UART_HandleTypeDef port;
static uint32_t sequence, move_id, row_id, phase_id, axis_id, dir_id, distance_um;
static bool aborted, started, ready;
/* ISR only queues timestamped motor notifications; no serial printing in ISR. */
typedef struct { uint32_t tick, move, row, phase, axis, dir, distance; } Arrival;
static volatile Arrival arrival[8];
static volatile uint8_t head, tail;
static volatile uint32_t dropped;

static void Emit(uint32_t tick, const char *event, uint32_t move, uint32_t row,
                 uint32_t phase, uint32_t axis, uint32_t dir, uint32_t distance,
                 uint32_t value)
{
  char line[160];
  int count = snprintf(line, sizeof(line), "E,%lu,%lu,%s,%lu,%lu,%lu,%lu,%lu,%lu,%lu\r\n",
    (unsigned long)sequence++, (unsigned long)tick, event, (unsigned long)move,
    (unsigned long)row, (unsigned long)phase, (unsigned long)axis,
    (unsigned long)dir, (unsigned long)distance, (unsigned long)value);
  if ((count <= 0) || (count >= (int)sizeof(line)) ||
      (HAL_UART_Transmit(&port, (uint8_t *)line, (uint16_t)count, 100U) != HAL_OK))
  {
    aborted = true;
  }
}
#endif

void Lab_Init(void)
{
#if LAB_LOG_ENABLE
  GPIO_InitTypeDef pins = {0};
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_USART3_CLK_ENABLE();
  pins.Pin = GPIO_PIN_10;
  pins.Mode = GPIO_MODE_AF_PP;
  pins.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOB, &pins);
  pins.Pin = GPIO_PIN_11;
  pins.Mode = GPIO_MODE_INPUT;
  pins.Pull = GPIO_PULLUP;
  HAL_GPIO_Init(GPIOB, &pins);
  port.Instance = USART3;
  port.Init.BaudRate = 115200;
  port.Init.WordLength = UART_WORDLENGTH_8B;
  port.Init.StopBits = UART_STOPBITS_1;
  port.Init.Parity = UART_PARITY_NONE;
  port.Init.Mode = UART_MODE_TX_RX;
  port.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  port.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&port) != HAL_OK) { aborted = true; return; }
  Lab_Event("BOOT", 1U);
  Lab_Event("MODE", SCAN_MODE);
  Lab_Event("EXPERIMENT", LAB_EXPERIMENT);
  Lab_Event("STAGE", SCAN_STAGE);
  Lab_Event("WIDTH_UM", MASK_SCAN_WIDTH_UM);
  Lab_Event("HEIGHT_UM", MASK_SCAN_HEIGHT_UM);
  Lab_Event("STEP_UM", SCAN_LINE_STEP_UM);
  Lab_Event("RPM", SCAN_SPEED_RPM);
  Lab_Event("LEAD_UM", LEAD_UM_PER_REV);
  Lab_Event("ACC", SCAN_ACCELERATION);
#endif
}

void Lab_Context(uint32_t move, uint32_t row, uint32_t phase,
                 uint32_t axis, uint32_t direction, uint32_t distance)
{
#if LAB_LOG_ENABLE
  __disable_irq();
  move_id=move; row_id=row; phase_id=phase; axis_id=axis; dir_id=direction; distance_um=distance;
  __enable_irq();
#else
  (void)move; (void)row; (void)phase; (void)axis; (void)direction; (void)distance;
#endif
}

void Lab_Event(const char *event, uint32_t value)
{
#if LAB_LOG_ENABLE
  Emit(HAL_GetTick(), event, move_id, row_id, phase_id, axis_id, dir_id, distance_um, value);
#else
  (void)event; (void)value;
#endif
}

void Lab_MotorRx(const uint8_t *data, uint16_t length, uint32_t tick)
{
#if LAB_LOG_ENABLE
  uint16_t i;
  /* Only complete four-byte protocol frames; never scan arbitrary byte offsets. */
  if (length % 4U != 0U) { return; }
  for (i=0U; i<length; i+=4U)
  {
    if ((data[i] == axis_id) && (data[i+1U] == 0xFDU) &&
        (data[i+2U] == 0x9FU) && (data[i+3U] == 0x6BU))
    {
      uint8_t next=(uint8_t)((head+1U)%8U);
      if (next == tail) { ++dropped; continue; }
      arrival[head].tick=tick; arrival[head].move=move_id; arrival[head].row=row_id;
      arrival[head].phase=phase_id; arrival[head].axis=axis_id;
      arrival[head].dir=dir_id; arrival[head].distance=distance_um;
      head=next;
    }
  }
#else
  (void)data; (void)length; (void)tick;
#endif
}

void Lab_Service(void)
{
#if LAB_LOG_ENABLE
  if (__HAL_UART_GET_FLAG(&port, UART_FLAG_ORE))
  {
    __HAL_UART_CLEAR_OREFLAG(&port);
    aborted=true;
  }
  if (__HAL_UART_GET_FLAG(&port, UART_FLAG_RXNE))
  {
    uint8_t command=(uint8_t)port.Instance->DR;
    if (command == '!') { aborted=true; Lab_Event("ABORT_REQUEST",0U); }
    else if (command == '?') { Lab_Event("SYNC",0U); }
    else if ((command == 'G') && ready && !started && !aborted) { started=true; }
  }
  while (tail != head)
  {
    Arrival a;
    __disable_irq();
    a=arrival[tail]; tail=(uint8_t)((tail+1U)%8U);
    __enable_irq();
    Emit(a.tick,"DRIVER_REACHED_RX",a.move,a.row,a.phase,a.axis,a.dir,a.distance,0U);
  }
  if (dropped != 0U)
  {
    uint32_t lost;
    __disable_irq(); lost=dropped; dropped=0U; __enable_irq();
    Lab_Event("LOG_LOST",lost);
    aborted=true;
  }
#endif
}

bool Lab_Aborted(void)
{
#if LAB_LOG_ENABLE
  return aborted;
#else
  return false;
#endif
}

void Lab_Delay(uint32_t ms)
{
#if LAB_LOG_ENABLE
  uint32_t begin=HAL_GetTick();
  do { Lab_Service(); if (Lab_Aborted()) { return; } HAL_Delay(1U); }
  while ((uint32_t)(HAL_GetTick()-begin)<ms);
#else
  HAL_Delay(ms);
#endif
}

bool Lab_WaitStart(void)
{
#if LAB_LOG_ENABLE
  uint32_t last=HAL_GetTick();
  ready=true;
  Lab_Event("READY",0U);
  while (!started && !aborted)
  {
    Lab_Delay(5U);
    if ((uint32_t)(HAL_GetTick()-last)>=1000U)
    { Lab_Event("READY",0U); last=HAL_GetTick(); }
  }
  ready=false;
  return !aborted;
#else
  return true;
#endif
}
