import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGE_URL = (ROOT / "index.html").as_uri()


class DashboardDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.page = cls.browser.new_page(viewport={"width": 1440, "height": 1000})
        cls.page.set_default_timeout(5000)
        cls.errors = []
        cls.page.on("console", lambda msg: cls.errors.append(msg.text) if msg.type == "error" else None)
        cls.page.goto(PAGE_URL)
        cls.page.wait_for_load_state("networkidle")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page.reload()
        self.page.wait_for_load_state("networkidle")

    def test_prioritizes_faults_and_maintenance(self):
        self.assertIn("Smart Farm", self.page.title())
        self.assertEqual(self.page.locator("[data-status='critical']").count(), 1)
        self.assertEqual(self.page.locator("[data-status='warning']").count(), 2)
        self.assertEqual(self.page.locator("[data-device-row]").count(), 8)
        self.assertTrue(self.page.get_by_text("ต้องดำเนินการ 3 รายการ", exact=True).is_visible())

    def test_filter_and_acknowledge_are_interactive(self):
        self.page.get_by_role("button", name="ดูเฉพาะผิดปกติ").click()
        self.assertEqual(self.page.locator("[data-device-row]:visible").count(), 3)

        self.page.locator("[data-alert-id='ALT-001']").get_by_role("button", name="รับทราบ").click()
        self.assertTrue(
            self.page.locator("[data-alert-id='ALT-001']").get_by_text("รับทราบแล้ว").is_visible()
        )

    def test_demo_contains_no_equipment_control(self):
        forbidden = ["เปิดปั๊ม", "ปิดปั๊ม", "เปิดวาล์ว", "ปิดวาล์ว"]
        page_text = self.page.locator("body").inner_text()
        for label in forbidden:
            self.assertNotIn(label, page_text)

    def test_has_no_console_errors(self):
        self.assertEqual(self.errors, [])

    def test_one_year_history_changes_chart_and_summary(self):
        self.page.get_by_role("button", name="ข้อมูลย้อนหลัง").click()
        self.page.get_by_role("button", name="1 ปี", exact=True).click()

        self.assertTrue(self.page.get_by_text("ย้อนหลัง 1 ปี", exact=True).is_visible())
        self.assertEqual(self.page.locator("#history-chart [data-month-point]").count(), 12)
        self.assertTrue(self.page.get_by_text("สุขภาพเฉลี่ย 92%", exact=True).is_visible())

    def test_raw_history_logs_follow_period_and_status_filter(self):
        self.page.get_by_role("button", name="ข้อมูลย้อนหลัง").click()
        self.page.get_by_role("button", name="1 ปี", exact=True).click()

        self.assertTrue(self.page.get_by_text("ข้อมูล Log ดิบ", exact=True).is_visible())
        self.assertTrue(self.page.get_by_text("ข้อมูลตัวอย่างจากย้อนหลัง 1 ปี", exact=True).is_visible())
        self.assertEqual(self.page.locator("[data-log-row]").count(), 8)
        self.assertTrue(self.page.get_by_role("columnheader", name="ค่าดิบ").is_visible())

        self.page.get_by_role("button", name="เฉพาะผิดปกติ", exact=True).click()
        self.assertEqual(self.page.locator("[data-log-row]:visible").count(), 3)

    def test_primary_machine_health_is_inspectable(self):
        self.page.get_by_role("button", name="สุขภาพเครื่องจักร").click()

        self.assertEqual(self.page.locator("[data-machine-card]").count(), 4)
        self.page.get_by_role("button", name="มอเตอร์ปั๊มสารอาหาร P-02").click()
        self.assertTrue(self.page.get_by_text("อุณหภูมิลูกปืน 71°C", exact=True).is_visible())
        self.assertTrue(self.page.get_by_text("แนะนำให้ตรวจภายใน 2 ชั่วโมง", exact=True).is_visible())

    def test_maintenance_plan_can_show_only_necessary_work(self):
        self.page.get_by_role("button", name="แผนซ่อมบำรุง").click()
        self.assertEqual(self.page.locator("[data-maintenance-item]").count(), 5)

        self.page.get_by_role("button", name="เฉพาะจำเป็น").click()
        self.assertEqual(self.page.locator("[data-maintenance-item]:visible").count(), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
