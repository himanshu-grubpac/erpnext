import frappe

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.transaction_base import validate_uom_is_integer


class TestUtils(ERPNextTestSuite):
	def test_reset_default_field_value(self):
		doc = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"set_warehouse": "Warehouse 1",
			}
		)

		# Same values
		doc.items = [
			{"warehouse": "Warehouse 1"},
			{"warehouse": "Warehouse 1"},
			{"warehouse": "Warehouse 1"},
		]
		doc.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.assertEqual(doc.set_warehouse, "Warehouse 1")

		# Mixed values
		doc.items = [
			{"warehouse": "Warehouse 1"},
			{"warehouse": "Warehouse 2"},
			{"warehouse": "Warehouse 1"},
		]
		doc.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.assertEqual(doc.set_warehouse, None)

	def test_reset_default_field_value_in_mfg_stock_entry(self):
		# manufacture stock entry with rows having blank source/target wh
		se = frappe.get_doc(
			doctype="Stock Entry",
			purpose="Manufacture",
			stock_entry_type="Manufacture",
			company="_Test Company",
			from_warehouse="_Test Warehouse - _TC",
			to_warehouse="_Test Warehouse 1 - _TC",
			items=[
				frappe._dict(
					item_code="_Test Item", qty=1, basic_rate=200, s_warehouse="_Test Warehouse - _TC"
				),
				frappe._dict(
					item_code="_Test FG Item",
					qty=4,
					t_warehouse="_Test Warehouse 1 - _TC",
					is_finished_item=1,
				),
			],
		)
		se.save()

		# default fields must be untouched
		self.assertEqual(se.from_warehouse, "_Test Warehouse - _TC")
		self.assertEqual(se.to_warehouse, "_Test Warehouse 1 - _TC")

		se.delete()

	def test_reset_default_field_value_in_transfer_stock_entry(self):
		doc = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"purpose": "Material Receipt",
				"from_warehouse": "Warehouse 1",
				"to_warehouse": "Warehouse 2",
			}
		)

		# Same values
		doc.items = [
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
		]

		doc.reset_default_field_value("from_warehouse", "items", "s_warehouse")
		doc.reset_default_field_value("to_warehouse", "items", "t_warehouse")
		self.assertEqual(doc.from_warehouse, "Warehouse 1")
		self.assertEqual(doc.to_warehouse, "Warehouse 2")

		# Mixed values in source wh
		doc.items = [
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
			{"s_warehouse": "Warehouse 3", "t_warehouse": "Warehouse 2"},
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
		]

		doc.reset_default_field_value("from_warehouse", "items", "s_warehouse")
		doc.reset_default_field_value("to_warehouse", "items", "t_warehouse")
		self.assertEqual(doc.from_warehouse, None)
		self.assertEqual(doc.to_warehouse, "Warehouse 2")

	def test_validate_posting_time_invalid(self):
		"""An invalid posting_time string must raise a ValidationError."""
		doc = frappe.get_doc({"doctype": "Stock Entry"})
		doc.set_posting_time = 1
		doc.posting_time = "not-a-time"

		self.assertRaises(frappe.ValidationError, doc.validate_posting_time)

	def test_validate_posting_time_auto_set(self):
		"""When set_posting_time is falsy, posting_date and posting_time are replaced with now."""
		from frappe.utils import getdate, nowdate

		doc = frappe.get_doc({"doctype": "Stock Entry"})
		doc.set_posting_time = 0
		doc.posting_date = "2000-01-01"
		doc.posting_time = "00:00:00"

		doc.validate_posting_time()

		# Both fields must have been refreshed to the current date/time
		self.assertEqual(doc.posting_date, nowdate())
		# posting_time should look like HH:MM:SS (not the old midnight value)
		self.assertNotEqual(doc.posting_time, "00:00:00")

	def test_validate_uom_is_integer_raises_for_fraction(self):
		"""Fractional qty in a whole-number UOM must raise UOMMustBeIntegerError."""
		from erpnext.utilities.transaction_base import UOMMustBeIntegerError

		# Nos is seeded as a whole-number UOM in test fixtures
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"purpose": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "_Test Item",
						"uom": "Nos",
						"qty": 1.5,
						"t_warehouse": "_Test Warehouse - _TC",
						"basic_rate": 100,
					}
				],
			}
		)

		self.assertRaises(UOMMustBeIntegerError, validate_uom_is_integer, se, "uom", "qty")

	def test_validate_uom_is_integer_passes_for_whole_number(self):
		"""Integer qty in a whole-number UOM must NOT raise any error."""
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"purpose": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "_Test Item",
						"uom": "Nos",
						"qty": 3,
						"t_warehouse": "_Test Warehouse - _TC",
						"basic_rate": 100,
					}
				],
			}
		)

		# Should complete without raising
		validate_uom_is_integer(se, "uom", "qty")
