/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "dma.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

#include "Emm_V5.h"
#include "snake_scan_config.h"

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

#define MOTOR_STATUS_REACHED_MASK    0x02U
#define EMM_REPLY_OK                 0x02U
#define EMM_REPLY_REACHED            0x9FU
#define EMM_CHECK_BYTE               0x6BU

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */

typedef enum
{
  SCAN_STATE_BOOT = 0,
  SCAN_STATE_ID_SETUP_DONE,
  SCAN_STATE_CHECKING_AXES,
  SCAN_STATE_SAFE_LOCKED,
  SCAN_STATE_START_DELAY,
  SCAN_STATE_MOVING_X,
  SCAN_STATE_MOVING_Y,
  SCAN_STATE_FINISHED,
  SCAN_STATE_ERROR,
  SCAN_STATE_RETURNING_X
} ScanState_t;

/* Runtime state variables for scan progress and fault diagnosis. */
volatile ScanState_t scan_state = SCAN_STATE_BOOT;
volatile uint8_t scan_error = 0U;
volatile uint32_t scan_line = 0U;
volatile uint32_t scan_x_offset_um = 0U;
volatile uint32_t scan_y_offset_um = 0U;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */

static void Scan_ClearRxFrame(void);
static bool Scan_TakeRxFrame(uint8_t *frame, uint8_t *length);
static bool Scan_RestartUartRx(void);
static bool Scan_WaitReply(uint8_t addr, uint8_t code, uint8_t *value,
                           uint32_t timeout_ms);
static bool Scan_ReadMotorStatus(uint8_t addr, uint8_t *status);
static bool Scan_CheckAxis(uint8_t addr);
static bool Scan_ResetMotorCounter(uint8_t addr);
static bool Scan_WaitAxisReached(uint8_t addr, uint32_t timeout_ms,
                                  uint32_t sent_tick, uint32_t nominal_ms,
                                  bool accepted);
static bool Scan_MoveRelative(uint8_t addr, uint8_t direction,
                              uint32_t distance_um, uint32_t timeout_ms);
static void Scan_LedOn(void);
static void Scan_LedOff(void);
static void Scan_StartCountdown(void);
static void Scan_ShowErrorForever(uint8_t error_code);
static void Scan_Fail(uint8_t error_code);
static void SnakeScan(void);

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

static void Scan_ClearRxFrame(void)
{
  __disable_irq();
  rxFrameFlag = false;
  rxCount = 0U;
  __enable_irq();
}

static bool Scan_TakeRxFrame(uint8_t *frame, uint8_t *length)
{
  uint8_t i;
  uint8_t count;

  if (rxFrameFlag == false)
  {
    return false;
  }

  __disable_irq();
  count = rxCount;
  if (count > 16U)
  {
    count = 16U;
  }
  for (i = 0U; i < count; ++i)
  {
    frame[i] = rxCmd[i];
  }
  rxFrameFlag = false;
  rxCount = 0U;
  __enable_irq();

  *length = count;
  return true;
}

static bool Scan_RestartUartRx(void)
{
  if (HAL_UART_AbortReceive(&huart1) != HAL_OK)
  {
    return false;
  }

  __HAL_UART_CLEAR_OREFLAG(&huart1);
  __HAL_UART_CLEAR_IDLEFLAG(&huart1);
  Scan_ClearRxFrame();

  return (UART1_StartReceiveToIdle() == HAL_OK);
}

static bool Scan_WaitReply(uint8_t addr, uint8_t code, uint8_t *value,
                           uint32_t timeout_ms)
{
  uint8_t frame[16];
  uint8_t length;
  uint8_t i;
  uint32_t start_tick = HAL_GetTick();

  while ((uint32_t)(HAL_GetTick() - start_tick) < timeout_ms)
  {
    if (Scan_TakeRxFrame(frame, &length))
    {
      /* Search in case two short frames arrived in one DMA buffer. */
      for (i = 0U; (uint8_t)(i + 3U) < length; ++i)
      {
        if ((frame[i] == addr) &&
            (frame[i + 1U] == code) &&
            (frame[i + 3U] == EMM_CHECK_BYTE))
        {
          *value = frame[i + 2U];
          return true;
        }
      }
    }
  }

  return false;
}

static bool Scan_ReadMotorStatus(uint8_t addr, uint8_t *status)
{
  uint8_t attempt;

  for (attempt = 0U; attempt < MOTOR_COMM_RETRY_COUNT; ++attempt)
  {
    Scan_ClearRxFrame();
    Emm_V5_Read_Sys_Params(addr, S_FLAG);

    if (Scan_WaitReply(addr, 0x3AU, status, MOTOR_REPLY_TIMEOUT_MS))
    {
      return true;
    }

    /* Recover a UART/DMA receiver that stopped seeing RS485 replies. */
    if (!Scan_RestartUartRx())
    {
      return false;
    }
    HAL_Delay(MOTOR_COMM_RETRY_DELAY_MS);
  }

  return false;
}

