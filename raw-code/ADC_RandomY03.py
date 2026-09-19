from collections import deque
import csv
from datetime import datetime
from pathlib import Path
import time
import pandas as pd
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from sklearn.ensemble import RandomForestRegressor

# --- 1. ตั้งค่าการเชื่อมต่อ PLC ---
COM_PORT = "COM6"  # ตรวจสอบพอร์ต USB-RS485
BAUDRATE = 9600
SLAVE_ID = 1
REGISTER_ADDRESS = 1  # D1
CSV_FILENAME = Path(__file__).resolve().parent / "plc_voltage_log.csv"
M100_COIL_ADDR = 100  # Address ของ M100 เพื่อสั่งขับ Y3
DROP_THRESHOLD = 0.15  # เกณฑ์ตัดสินแนวโน้มลดลง (เช่น ลดลงเกิน 0.15 V)

# --- 2. เทรนโมเดล Random Forest จากไฟล์ CSV เดิม ---
print(" กำลังเทรนโมเดล Random Forest จาก plc_voltage_log.csv ...")
try:
    df = pd.read_csv(CSV_FILENAME)
    df["Lag_1"] = df["Voltage_V"].shift(1)
    df["Lag_2"] = df["Voltage_V"].shift(2)
    df["Lag_3"] = df["Voltage_V"].shift(3)
    df_clean = df.dropna().reset_index(drop=True)

    X = df_clean[["Lag_1", "Lag_2", "Lag_3"]]
    y = df_clean["Voltage_V"]

    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X, y)
    print("เทรนโมเดลสำเร็จ พร้อมใช้งาน!")
except Exception as e:
    print(f" เกิดข้อผิดพลาดในการโหลด/เทรนข้อมูล: {e}")
    exit()

# --- 3. เชื่อมต่อ Modbus Serial ---
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

# ตัวแปรเก็บค่าแรงดันย้อนหลัง 3 จุด (Lag_3, Lag_2, Lag_1)
voltage_history = deque(maxlen=3)

print("\n เริ่มต้นระบบ AI ทำนายแนวโน้มและสั่งงาน PLC (กด Ctrl+C เพื่อหยุด)")
print("=" * 65)

try:
    while True:
        try:
            # อ่านค่าดิบจาก D1 (Address 1)
            result = client.read_holding_registers(
                address=REGISTER_ADDRESS, count=1, device_id=SLAVE_ID
            )

            if (
                result is not None
                and not result.isError()
                and hasattr(result, "registers")
            ):
                raw_value = result.registers[0]
                current_v = round((raw_value / 4095.0) * 10.0, 2)
                now_str = datetime.now().strftime("%H:%M:%S")

                with CSV_FILENAME.open(
                    mode="a", newline="", encoding="utf-8"
                ) as file:
                    csv.writer(file).writerow(
                        [
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            raw_value,
                            current_v,
                        ]
                    )

                voltage_history.append(current_v)

                # เมื่อมีข้อมูลสะสมครบ 3 จุดขึ้นไป จึงเริ่มทำนาย
                if len(voltage_history) == 3:
                    # เตรียมข้อมูล Features: [Lag_1 (ล่าสุด), Lag_2, Lag_3]
                    features = pd.DataFrame(
                        [
                            [
                                voltage_history[2],
                                voltage_history[1],
                                voltage_history[0],
                            ]
                        ],
                        columns=["Lag_1", "Lag_2", "Lag_3"],
                    )

                    # ทำนายแรงดันในอนาคต (t+1)
                    pred_v = round(rf_model.predict(features)[0], 2)
                    diff = pred_v - current_v

                    # ตรวจสอบแนวโน้ม
                    if diff < -DROP_THRESHOLD:
                        trend_status = " แนวโน้มลดลง"
                        y3_state = True  # สั่ง M100 = 1 -> Y3 ติด
                    else:
                        trend_status = "⏸ แนวโน้มคงที่/เพิ่มขึ้น"
                        y3_state = False  # สั่ง M100 = 0 -> Y3 ดับ

                    # ส่งคำสั่งไปยัง PLC (Write Coil M100)
                    try:
                        client.write_coil(
                            address=M100_COIL_ADDR,
                            value=y3_state,
                            slave=SLAVE_ID,
                        )
                    except TypeError:
                        client.write_coil(
                            address=M100_COIL_ADDR, value=y3_state
                        )

                    y3_text = " ON" if y3_state else " OFF"
                    print(
                        f"[{now_str}] ค่าจริง: {current_v:4.2f}V | ทำนาย: {pred_v:4.2f}V | {trend_status} | สั่ง Y3: {y3_text}"
                    )
                else:
                    print(
                        f"[{now_str}] กำลังสะสมข้อมูลเริ่มต้น... ({len(voltage_history)}/3) ค่าปัจจุบัน: {current_v:.2f}V"
                    )

        except ModbusException:
            print(" ขาดการติดต่อกับ PLC...")

        time.sleep(1)  # ทำงานทุก 1 วินาที

except KeyboardInterrupt:
    print("\n สั่งปิดระบบ และดับ Y3...")
    # สั่งดับ Y3 ก่อนปิดโปรแกรม
    try:
        client.write_coil(address=M100_COIL_ADDR, value=False, slave=SLAVE_ID)
    except Exception:
        pass
finally:
    client.close()
