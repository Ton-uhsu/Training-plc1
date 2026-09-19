import csv
from datetime import datetime
import time
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

# --- ตั้งค่าการเชื่อมต่อ ---
COM_PORT = "COM6"  # ตรวจสอบชื่อพอร์ตใน Device Manager
BAUDRATE = 9600  # ตรงกับ D8120
SLAVE_ID = 1  # Station ID ของ PLC
CSV_FILENAME = "plc_voltage_log.csv"

# 1. เตรียมไฟล์ CSV
with open(CSV_FILENAME, mode="a", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    if file.tell() == 0:
        writer.writerow(["Timestamp", "Raw_AD (D0)", "Voltage_V"])

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
            result = client.read_holding_registers(address=0, count=1)

            if (
                result is not None
                and not result.isError()
                and hasattr(result, "registers")
            ):
                raw_value = result.registers[0]
                voltage = round((raw_value / 4095.0) * 10.0, 2)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with open(
                    CSV_FILENAME, mode="a", newline="", encoding="utf-8"
                ) as file:
                    writer = csv.writer(file)
                    writer.writerow([now_str, raw_value, voltage])

                print(f"[{now_str}] D0: {raw_value} | แรงดัน: {voltage} V")
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