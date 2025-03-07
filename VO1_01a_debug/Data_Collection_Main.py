VERSION = "VO1_01a_debug"
import micropython
print("Debugger:[Data_Collection_Main] 首行，記憶體:")
micropython.mem_info()

#標準庫
import os
import utime
import gc
import _thread
import ujson
import machine
#外部依賴
from machine import UART, Timer, WDT
#from machine import UART, Pin, SPI, Timer, WDT
from umqtt.simple import MQTTClient
#本地
from uart_handler import UartHandler
from uart_manager import UartManager
from mqtt_manager import MqttManager
from timer_manager import TimerManager
from received_claw_data import ReceivedClawData

# =============================
# wifi連線 tets ok 
# =============================
# print(f"[Data]: wifi_manager: {wifi_manager}")
# print(f"[Data]: network_info:{network_info},{wifi_manager.ssid}")

# =============================
# 狀態類型
# =============================
# 定義狀態類型
class MainStatus:
    NONE_WIFI = 0       # 還沒連上WiFi
    NONE_INTERNET = 1   # 連上WiFi，但還沒連上外網      現在先不做這個判斷
    NONE_MQTT = 2       # 連上外網，但還沒連上MQTT Broker
    NONE_FEILOLI = 3    # 連上MQTT，但還沒連上FEILOLI娃娃機
    STANDBY_FEILOLI = 4 # 連上FEILOLI娃娃機，正常運行中
    WAITING_FEILOLI = 5 # 連上FEILOLI娃娃機，等待娃娃機回覆
    GOING_TO_OTA = 6    # 接收到要OTA，但還沒完成OTA
    UNEXPECTED_STATE = -1

