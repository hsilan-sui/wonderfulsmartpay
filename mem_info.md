## 記憶體資訊

- 還是要把 Data_while 中的悠遊卡中斷程式拆出來
- data 不要放太多函式

```bash
Debugger:[update]: 遠端與本地檔案一致 no update 70752
ESP OTA OK
[main]: 執行Data_Collection_Main.py...
Debugger:[main.py] 執行Data_Collection_Main.py之前 記憶體:
stack: 640 out of 15360
GC: total: 108032, used: 37216, free: 70816
 No. of 1-blocks: 339, 2-blocks: 79, max blk sz: 640, max free sz: 3645
Debugger:[Data_Collection_Main] 首行，記憶體:
stack: 1184 out of 15360
GC: total: 108032, used: 45808, free: 62224
 No. of 1-blocks: 407, 2-blocks: 97, max blk sz: 640, max free sz: 2808

開始執行Data_Collection_Main.py初始化，版本為: VO1_02a_debug
開機秒數: 96.984
33008
1開機秒數: 97.015
2開機秒數: 97.03501

Init, MainStatus: NONE_WIFI
[UartHandler] 初始化完成: UART(2, baudrate=19200, bits=8, parity=None, stop=1, tx=17, rx=16, rts=-1, cts=-1, txbuf=256, rxbuf=256, timeout=0, timeout_char=1)
Get token: 123456789012345678901234567890123456
debug: [uart_manager.receive_packet 執行緒啟動中..]:

###################################################33
[Data while之前]記憶體:
stack: 1184 out of 15360
GC: total: 108032, used: 77136, free: 30896
 No. of 1-blocks: 778, 2-blocks: 208, max blk sz: 640, max free sz: 679
####################################################
這裡max free sz 只剩下679
#######################################################
now_main_state: WiFi is disconnect, 開機秒數: 99.901
My IP Address: 192.168.2.157
My MAC Address: E831CD245274

Action: WiFi is OK, MainStatus: NONE_INTERNET

now_main_state: WiFi is OK, 開機秒數: 100.905

Action: Internet is OK, MainStatus: NONE_MQTT
now_main_state: Internet is OK, 開機秒數: 101.913
更新 LCD 顯示時間: 03/07 17:39
MQTT broker connection OK!
debug: [Step 5: MQTT 訂閱主題]
MQTT Subscribe topic: E831CD245274/123456789012345678901234567890123456/commands
MQTT Subscribe topic: E831CD245274/123456789012345678901234567890123456/fota
[mqtt_manager(check_rtc_on_startup)]: RTC 時間正常，無需同步

Action: MQTT is OK, MainStatus: NONE_FEILOLI
30448
更新 LCD 顯示時間: 03/07 17:39
Updating 娃娃機 機台狀態 ...
Sent packet to 娃娃機: BB 73 01 01 00 00 00 00 00 00 00 00 00 01 00 AB
DEBUG: Received Raw Data 收到執行緒receive_packet: b'-\x8a\x81\x01\x01\x13\x00\x00\x00\x00\x00\x00\x00\x01\x009'
debug: 收到有效封包: 2D 8A 81 01 01 13 00 00 00 00 00 00 00 01 00 39
debug: 解析uart封包ing: 2D 8A 81 01 01 13 00 00 00 00 00 00 00 01 00 39
Recive 娃娃機 : 二、主控制\æ��台狀態
debug:[uart_handler] 已處理LCD_update_flag

Action: FEILOLI UART is OK, MainStatus: STANDBY_FEILOLI
debug: 已發送給解析封包 parse_packet 功能去了 2D 8A 81 01 01 13 00 00 00 00 00 00 00 01 00 39


```
