import csv
from datetime import datetime
from pathlib import Path
import time
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

# --- ตั้งค่าการเชื่อมต่อ ---
COM_PORT = "COM6"  # ตรวจสอบชื่อพอร์ตใน Device Manager
BAUDRATE = 9600  # ตรงกับ D8120
SLAVE_ID = 1  # Station ID ของ PLC
REGISTER_ADDRESS = 1  # D1
CSV_FILENAME = Path(__file__).resolve().parent / "plc_voltage_log.csv"

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

print("เชื่อมต่อ Serial สำเร็จ! กำลังรอข้อมูลจาก PLC... (กด Ctrl+C เพื่อหยุด)")

# 3. ลูปอ่านค่า
try:
    while True:
        try:
            result = client.read_holding_registers(
                address=REGISTER_ADDRESS, count=1, device_id=SLAVE_ID
            )

            if (
                result is not None
                and not result.isError()
                and hasattr(result, "registers")
            ):
                raw_value = result.registers[0]
                voltage = round((raw_value / 4095.0) * 10.0, 2)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with CSV_FILENAME.open(
                    mode="a", newline="", encoding="utf-8"
                ) as file:
                    writer = csv.writer(file)
                    writer.writerow([now_str, raw_value, voltage])

                print(f"[{now_str}] D1: {raw_value} | แรงดัน: {voltage} V")
            else:
                print(" บอร์ด PLC ไม่ตอบสนอง (กำลังรอสัญญาณ...)")

        except ModbusException:
            print(
                " ไม่ได้รับสัญญาณตอบกลับจาก PLC (ตรวจสอบสาย A/B หรือสถานะ RUN)"
            )

        time.sleep(1)

except KeyboardInterrupt:
    print("\n หยุดการบันทึกข้อมูลเรียบร้อย")
finally:
    client.close()