# =============================
# 狀態機
# =============================
# 定義狀態機類別
class MainStateMachine:
    def __init__(self):
        self.state = MainStatus.NONE_WIFI
        # 以下執行"狀態機初始化"相應的操作
        print('\n\rInit, MainStatus: NONE_WIFI')
        GPO_CardReader_EPAY_EN.value(0)   # Wi-Fi未連線、而且娃娃機連線未確定，暫停卡機支付功能
        global main_while_delay_seconds, LCD_update_flag
        main_while_delay_seconds = 1
        LCD_update_flag['Uniform'] = True

    def transition(self, action):
        global main_while_delay_seconds, LCD_update_flag
        if action == 'WiFi is disconnect':
            self.state = MainStatus.NONE_WIFI
            # 以下執行"未連上WiFi後"相應的操作
            print('\n\rAction: WiFi is disconnect, MainStatus: NONE_WIFI')
            GPO_CardReader_EPAY_EN.value(0)   # Wi-Fi未連線、而且娃娃機連線未確定，暫停卡機支付功能
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True

        elif self.state == MainStatus.NONE_WIFI and action == 'WiFi is OK':
            self.state = MainStatus.NONE_INTERNET
            # 以下執行"連上WiFi後"相應的操作
            print('\n\rAction: WiFi is OK, MainStatus: NONE_INTERNET')
            GPO_CardReader_EPAY_EN.value(0)   # Wi-Fi已連線、但娃娃機連線未確定，暫停卡機支付功能
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True

        elif self.state == MainStatus.NONE_INTERNET and action == 'Internet is OK':
            self.state = MainStatus.NONE_MQTT
            # 以下執行"連上Internet後"相應的操作
            print('\n\rAction: Internet is OK, MainStatus: NONE_MQTT')
            GPO_CardReader_EPAY_EN.value(0)   # 外網已連線、但娃娃機連線未確定，暫停卡機支付功能
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True

        elif self.state == MainStatus.NONE_MQTT and action == 'MQTT is OK':
            self.state = MainStatus.NONE_FEILOLI
            # 以下執行"連上MQTT後"相應的操作
            print('\n\rAction: MQTT is OK, MainStatus: NONE_FEILOLI')
            GPO_CardReader_EPAY_EN.value(0)   # MQTT已連線、但娃娃機連線未確定，暫停卡機支付功能
            main_while_delay_seconds = 10
            LCD_update_flag['WiFi'] = True
            LCD_update_flag['Claw_State'] = True

        elif (self.state == MainStatus.NONE_FEILOLI or self.state == MainStatus.WAITING_FEILOLI) and action == 'FEILOLI UART is OK':
            self.state = MainStatus.STANDBY_FEILOLI
            # 以下執行"連上FEILOLI娃娃機後"相應的操作
            print('\n\rAction: FEILOLI UART is OK, MainStatus: STANDBY_FEILOLI')
            main_while_delay_seconds = 10
            LCD_update_flag['Claw_State'] = True

        elif self.state == MainStatus.STANDBY_FEILOLI and action == 'FEILOLI UART is waiting':
            self.state = MainStatus.WAITING_FEILOLI
            # 以下執行"等待FEILOLI娃娃機後"相應的操作
            print('\n\rAction: FEILOLI UART is waiting, MainStatus: WAITING_FEILOLI')
            main_while_delay_seconds = 10

        elif self.state == MainStatus.WAITING_FEILOLI and action == 'FEILOLI UART is not OK':
            self.state = MainStatus.NONE_FEILOLI
            # 以下執行"等待失敗後"相應的操作
            print('\n\rAction: FEILOLI UART is not OK, MainStatus: NONE_FEILOLI')
            GPO_CardReader_EPAY_EN.value(0)   # 娃娃機無法連線，暫停卡機支付功能
            main_while_delay_seconds = 10    
            LCD_update_flag['Claw_State'] = True

        elif (self.state == MainStatus.NONE_FEILOLI or self.state == MainStatus.STANDBY_FEILOLI or self.state == MainStatus.WAITING_FEILOLI) and action == 'MQTT is not OK':
            self.state = MainStatus.NONE_MQTT
            # 以下執行"MQTT失敗後"相應的操作
            print('\n\rAction: MQTT is not OK, MainStatus: NONE_MQTT')
            GPO_CardReader_EPAY_EN.value(0)   # MQTT無法連線，暫停卡機支付功能
            main_while_delay_seconds = 1
            LCD_update_flag['WiFi'] = True

        else:
            print('\n\rInvalid action:', action, 'for current state:', self.state)
            main_while_delay_seconds = 1


# =============================
# 娃娃機指令
# =============================
class KindFEILOLIcmd:
    Ask_Machine_status = 210
    Send_Machine_reboot = 215
    Send_Machine_shutdown = 216
    Send_Payment_countdown_Or_fail = 231
    #     Send_Starting_games = 220
    Send_Starting_once_game = 221
    Ask_Transaction_account = 321 # 查詢:遠端帳目
    Ask_Coin_account = 322 # 查詢:投幣帳目
    
    Send_Clean_transaction_account = 323 # 清除:遠端帳目
    #Clean_Coin_account = 324 ## 清除:投幣帳目
    Ask_Machine_setting = 431

def get_file_info(filename):
    try:
        file_stat = os.stat(filename)
        file_size = file_stat[6]  # Index 6 is the file size
        file_mtime = file_stat[8]  # Index 8 is the modification time
        return file_size, file_mtime
    except OSError:
        return None, None



##### GPO ###############################################    
# 這段主要在設定GPIO 通用輸入輸出 並監聽悠遊卡付款訊號  
# 偵測悠遊卡付款時 ===> 會觸發娃娃機開始遊戲
# GPIO 21 23為輸出模式
# GPIO21 (GPO_IO21test) 可能是 除錯燈號或測試訊號
# GPIO23 (GPO_IO23test) 可能是 悠遊卡付款成功的指示訊號
# GPO_IO23test.value(1) → sleep(100ms) → GPO_IO23test.value(0) 代表 觸發一個短暫的訊號脈衝，可能用於：
# 通知其他元件付款成功
# 觸發 LED 指示燈
# 進行訊號測
# ##### GPO ###############################################  
# 
# 設定GPIO21 為輸出 初始值為0 
GPO_IO21test = Pin(21, Pin.OUT, value=0)
#GPO_IO21test.value(0)
utime.sleep_ms(100)
IO21value = 1
GPO_IO21test.value(IO21value)  # 將 GPIO21 設為高電位 (1)