static bool Scan_CheckAxis(uint8_t addr)
{
  uint8_t status;
  return Scan_ReadMotorStatus(addr, &status);
}

static bool Scan_ResetMotorCounter(uint8_t addr)
{
  uint8_t reply;

  Scan_ClearRxFrame();
  Emm_V5_Reset_CurPos_To_Zero(addr);

  if (!Scan_WaitReply(addr, 0x0AU, &reply, MOTOR_REPLY_TIMEOUT_MS))
  {
    return false;
  }

  return (reply == EMM_REPLY_OK);
}

static bool Scan_WaitAxisReached(uint8_t addr, uint32_t timeout_ms,
                                  uint32_t sent_tick, uint32_t nominal_ms,
                                  bool accepted)
{
  bool moving_seen = false;
  uint8_t reached_count = 0U;
  uint8_t status;
  uint32_t start_tick = HAL_GetTick();

  while ((uint32_t)(HAL_GetTick() - start_tick) < timeout_ms)
  {
    HAL_Delay(STATUS_POLL_INTERVAL_MS);

    if (Scan_ReadMotorStatus(addr, &status))
    {
      if ((status & MOTOR_STATUS_REACHED_MASK) == 0U)
      {
        moving_seen = true;
        reached_count = 0U;
      }
      else if ((moving_seen || accepted) &&
               ((uint32_t)(HAL_GetTick() - sent_tick) >= nominal_ms))
      {
        /* Short moves may finish before the first status query. Require an
         * acceptance acknowledgement or observed motion, then two reached
         * samples; an unsolicited FD/9F alone is never completion authority.
         * This checks driver status, not the measured mechanical position. */
        if (++reached_count >= 2U)
        {
          return true;
        }
      }
    }
    else
    {
      reached_count = 0U;
    }
  }

  return false;
}

static bool Scan_MoveRelative(uint8_t addr, uint8_t direction,
                              uint32_t distance_um, uint32_t timeout_ms)
{
  bool reply_received;
  uint8_t reply;
  uint32_t pulses = (uint32_t)DISTANCE_PULSES(distance_um);
  uint32_t sent_tick = HAL_GetTick();
  uint32_t nominal_ms = (uint32_t)MOVE_NOMINAL_MS(distance_um);

  if (pulses == 0U)
  {
    return false;
  }

  Scan_ClearRxFrame();
  Emm_V5_Pos_Control(addr, direction, SCAN_SPEED_RPM, SCAN_ACCELERATION,
                     pulses, 2U, false);

  reply_received = Scan_WaitReply(addr, 0xFDU, &reply,
                                  MOTOR_REPLY_TIMEOUT_MS);

  if (reply_received && (reply != EMM_REPLY_OK) &&
      (reply != EMM_REPLY_REACHED))
  {
    return false;
  }

  /* Receive/Both response mode is required for reliable short moves.
   * With no acknowledgement and no observed motion, stop on timeout rather
   * than assuming that an idle motor received the command. Never resend it. */
  return Scan_WaitAxisReached(addr, timeout_ms, sent_tick, nominal_ms,
                             reply_received && (reply == EMM_REPLY_OK));
}

/* Xiaozhi dual-USB board red status LED on PA1 is active-low. */
static void Scan_LedOn(void)
{
  HAL_GPIO_WritePin(STATUS_LED_RED_GPIO_Port, STATUS_LED_RED_Pin, GPIO_PIN_RESET);
}

static void Scan_LedOff(void)
{
  HAL_GPIO_WritePin(STATUS_LED_RED_GPIO_Port, STATUS_LED_RED_Pin, GPIO_PIN_SET);
}

static void Scan_StartCountdown(void)
{
  uint8_t i;

  /* One visible flash per second before any motion starts. */
  for (i = 0U; i < SCAN_START_COUNTDOWN_SECONDS; ++i)
  {
    Scan_LedOn();
    HAL_Delay(250U);
    Scan_LedOff();
    HAL_Delay(750U);
  }
}

static void Scan_ShowErrorForever(uint8_t error_code)
{
  uint8_t i;

  while (1)
  {
    for (i = 0U; i < error_code; ++i)
    {
      Scan_LedOn();
      HAL_Delay(200U);
      Scan_LedOff();
      HAL_Delay(200U);
    }
    HAL_Delay(1200U);
  }
}

