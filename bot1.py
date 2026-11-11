import sys
import traceback

try:
    import ctypes
    from ctypes import wintypes
    import io
    import time
    import pygetwindow as gw
    import requests
    from PIL import Image, ImageChops

    # --- НАЛАШТУВАННЯ ---
    TELEGRAM_BOT_TOKEN = "111111:AAAAAAAAAAAAAAAAAAAAAAAAA"
    TELEGRAM_CHAT_ID = "11111"

    CHECK_INTERVAL = 1.5      # Як часто перевіряти екран (сек)
    CHANGE_THRESHOLD = 8.0    # Поріг зміни у % (8-15%)
    COOLDOWN_SECONDS = 3.0    # Пауза після надсилання

    # Підключення WinAPI
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Дозволяє коректно отримувати координати на екранах із масштабуванням (DPI scaling)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    def send_to_telegram(image_bytes: bytes, caption: str = "Новий слайд з Teams"):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {"photo": ("slide.png", image_bytes, "image/png")}
        data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        try:
            response = requests.post(url, data=data, files=files, timeout=15)
            if response.status_code == 200:
                print("🚀 Новий слайд надіслано в Telegram!")
            else:
                print(f"❌ Помилка Telegram: {response.text}")
        except Exception as e:
            print(f"❌ Помилка з'єднання: {e}")

    def capture_window_direct(hwnd):
        """Пряме захоплення графічного буфера вікна за його дескриптором (HWND)."""
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width <= 0 or height <= 0:
            return None

        hwnd_dc = user32.GetWindowDC(hwnd)
        mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        save_bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        gdi32.SelectObject(mfc_dc, save_bitmap)

        # PW_RENDERFULLCONTENT = 2 (захоплює сучасні вікна навіть під іншими вікнами)
        result = user32.PrintWindow(hwnd, mfc_dc, 2)
        if result == 0:
            # Резервний режим, якщо прапорець 2 не підтримується
            user32.PrintWindow(hwnd, mfc_dc, 0)

        bmp_info = wintypes.BITMAPINFOHEADER()
        bmp_info.biSize = ctypes.sizeof(wintypes.BITMAPINFOHEADER)
        bmp_info.biWidth = width
        bmp_info.biHeight = -height  # Від'ємне значення, щоб зображення не було догори дриґом
        bmp_info.biPlanes = 1
        bmp_info.biBitCount = 32
        bmp_info.biCompression = 0

        buffer = ctypes.create_string_buffer(width * height * 4)
        gdi32.GetDIBits(mfc_dc, save_bitmap, 0, height, buffer, ctypes.byref(bmp_info), 0)

        # Звільнення дескрипторів Windows GDI
        gdi32.DeleteObject(save_bitmap)
        gdi32.DeleteDC(mfc_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)

        # Формування об'єкта зображення PIL
        image = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)
        return image.convert("RGB")

    def get_teams_screenshot():
        """Знаходить вікно Teams і робить його ізольований знімок."""
        windows = [w for w in gw.getWindowsWithTitle("Teams") if w.title and w.visible]
        if not windows:
            return None, None

        win = windows[0]
        # Вікно не повинно бути згорнуте в панель задач (isMinimized)
        if win.isMinimized:
            return None, None

        img = capture_window_direct(win._hWnd)
        return img, win.title

    def calculate_difference_percentage(img1, img2):
        thumb_size = (160, 90)
        i1 = img1.convert("L").resize(thumb_size)
        i2 = img2.convert("L").resize(thumb_size)

        diff = ImageChops.difference(i1, i2)
        hist = diff.histogram()

        # Сумуємо зміни яскравості пікселів > 25
        changed_pixels = sum(hist[25:])
        total_pixels = thumb_size[0] * thumb_size[1]
        return (changed_pixels / total_pixels) * 100.0

    print("=" * 60)
    print("🤖 Захоплення виключно вікна Microsoft Teams активовано!")
    print(f"🔎 Сканування кожні {CHECK_INTERVAL}с | Поріг: {CHANGE_THRESHOLD}%")
    print("=" * 60)

    last_image = None

    while True:
        current_image, title = get_teams_screenshot()

        if current_image is None:
            time.sleep(CHECK_INTERVAL)
            continue

        if last_image is not None:
            # Якщо розмір самого вікна змінився, синхронізуємо розмір
            if last_image.size != current_image.size:
                last_image = current_image
                time.sleep(CHECK_INTERVAL)
                continue

            diff_percent = calculate_difference_percentage(last_image, current_image)

            if diff_percent >= CHANGE_THRESHOLD:
                print(f"📸 Зміна слайда в Teams: {diff_percent:.1f}% площі змінилось")
                time.sleep(0.5)
                current_image, title = get_teams_screenshot()

                if current_image is not None:
                    buffer = io.BytesIO()
                    current_image.save(buffer, format="PNG")
                    buffer.seek(0)

                    send_to_telegram(
                        buffer.getvalue(),
                        caption=f"📊 Зміна слайда ({diff_percent:.1f}%)\n{title}"
                    )

                last_image = current_image
                time.sleep(COOLDOWN_SECONDS)
                continue

        last_image = current_image
        time.sleep(CHECK_INTERVAL)

except Exception:
    print("\n❌ СТАЛАСЯ ПОМИЛКА ПІД ЧАС РОБОТИ:")
    traceback.print_exc()
    input("\nНатисніть Enter, щоб закрити вікно...")