# 設定 GPIO23 為輸出，初始值 0
GPO_IO23test = Pin(23, Pin.OUT,value=0)
#GPO_IO23test.value(0)
utime.sleep_ms(100)
IO23value = 1
GPO_IO23test.value(1)# 設為高電位
utime.sleep_ms(100)
GPO_IO23test.value(0) # 設為低電位

##########################################################################################
############################################# 初始化 #############################################

print(f"\n\r開始執行Data_Collection_Main.py初始化，版本為: {VERSION}")
print(f"開機秒數: {utime.ticks_ms() / 1000}")

gc.collect()
print(gc.mem_free())

# 開啟 token 檔案
#load_token()

WDT_feed_flag = 0
wdt=WDT(timeout=1000*60*10)

print(f"1開機秒數: {utime.ticks_ms() / 1000}")


LCD_update_flag = {
    'Uniform': True,
    'WiFi': False,
    'Time': False,
    'Claw_State': False,
    'Claw_Value': False,
}

print(f"2開機秒數: {utime.ticks_ms() / 1000}")

# GPIO配置
# 卡機端的TV-1QR、觸控按鈕配置
GPIO_CardReader_PAYOUT = Pin(18, Pin.IN, Pin.PULL_UP)
GPO_CardReader_EPAY_EN = Pin(2, Pin.OUT, value=0)
#GPO_CardReader_EPAY_EN.value(0)

# 娃娃機端的投幣器、電眼配置
#GPO_Claw_Coin_EN = Pin(5, Pin.OUT)



# 創建狀態機
now_main_state = MainStateMachine()
# 創建娃娃機資料
claw_1 = ReceivedClawData()
# 創建 MQTT Client 1 資料
mq_client_1 = None

#==============
# # UART配置(改成初始化UART阜口)
# 涵蓋娃娃機參數 UART類別 KindFEILOLIcmd類別
# KindFEILOLIcmd先用參數傳遞(娃娃機指令)
# claw_1 也先用參數傳遞(娃娃機數據)
#創建 UART Handler，讓它持有 `mqtt_handler`
#==============
# UART配置
# print("Debugger:[Step 1: 初始化 UART Handler] 記憶體:")
# micropython.mem_info()
uart_handler = UartHandler(claw_1, None, LCD_update_flag, now_main_state, GPO_CardReader_EPAY_EN) # 但先不設定 mqtt_handler=None

# print("Debugger:[Step 2: 初始化 UART Manager] 記憶體:")
# micropython.mem_info()
uart_manager = UartManager(claw_1=claw_1,
    KindFEILOLIcmd=KindFEILOLIcmd,
    uart_handler=uart_handler,
    mqtt_handler=None) # 先不設定 mqtt_handler=None) 

#==============
# 1.mqtt_manager初始化(已含toke取得)
# 涵蓋娃娃機參數 UART類別 KindFEILOLIcmd類別
#==============
# print(f"wifi_manager: {wifi_manager}")  # 檢查 wifi_manager 是否有值
# print(VERSION)
# print(network_info["mac"])


#要測試UART_MANAGEr
# print("Debugger:[Step 3: 初始化 MQTT Manager | MqttHandler也在其中初始化] 記憶體:")
# micropython.mem_info()
mqtt_manager = MqttManager(
    mac_id=network_info["mac"],
    claw_1=claw_1,
    KindFEILOLIcmd=KindFEILOLIcmd,
    version=VERSION,
    wifi_manager=wifi_manager,
    uart_manager=uart_manager,
    LCD_update_flag=LCD_update_flag
) #並在其中建立 mqtt_handler()



