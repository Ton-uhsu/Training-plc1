from collections import deque
import csv
from datetime import datetime
from pathlib import Path
import matplotlib.animation as animation
import matplotlib.pyplot as plt
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

# --- ตั้งค่าการเชื่อมต่อ ---
COM_PORT = "COM6"  # พอร์ต USB-RS485
BAUDRATE = 9600
SLAVE_ID = 1
REGISTER_ADDRESS = 1  # D1
CSV_FILENAME = Path(__file__).resolve().parent / "plc_voltage_log.csv"
MAX_POINTS = 50  # จำนวนจุดข้อมูลที่จะแสดงบนกราฟ (ย้อนหลัง 50 จุด)

# --- ตัวแปรเก็บข้อมูลสำหรับพล็อตกราฟ ---
x_data = deque(maxlen=MAX_POINTS)
y_data = deque(maxlen=MAX_POINTS)

# 1. เตรียมไฟล์ CSV
with CSV_FILENAME.open(mode="a", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    if file.tell() == 0:
        writer.writerow(["Timestamp", "Raw_AD (D1)", "Voltage_V"])

# 2. เชื่อมต่อ Serial
try:
    client = ModbusSerialClient(
        port=COM_PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=1,
        unit_id=SLAVE_ID,
    )
except TypeError:
    client = ModbusSerialClient(
        port=COM_PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=1,
    )

if not client.connect():
    print(f" ไม่สามารถเปิดพอร์ต {COM_PORT} ได้")
    exit()

# 3. ตั้งค่าหน้าต่างกราฟ
fig, ax = plt.subplots(figsize=(10, 5))
fig.canvas.manager.set_window_title("PLC FX3U - Realtime Voltage Monitor")
(line,) = ax.plot([], [], color="#007acc", linewidth=2, marker="o", markersize=4)

ax.set_ylim(-0.5, 10.5)  # แกน Y ล็อคช่วง 0 - 10V
ax.set_title("Real-Time Voltage Monitoring (0 - 10V)", fontsize=14, fontweight="bold")
ax.set_xlabel("Time (HH:MM:SS)", fontsize=11)
ax.set_ylabel("Voltage (V)", fontsize=11)
ax.grid(True, linestyle="--", alpha=0.6)


# 4. ฟังก์ชันอัปเดตกราฟและบันทึกข้อมูล
def update_plot(frame):
    try:
        result = client.read_holding_registers(
            address=REGISTER_ADDRESS, count=1, device_id=SLAVE_ID
        )

        if (
            result is not None
            and not result.isError()
            and hasattr(result, "registers")
        ):
            raw_value = result.registers[0]  # ค่าดิบ 0 - 4095
            voltage = round((raw_value / 4095.0) * 10.0, 2)
            now_time = datetime.now().strftime("%H:%M:%S")
            now_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # บันทึกข้อมูลลง CSV
            with CSV_FILENAME.open(
                mode="a", newline="", encoding="utf-8"
            ) as file:
                writer = csv.writer(file)
                writer.writerow([now_full, raw_value, voltage])

            # เพิ่มข้อมูลเข้าคิวพล็อตกราฟ
            x_data.append(now_time)
            y_data.append(voltage)

            # อัปเดตข้อมูลเส้นกราฟ
            line.set_data(range(len(y_data)), y_data)
            ax.set_xlim(0, max(MAX_POINTS, len(y_data)))
            ax.set_xticks(range(len(x_data)))
            ax.set_xticklabels(x_data, rotation=45, ha="right", fontsize=8)

            # ปรับ Title แสดงค่าปัจจุบัน
            ax.set_title(
                f"Real-Time Voltage: {voltage:.2f} V  |  Raw AD (D1): {raw_value}",
                fontsize=13,
                color="#003366",
            )
    except ModbusException:
        pass

    return (line,)


# ตั้งให้อัปเดตทุก 500 ms (0.5 วินาที)
ani = animation.FuncAnimation(
    fig, update_plot, interval=500, blit=False, cache_frame_data=False
)

plt.tight_layout()

try:
    plt.show()
finally:
    client.close()
    print("\n ปิดการเชื่อมต่อและบันทึกข้อมูลเรียบร้อย")
