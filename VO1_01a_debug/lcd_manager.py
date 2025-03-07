"""lcd 管理類別 提供操作st7735 lcd的方法"""
import gc
from machine import Pin, SPI


class LCDManager:
    _instance = None

    # @classmethod/裝飾器（Decorator），用來定義類方法（Class Method）
    # 類方法與一般的實例方法（Instance Method）不同，它的第一個參數是 cls，代表類別本身
    @classmethod
    # @classmethod 讓 get_instance(cls) 可以直接由類別 LCDManager 呼叫，而不用先建立物件
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if LCDManager._instance is not None:
            raise Exception("請使用 get_instance() 取得實例")
        
        #延遲初始化
        self.st7735 = None
        self.dis = None
        self.color = None
        self.spi = None
        self.spleen16 = None

    def initialize(self, baudrate=20000000, sck_pin=14, mosi_pin=13, rotate=0):
        """初始化 LCD """
        if self.st7735 is not None:
            print("[lcd_manager]:　LCD已初始化")
            return 
        
        try:
            print("[lcd_manager]: 初始化 SPI 和 LCD...")
            # 初始化 SPI
            self.spi = SPI(1, baudrate=baudrate, polarity=0, phase=0, sck=Pin(sck_pin), mosi=Pin(mosi_pin))

            # 初始化 ST7735
            from dr.st7735.st7735_4bit import ST7735
            self.st7735 = ST7735(self.spi, 4, 15, None, 128, 160, rotate=rotate)
            self.st7735.initb2()
            self.st7735.setrgb(True)

            # 初始化顏色
            from gui.colors import colors
            self.color = colors(self.st7735)

            # 初始化字型
            from dr.display import display
            import fonts.spleen16 as spleen16

            #初始化繪製
            self.dis = display(self.st7735, 'ST7735_FB', self.color.WHITE, self.color.BLUE)
            self.spleen16 = spleen16

            print("[lcd_manager]: 已完成LCD初始化")
        except Exception as e:
            print(f"[lcd_manager]: LCD初始化失敗: {e}")
            self.cleanup()
            raise

    def fill(self, bgcolor=None):
        if not self.dis:
            print("[lcd_manager]: LCD尚未初始化，正在初始化...")
            self.initialize()
        
        # 預設使用黑色
        bgcolor = bgcolor if bgcolor is not None else self.color.BLACK

        self.dis.fill(bgcolor)
        gc.collect()

    def draw_text(self, x, y, text=None, fg=None, bg=None, bgmode=0, scale=1):
        """在LCD上繪製內容"""
        if not self.dis:
            print("[lcd_manager]: LCD 尚未初始化，正在初始化...")
            self.initialize()

        # 初始fg顏色是白色
        # 初始bg顏色是藍色
        # 初始顯示文字 預設 'Happy Collector'
        fg = fg if fg is not None else self.color.WHITE
        bg = bg if bg is not None else self.color.BLUE
        text = text if text is not None else 'Happy Collector'

        try:
            self.dis.draw_text(self.spleen16, text, x, y, scale, fg, bg, bgmode, True, 0, 0)
        except Exception as e:
            print(f"[lcd_manager]: 繪製文字時發生錯誤: {e}")
        gc.collect()

    def show(self):
        """顯示內容到螢幕上"""
        if self.dis:
            try: 
                self.dis.dev.show()
            except Exception as e:
                print(f"[lcd_manager]: 刷新屏幕時發生錯誤: {e}")

    def is_initialized(self):
        """檢查 LCD 是否已初始化"""
        return self.st7735 is not None
    
    def cleanup(self):
        """清理 LCD 資源"""
        try:
            if self.st7735:
                self.st7735 = None

            if self.spi:
                self.spi.deinit()
                self.spi = None
            
            self.dis = None
            self.color = None
            self.spleen16 = None
            LCDManager._instance = None
            gc.collect()
            print("[lcd_manager]: LCD 資源清理完成")
        except Exception as e:
            print(f"[lcd_manager]: LCD 資源清理失敗: {e}")