#==============

#==============
# print("Debugger:[Step 4: 相互依賴解耦與物件關聯初始化] 記憶體:")
# micropython.mem_info()
# gc.collect()

## ==============
# 避免在初始化階段因物件還未建立好就被呼叫，導致 NoneType 錯誤。
# 等到所有物件都建立完成後，再進行後設綁定，確保每個類別都能正確存取到其他類別的實體物件
## ==============
## 這時候 `mqtt_manager` 已經初始化完畢，直接取出 `mqtt_manager.mqtt_handler`
mqtt_handler = mqtt_manager.mqtt_handler  # 直接用 `MqttManager` 內建的 `MqttHandler`

uart_manager.mqtt_handler = mqtt_handler

uart_handler.mqtt_handler = mqtt_handler

mqtt_manager.uart_manager = uart_manager

gc.collect()




########################
# 定義GPI中斷處理函式
# GPI（General Purpose Input）中斷處理
###########################
# # 記錄時間變數（毫秒）
PAYOUT_falling_time = utime.ticks_ms()
PAYOUT_last_rising_time = utime.ticks_ms()

# 悠遊卡讀卡機訊號的中斷處理函式
def GPI_interrupt_handler(pin):
    global PAYOUT_falling_time, PAYOUT_last_rising_time, IO21value

    IO21value = not IO21value  # 變更 GPIO21 的狀態（高 <-> 低）
    GPO_IO21test.value(IO21value)  # 可能用於指示付款事件發生

    PAYOUT_value = GPIO_CardReader_PAYOUT.value()  # 讀取悠遊卡付款訊號
    PAYOUT_now_time = utime.ticks_ms()  # 紀錄目前時間（毫秒）
    
    print(f"悠遊卡訊號變化: {PAYOUT_value}，時間: {PAYOUT_now_time} ms")

    if pin == GPIO_CardReader_PAYOUT:  # 檢查是否為付款訊號觸發
        print("PAYOUT收到中斷:", PAYOUT_value)
        if PAYOUT_value == 0:  # **負緣觸發**（代表開始付款）
            PAYOUT_falling_time = PAYOUT_now_time
            print("偵測到付款開始（負緣觸發）")

        elif PAYOUT_value == 1:  # **正緣觸發**（代表付款完成）
            PAYOUT_rising_time = PAYOUT_now_time
            PAYOUT_hipulse_time = PAYOUT_falling_time - PAYOUT_last_rising_time  # 計算高電位時間
            PAYOUT_lowpulse_time = PAYOUT_rising_time - PAYOUT_falling_time  # 計算低電位時間
            print(f"偵測到付款完成（正緣觸發）")
            print("中斷PAYOUT收到Hi Pulse，寬度(ms):", PAYOUT_hipulse_time, ",和Low Pulse，寬度(ms):", PAYOUT_lowpulse_time)

            # **確認訊號是否合法**
            if PAYOUT_hipulse_time >= 100 and (50 <= PAYOUT_lowpulse_time <= 200):
                print("付款訊號有效，觸發娃娃機開始遊戲")
                print("Pulse的Hi和Lo寬度都正確，啟動娃娃機遊戲")
                #===================test==============
                utime.sleep_ms(500)
                #uart_FEILOLI_send_packet(KindFEILOLIcmd.Send_Starting_once_game)  # **通知娃娃機開始遊戲**
                uart_manager.send_packet(KindFEILOLIcmd.Send_Starting_once_game)
                
                utime.sleep_ms(100)  # 確保有時間接收回傳資料
                response = uart_manager.uart_FEILOLI.read()
                print(f"[DEBUG] UART 回應: {response}")
            else:
                print("Pulse的Hi或Lo寬度不正確，不進行任何動作")
            PAYOUT_last_rising_time = PAYOUT_rising_time  # 更新最後一次的付款完成時間