static void Scan_Fail(uint8_t error_code)
{
  scan_error = error_code;
  scan_state = SCAN_STATE_ERROR;

  /* Broadcast immediate stop. Both axes retain holding torque. */
  Scan_ClearRxFrame();
  Emm_V5_Stop_Now(0U, false);
  HAL_Delay(100U);
  Scan_ShowErrorForever(error_code);
}

static void SnakeScan(void)
{
  uint32_t pass;
  uint8_t x_direction;

  for (pass = 0U; pass < ACTIVE_HORIZONTAL_PASS_COUNT; ++pass)
  {
    scan_line = pass + 1U;
    x_direction = ((SCAN_MODE == 1U) || ((pass & 1U) == 0U)) ? X_FIRST_PASS_DIRECTION
                                      : X_ALTERNATE_PASS_DIRECTION;

    /* Only this X leg is an imaging pass in unidirectional mode. */
    scan_state = SCAN_STATE_MOVING_X;
    if (!Scan_MoveRelative(X_AXIS_ADDR, x_direction,
                           ACTIVE_SCAN_WIDTH_UM, X_MOVE_TIMEOUT_MS))
    {
      Scan_Fail(3U);
    }
    scan_x_offset_um = ((SCAN_MODE == 1U) || ((pass & 1U) == 0U)) ?
                       ACTIVE_SCAN_WIDTH_UM : 0U;
    HAL_Delay(AXIS_SWITCH_DELAY_MS);

    if (SCAN_MODE == 1U)
    {
      /* Nominal return, not mechanical homing. Do not image this leg. */
      scan_state = SCAN_STATE_RETURNING_X;
      if (!Scan_MoveRelative(X_AXIS_ADDR, X_ALTERNATE_PASS_DIRECTION,
                             ACTIVE_SCAN_WIDTH_UM, X_MOVE_TIMEOUT_MS))
      {
        Scan_Fail(8U);
      }
      scan_x_offset_um = 0U;
      HAL_Delay(AXIS_SWITCH_DELAY_MS);
    }

    /* Every completed horizontal line is followed by one upward line step. */
    scan_state = SCAN_STATE_MOVING_Y;
    if (!Scan_MoveRelative(Y_AXIS_ADDR, Y_STEP_DIRECTION,
                           ACTIVE_LINE_STEP_UM, Y_MOVE_TIMEOUT_MS))
    {
      Scan_Fail(4U);
    }
    scan_y_offset_um += ACTIVE_LINE_STEP_UM;
    HAL_Delay(AXIS_SWITCH_DELAY_MS);
  }

  scan_state = SCAN_STATE_FINISHED;
  Scan_LedOn();
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_USART1_UART_Init();
  /* USER CODE BEGIN 2 */
  if (UART1_StartReceiveToIdle() != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN WHILE */

/**********************************************************
***	上电延时500毫秒等待闭环初始化完毕
**********************************************************/	
	HAL_Delay(500);

  if (Y_AXIS_ID_SETUP_ONCE != 0U)
  {
    /* Only the Y motor may be connected while this one-time mode is enabled. */
    Scan_ClearRxFrame();
    Emm_V5_Modify_Motor_ID(1U, true, Y_AXIS_ADDR);
    HAL_Delay(500U);

    if (!Scan_CheckAxis(Y_AXIS_ADDR))
    {
      Scan_Fail(5U);
    }

    scan_state = SCAN_STATE_ID_SETUP_DONE;
    Scan_LedOn();
    while (1)
    {
      HAL_Delay(1000U);
    }
  }

  scan_state = SCAN_STATE_CHECKING_AXES;
  if (!Scan_CheckAxis(X_AXIS_ADDR))
  {
    Scan_Fail(1U); /* Horizontal axis, address 2, did not reply. */
  }
  HAL_Delay(20U);
  if (!Scan_CheckAxis(Y_AXIS_ADDR))
  {
    Scan_Fail(2U); /* Vertical axis, address 1, did not reply. */
  }

  if (RESET_MOTOR_COUNTERS_AT_START != 0U)
  {
    if (!Scan_ResetMotorCounter(X_AXIS_ADDR))
    {
      Scan_Fail(6U);
    }
    HAL_Delay(20U);
    if (!Scan_ResetMotorCounter(Y_AXIS_ADDR))
    {
      Scan_Fail(7U);
    }
  }

  if (SCAN_STAGE == SCAN_STAGE_COMM_CHECK)
  {
    /* Solid LED means both addresses replied. This stage never moves. */
    scan_state = SCAN_STATE_SAFE_LOCKED;
    Scan_LedOn();
  }
  else
  {
    scan_state = SCAN_STATE_START_DELAY;
    Scan_StartCountdown();
    SnakeScan();
  }

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
