from unittest.mock import patch

import frappe

from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


class TestTaxesAndTotals(ERPNextTestSuite):
	def test_regional_round_off_accounts(self):
		"""
		Regional overrides cannot extend the list in-place — the return
		value must be assigned back to frappe.flags.round_off_applicable_accounts.
		"""
		test_account = "_Test Round Off Account"

		def mock_regional(company, account_list: list) -> list:
			# Simulates a regional override
			account_list.extend([test_account])
			return account_list

		so = make_sales_order(do_not_save=True)

		with patch(
			"erpnext.controllers.taxes_and_totals.get_regional_round_off_accounts",
			mock_regional,
		):
			calculate_taxes_and_totals(so)

		self.assertIn(test_account, frappe.flags.round_off_applicable_accounts)

	def test_disabling_rounded_total_resets_base_fields(self):
		"""Disabling rounded total should also clear base rounded values."""
		so = make_sales_order(do_not_save=True)
		so.items[0].qty = 1
		so.items[0].rate = 1000.25
		so.items[0].price_list_rate = 1000.25
		so.items[0].discount_percentage = 0
		so.items[0].discount_amount = 0
		so.set("taxes", [])

		so.disable_rounded_total = 0
		calculate_taxes_and_totals(so)

		self.assertEqual(so.grand_total, 1000.25)
		self.assertEqual(so.rounded_total, 1000.0)
		self.assertEqual(so.rounding_adjustment, -0.25)
		self.assertEqual(so.base_grand_total, 1000.25)
		self.assertEqual(so.base_rounded_total, 1000.0)
		self.assertEqual(so.base_rounding_adjustment, -0.25)

		# User toggles disable_rounded_total after values are already set.
		so.disable_rounded_total = 1

		calculate_taxes_and_totals(so)

		self.assertEqual(so.rounded_total, 0)
		self.assertEqual(so.rounding_adjustment, 0)
		self.assertEqual(so.base_rounded_total, 0)
		self.assertEqual(so.base_rounding_adjustment, 0)

	def test_calculate_margin_amount_type(self):
		"""When rate exceeds price_list_rate and no pricing rules, margin type is set to 'Amount'."""
		so = make_sales_order(do_not_save=True)
		item = so.items[0]
		item.qty = 2
		item.price_list_rate = 100.0
		item.rate = 120.0  # rate > price_list_rate -> implicit Amount margin
		item.pricing_rules = ""
		item.margin_type = None
		item.margin_rate_or_amount = 0

		calculate_taxes_and_totals(so)

		self.assertEqual(item.margin_type, "Amount")
		self.assertEqual(item.margin_rate_or_amount, 20.0)
		# The implicit-Amount branch does not populate rate_with_margin; the rate is preserved.
		self.assertEqual(item.rate, 120.0)

	def test_calculate_margin_percentage_type(self):
		"""Percentage margin should add a fraction of price_list_rate to derive rate_with_margin."""
		so = make_sales_order(do_not_save=True)
		item = so.items[0]
		item.qty = 1
		item.price_list_rate = 200.0
		item.rate = 200.0
		item.pricing_rules = ""
		item.margin_type = "Percentage"
		item.margin_rate_or_amount = 10  # 10% margin

		calculate_taxes_and_totals(so)

		# rate_with_margin = price_list_rate * (1 + margin_rate / 100)
		expected_rate_with_margin = 200.0 * 1.10
		self.assertAlmostEqual(item.rate_with_margin, expected_rate_with_margin, places=2)

	def test_filter_rows_excludes_alternative_items(self):
		"""Quotation totals must not include rows marked as is_alternative."""
		qo = make_quotation(qty=5, rate=100, do_not_save=True)
		# Append an alternative item that should be excluded from the net total
		qo.append(
			"items",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 10,
				"rate": 500,
				"is_alternative": 1,
			},
		)

		calculate_taxes_and_totals(qo)

		# Only the first (non-alternative) item should contribute: 5 x 100 = 500
		self.assertEqual(qo.net_total, 500.0)
		self.assertEqual(qo.grand_total, 500.0)

	def test_calculate_total_net_weight(self):
		"""total_net_weight must equal the sum of total_weight across all item rows."""
		so = make_sales_order(do_not_save=True)
		so.items[0].qty = 3
		so.items[0].rate = 50
		so.items[0].total_weight = 6.0  # set directly so no item master lookup needed

		calculate_taxes_and_totals(so)

		self.assertEqual(so.total_net_weight, 6.0)

	def test_set_discount_amount_exceeds_grand_total_throws(self):
		"""Discount amount larger than grand total must raise a ValidationError."""
		so = make_sales_order(do_not_save=True)
		so.items[0].qty = 1
		so.items[0].rate = 100
		so.apply_discount_on = "Grand Total"
		so.discount_amount = 200  # more than the 100 grand total
		# _action must be set to trigger the validation path
		so._action = "save"

		self.assertRaises(frappe.ValidationError, calculate_taxes_and_totals, so)