# GPIO 中斷配置
# 設定TV-1QR PAYOUT中斷，觸發條件為正緣和負緣
GPIO_CardReader_PAYOUT.irq(trigger = (Pin.IRQ_FALLING | Pin.IRQ_RISING ), handler = GPI_interrupt_handler)

## ==============
# 避免在初始化階段因物件還未建立好就被呼叫，導致 NoneType 錯誤。
# 等到所有物件都建立完成後，再進行後設綁定，確保每個類別都能正確存取到其他類別的實體物件
## ==============


# ========================
# 初始化timer
# =========================
timer_manager = TimerManager(now_main_state, MainStatus, wifi_manager, uart_manager, mqtt_manager, mqtt_handler, lcd_mgr, wdt, LCD_update_flag, claw_1, WDT_feed_flag,GPO_IO23test)

gc.collect()
# print("Debugger:[準備執行緒] 記憶體:")
# micropython.mem_info()

_thread.stack_size(16 * 1024)  # 只需設置一次
#_thread.stack_size(20 * 1024)  # 只需設置一次
_thread.start_new_thread(uart_manager.receive_packet, ())


utime.sleep(2) 


# ========================
# 執行timer callback
# =========================
timer_manager.start_timers()

print("[Data while之前]記憶體:")
micropython.mem_info()

last_time = 0
main_while_delay_seconds = 1
while True:

    utime.sleep_ms(500)
    if WDT_feed_flag == 1 :
        WDT_feed_flag = 0
        wdt.feed()
        print('WDT fed! 開機秒數:', utime.ticks_ms() / 1000)

    current_time = utime.ticks_ms()
    if (utime.ticks_diff(current_time, last_time) >= main_while_delay_seconds * 1000):
        last_time = utime.ticks_ms()

        if now_main_state.state == MainStatus.NONE_WIFI:
            print('\n\rnow_main_state: WiFi is disconnect, 開機秒數:', current_time / 1000)

            # =============================
            # network_info
            # =============================
            print("My IP Address:", network_info['ip'])
            print("My MAC Address:", network_info['mac'])
            now_main_state.transition('WiFi is OK')
            

        elif now_main_state.state == MainStatus.NONE_INTERNET:
            print('\n\rnow_main_state: WiFi is OK, 開機秒數:', current_time / 1000)
            now_main_state.transition('Internet is OK')  # 目前不做判斷，狀態機直接往下階段跳轉

        elif now_main_state.state == MainStatus.NONE_MQTT:
            print('now_main_state: Internet is OK, 開機秒數:', current_time / 1000)
            # =============================
            # 連線mqtt
            # =============================
            # 連線 MQTT
            mqtt_manager.connect_mqtt()
            mq_client_1 = mqtt_manager.client

            if mq_client_1 is not None:
                try:
                    now_main_state.transition('MQTT is OK')
                except:
                    print('MQTT subscription has failed')
            gc.collect()
            print(gc.mem_free())

        elif now_main_state.state == MainStatus.NONE_FEILOLI:
            print('\n\rnow_main_state: MQTT is OK (FEILOLI UART is not OK), 開機秒數:', current_time / 1000)
            gc.collect()
            print(gc.mem_free())

        elif now_main_state.state == MainStatus.STANDBY_FEILOLI:
            print('\n\rnow_main_state: FEILOLI UART is OK, 開機秒數:', current_time / 1000)
            gc.collect()
            print(gc.mem_free())

        elif now_main_state.state == MainStatus.WAITING_FEILOLI:
            print('\n\rnow_main_state: FEILOLI UART is witing, 開機秒數:', current_time / 1000)
            gc.collect()
            print(gc.mem_free())
            

        else:
            print('\n\rInvalid action! now_main_state:', now_main_state.state)
            print('開機秒數:', current_time / 1000)
            gc.collect()

        LCD_update_flag['Time'] = True
