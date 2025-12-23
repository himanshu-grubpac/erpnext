# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import getdate

from erpnext import allow_regional
from erpnext.controllers.accounts_controller import validate_account_head


class TaxWithholdingCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.tax_withholding_account.tax_withholding_account import (
			TaxWithholdingAccount,
		)
		from erpnext.accounts.doctype.tax_withholding_rate.tax_withholding_rate import TaxWithholdingRate

		accounts: DF.Table[TaxWithholdingAccount]
		category_name: DF.Data | None
		disable_cumulative_threshold: DF.Check
		disable_transaction_threshold: DF.Check
		rates: DF.Table[TaxWithholdingRate]
		round_off_tax_amount: DF.Check
		tax_deduction_basis: DF.Literal["", "Gross Total", "Net Total"]
		tax_on_excess_amount: DF.Check
	# end: auto-generated types

	def validate(self):
		# TODO: Disable single threshold if tax on excess is enabled
		self.validate_dates()
		self.validate_companies_and_accounts()
		self.validate_thresholds()

	def validate_dates(self):
		group_rates = defaultdict(list)
		for d in self.get("rates"):
			if getdate(d.from_date) >= getdate(d.to_date):
				frappe.throw(_("Row #{0}: From Date cannot be before To Date").format(d.idx))
			group_rates[d.tax_withholding_group].append(d)

		# Validate overlapping dates within each group
		for group, rates in group_rates.items():
			rates = sorted(rates, key=lambda d: getdate(d.from_date))
			last_to_date = None

			for d in rates:
				if last_to_date and getdate(d.from_date) < getdate(last_to_date):
					frappe.throw(
						_("Row #{0}: Dates overlapping with other row in group {1}").format(
							d.idx, group or "Default"
						)
					)

				last_to_date = d.to_date

	def validate_companies_and_accounts(self):
		existing_accounts = set()
		companies = set()
		for d in self.get("accounts"):
			# validate duplicate company
			if d.get("company") in companies:
				frappe.throw(_("Company {0} added multiple times").format(frappe.bold(d.get("company"))))
			companies.add(d.get("company"))

			# validate duplicate account
			if d.get("account") in existing_accounts:
				frappe.throw(_("Account {0} added multiple times").format(frappe.bold(d.get("account"))))

			validate_account_head(d.idx, d.get("account"), d.get("company"))
			existing_accounts.add(d.get("account"))

	def validate_thresholds(self):
		for d in self.get("rates"):
			if d.cumulative_threshold and d.single_threshold and d.cumulative_threshold < d.single_threshold:
				frappe.throw(
					_(
						"Row #{0}: Cumulative threshold cannot be less than Single Transaction threshold"
					).format(d.idx)
				)

	def get_applicable_tax_row(self, posting_date, tax_withholding_group):
		for row in self.rates:
			if (
				getdate(row.from_date) <= getdate(posting_date) <= getdate(row.to_date)
				and row.tax_withholding_group == tax_withholding_group
			):
				return row

		frappe.throw(_("No Tax Withholding data found for the current posting date."))

<<<<<<< HEAD
	if inv.doctype == "Sales Invoice":
		party_type = "Customer"
		party = inv.customer
	else:
		party_type = "Supplier"
		party = inv.supplier
=======
	def get_company_account(self, company):
		for row in self.accounts:
			if company == row.company:
				return row.account
>>>>>>> c66f78c784 (feat: Introduce tax withholding entry)

		frappe.throw(
<<<<<<< HEAD
			_(
				"Tax Withholding Category {} against Company {} for Customer {} should have Cumulative Threshold value."
			).format(tax_withholding_category, inv.company, party)
		)

	tax_amount, tax_deducted, tax_deducted_on_advances, voucher_wise_amount = get_tax_amount(
		party_type, parties, inv, tax_details, posting_date, pan_no
	)

	if party_type == "Supplier":
		tax_row = get_tax_row_for_tds(tax_details, tax_amount)
	else:
		tax_row = get_tax_row_for_tcs(inv, tax_details, tax_amount, tax_deducted)

	cost_center = get_cost_center(inv)
	tax_row.update(
		{
			"cost_center": cost_center,
			"is_tax_withholding_account": 1,
		}
	)

	if cint(tax_details.round_off_tax_amount):
		inv.round_off_applicable_accounts_for_tax_withholding = tax_details.account_head

	if inv.doctype == "Purchase Invoice":
		return tax_row, tax_deducted_on_advances, voucher_wise_amount
	else:
		return tax_row


def get_cost_center(inv):
	cost_center = frappe.get_cached_value("Company", inv.company, "cost_center")

	if len(inv.get("taxes", [])) > 0:
		cost_center = inv.get("taxes")[0].cost_center

	return cost_center


def get_tax_withholding_details(tax_withholding_category, posting_date, company):
	tax_withholding = frappe.get_doc("Tax Withholding Category", tax_withholding_category)

	tax_rate_detail = get_tax_withholding_rates(tax_withholding, posting_date)

	for account_detail in tax_withholding.accounts:
		if company == account_detail.company:
			return frappe._dict(
				{
					"tax_withholding_category": tax_withholding_category,
					"account_head": account_detail.account,
					"rate": tax_rate_detail.tax_withholding_rate,
					"from_date": tax_rate_detail.from_date,
					"to_date": tax_rate_detail.to_date,
					"threshold": tax_rate_detail.single_threshold,
					"cumulative_threshold": tax_rate_detail.cumulative_threshold,
					"description": tax_withholding.category_name
					if tax_withholding.category_name
					else tax_withholding_category,
					"consider_party_ledger_amount": tax_withholding.consider_party_ledger_amount,
					"tax_on_excess_amount": tax_withholding.tax_on_excess_amount,
					"round_off_tax_amount": tax_withholding.round_off_tax_amount,
				}
			)


def get_tax_withholding_rates(tax_withholding, posting_date):
	# returns the row that matches with the fiscal year from posting date
	for rate in tax_withholding.rates:
		if getdate(rate.from_date) <= getdate(posting_date) <= getdate(rate.to_date):
			return rate

	frappe.throw(_("No Tax Withholding data found for the current posting date."))


def get_tax_row_for_tcs(inv, tax_details, tax_amount, tax_deducted):
	row = {
		"category": "Total",
		"charge_type": "Actual",
		"tax_amount": tax_amount,
		"description": tax_details.description,
		"account_head": tax_details.account_head,
	}

	if tax_deducted:
		# TCS already deducted on previous invoices
		# So, TCS will be calculated by 'Previous Row Total'

		taxes_excluding_tcs = [d for d in inv.taxes if d.account_head != tax_details.account_head]
		if taxes_excluding_tcs:
			# chargeable amount is the total amount after other charges are applied
			row.update(
				{
					"charge_type": "On Previous Row Total",
					"row_id": len(taxes_excluding_tcs),
					"rate": tax_details.rate,
				}
			)
		else:
			# if only TCS is to be charged, then net total is chargeable amount
			row.update({"charge_type": "On Net Total", "rate": tax_details.rate})

	return row


def get_tax_row_for_tds(tax_details, tax_amount):
	return {
		"category": "Total",
		"charge_type": "Actual",
		"tax_amount": tax_amount,
		"add_deduct_tax": "Deduct",
		"description": tax_details.description,
		"account_head": tax_details.account_head,
	}


def get_lower_deduction_certificate(company, posting_date, tax_details, pan_no):
	ldc_name = frappe.db.get_value(
		"Lower Deduction Certificate",
		{
			"pan_no": pan_no,
			"tax_withholding_category": tax_details.tax_withholding_category,
			"valid_from": ("<=", posting_date),
			"valid_upto": (">=", posting_date),
			"company": company,
		},
		"name",
	)

	if ldc_name:
		return frappe.get_doc("Lower Deduction Certificate", ldc_name)


def get_tax_amount(party_type, parties, inv, tax_details, posting_date, pan_no=None):
	vouchers, voucher_wise_amount = get_invoice_vouchers(
		parties,
		tax_details,
		inv.company,
		party_type=party_type,
	)

	payment_entry_vouchers = get_payment_entry_vouchers(
		parties, tax_details, inv.company, party_type=party_type
	)

	advance_vouchers = get_advance_vouchers(
		parties,
		company=inv.company,
		from_date=tax_details.from_date,
		to_date=tax_details.to_date,
		party_type=party_type,
	)

	taxable_vouchers = vouchers + advance_vouchers + payment_entry_vouchers
	tax_deducted_on_advances = 0

	if inv.doctype == "Purchase Invoice":
		tax_deducted_on_advances = get_taxes_deducted_on_advances_allocated(inv, tax_details)

	tax_deducted = 0
	if taxable_vouchers:
		tax_deducted = get_deducted_tax(taxable_vouchers, tax_details)

	# If advance is outside the current tax withholding period (usually a fiscal year), `get_deducted_tax` won't fetch it.
	# updating `tax_deducted` with correct advance tax value (from current and previous previous withholding periods), will allow the
	# rest of the below logic to function properly
	# ---FY 2023-------------||---------------------FY 2024-----------------------||--
	# ---Advance-------------||---------Inv_1--------Inv_2------------------------||--
	if tax_deducted_on_advances:
		tax_deducted += get_advance_tax_across_fiscal_year(tax_deducted_on_advances, tax_details)

	tax_amount = 0

	if party_type == "Supplier":
		# if tds account is changed.
		if not tax_deducted:
			tax_deducted = is_tax_deducted_on_the_basis_of_inv(vouchers)

		ldc = get_lower_deduction_certificate(inv.company, posting_date, tax_details, pan_no)
		if tax_deducted:
			net_total = inv.tax_withholding_net_total
			if ldc:
				limit_consumed = get_limit_consumed(ldc, parties)
				if is_valid_certificate(ldc, posting_date, limit_consumed):
					tax_amount = get_lower_deduction_amount(
						net_total, limit_consumed, ldc.certificate_limit, ldc.rate, tax_details
					)
				else:
					tax_amount = net_total * tax_details.rate / 100
			else:
				tax_amount = net_total * tax_details.rate / 100

			# once tds is deducted, not need to add vouchers in the invoice
			voucher_wise_amount = {}
		else:
			tax_amount = get_tds_amount(ldc, parties, inv, tax_details, voucher_wise_amount)

	elif party_type == "Customer":
		if tax_deducted:
			# if already TCS is charged, then amount will be calculated based on 'Previous Row Total'
			tax_amount = 0
		else:
			#  if no TCS has been charged in FY,
			# then chargeable value is "prev invoices + advances - advance_adjusted" value which cross the threshold
			tax_amount = get_tcs_amount(parties, inv, tax_details, vouchers, advance_vouchers)

	if cint(tax_details.round_off_tax_amount):
		tax_amount = normal_round(tax_amount)

	return tax_amount, tax_deducted, tax_deducted_on_advances, voucher_wise_amount


def is_tax_deducted_on_the_basis_of_inv(vouchers):
	return frappe.db.exists(
		"Purchase Taxes and Charges",
		{
			"parent": ["in", vouchers],
			"is_tax_withholding_account": 1,
			"parenttype": "Purchase Invoice",
			"base_tax_amount_after_discount_amount": [">", 0],
		},
	)


def get_invoice_vouchers(parties, tax_details, company, party_type="Supplier"):
	voucher_wise_amount = []
	vouchers = []

	ldcs = frappe.db.get_all(
		"Lower Deduction Certificate",
		filters={
			"valid_from": [">=", tax_details.from_date],
			"valid_upto": ["<=", tax_details.to_date],
			"company": company,
			"supplier": ["in", parties],
		},
		fields=["supplier", "valid_from", "valid_upto", "rate"],
	)

	doctype = "Purchase Invoice" if party_type == "Supplier" else "Sales Invoice"
	field = [
		"base_tax_withholding_net_total as base_net_total" if party_type == "Supplier" else "base_net_total",
		"name",
		"grand_total",
		"posting_date",
	]

	filters = {
		"company": company,
		frappe.scrub(party_type): ["in", parties],
		"posting_date": ["between", (tax_details.from_date, tax_details.to_date)],
		"is_opening": "No",
		"docstatus": 1,
	}

	if doctype != "Sales Invoice":
		filters.update(
			{"apply_tds": 1, "tax_withholding_category": tax_details.get("tax_withholding_category")}
=======
			_("No Tax withholding account set for Company {0} in Tax Withholding Category {1}.").format(
				frappe.bold(company), frappe.bold(self.name)
			)
>>>>>>> c66f78c784 (feat: Introduce tax withholding entry)
		)


class TaxWithholdingDetails:
	def __init__(
		self,
		tax_withholding_categories: list[str],
		tax_withholding_group: str,
		posting_date: str,
		party_type: str,
		party: str,
		company: str,
	):
		self.tax_withholding_categories = tax_withholding_categories
		self.tax_withholding_group = tax_withholding_group
		self.posting_date = posting_date
		self.party_type = party_type
		self.party = party
		self.company = company

	def get(self) -> list:
		"""
		Fetches tax withholding categories based on the provided parameters.
		"""
		category_details = frappe._dict()
		if not self.tax_withholding_categories:
			return category_details

		ldc_details = self.get_ldc_details()

		for category_name in self.tax_withholding_categories:
			doc: TaxWithholdingCategory = frappe.get_cached_doc("Tax Withholding Category", category_name)
			row = doc.get_applicable_tax_row(self.posting_date, self.tax_withholding_group)
			account_head = doc.get_company_account(self.company)

			category_detail = frappe._dict(
				name=category_name,
				description=doc.category_name,
				account_head=account_head,
				# rates
				tax_rate=row.tax_withholding_rate,
				from_date=row.from_date,
				to_date=row.to_date,
				single_threshold=row.single_threshold,
				cumulative_threshold=row.cumulative_threshold,
				# settings
				tax_deduction_basis=doc.tax_deduction_basis,
				round_off_tax_amount=doc.round_off_tax_amount,
				tax_on_excess_amount=doc.tax_on_excess_amount,
				disable_cumulative_threshold=doc.disable_cumulative_threshold,
				disable_transaction_threshold=doc.disable_transaction_threshold,
				taxable_amount=0,
			)

			# ldc (only if valid based on posting date)
			if ldc_detail := ldc_details.get(category_name):
				category_detail.update(ldc_detail)

			category_details[category_name] = category_detail

		return category_details

	def get_ldc_details(self):
		"""
		Fetches the Lower Deduction Certificate (LDC) details for the given party.
		Assumes that only one LDC per category can be valid at a time.
		"""
		ldc_details = {}

		if self.party_type != "Supplier":
			return ldc_details

		# NOTE: This can be a configurable option
		# To check if filter by tax_id is needed
		tax_id = get_tax_id_for_party(self.party_type, self.party)

		# ldc details
		ldc_records = self.get_valid_ldc_records(tax_id)
		if not ldc_records:
			return ldc_details

		ldc_names = [ldc.name for ldc in ldc_records]
		ldc_utilization_map = self.get_ldc_utilization_by_category(ldc_names, tax_id)

		# map
		for ldc in ldc_records:
			category_name = ldc.tax_withholding_category

			unutilized_amount = ldc.certificate_limit - (ldc_utilization_map.get(ldc.name) or 0)
			if not unutilized_amount:
				continue

			ldc_details[category_name] = dict(
				ldc_certificate=ldc.name,
				ldc_unutilized_amount=unutilized_amount,
				ldc_rate=ldc.rate,
			)

		return ldc_details

	def get_valid_ldc_records(self, tax_id):
		ldc = frappe.qb.DocType("Lower Deduction Certificate")
		query = (
			frappe.qb.from_(ldc)
			.select(
				ldc.name,
				ldc.tax_withholding_category,
				ldc.rate,
				ldc.certificate_limit,
			)
			.where(
				(ldc.valid_from <= self.posting_date)
				& (ldc.valid_upto >= self.posting_date)
				& (ldc.company == self.company)
				& ldc.tax_withholding_category.isin(self.tax_withholding_categories)
			)
		)

		query = query.where(ldc.pan_no == tax_id) if tax_id else query.where(ldc.supplier == self.party)

		return query.run(as_dict=True)

	def get_ldc_utilization_by_category(self, ldc_names, tax_id):
		twe = frappe.qb.DocType("Tax Withholding Entry")
		query = (
			frappe.qb.from_(twe)
			.select(twe.lower_deduction_certificate, Sum(twe.taxable_amount).as_("limit_consumed"))
			.where(
				(twe.company == self.company)
				& (twe.party_type == self.party_type)
				& (twe.tax_withholding_category.isin(self.tax_withholding_categories))
				& (twe.lower_deduction_certificate.isin(ldc_names))
				& (twe.docstatus == 1)
				& (twe.status.isin(["Settled", "Over Withheld"]))
			)
			.groupby(twe.lower_deduction_certificate)
		)

		query = query.where(twe.tax_id == tax_id) if tax_id else query.where(twe.party == self.party)

		return frappe._dict(query.run())


<<<<<<< HEAD
def get_tcs_amount(parties, inv, tax_details, vouchers, adv_vouchers):
	tcs_amount = 0
	ple = qb.DocType("Payment Ledger Entry")

	# sum of debit entries made from sales invoices
	invoiced_amt = (
		frappe.db.get_value(
			"GL Entry",
			{
				"is_cancelled": 0,
				"party_type": "Customer",
				"party": ["in", parties],
				"company": inv.company,
				"voucher_no": ["in", vouchers],
			},
			[{"SUM": "debit"}],
		)
		or 0.0
	)

	# sum of credit entries made from PE / JV with unset 'against voucher'

	conditions = []
	conditions.append(ple.amount.lt(0))
	conditions.append(ple.delinked == 0)
	conditions.append(ple.party_type == "Customer")
	conditions.append(ple.party.isin(parties))
	conditions.append(ple.voucher_no == ple.against_voucher_no)
	conditions.append(ple.company == inv.company)
	conditions.append(ple.posting_date[tax_details.from_date : tax_details.to_date])

	advance_amt = (
		qb.from_(ple).select(Abs(Sum(ple.amount))).where(Criterion.all(conditions)).run()[0][0] or 0.0
	)

	# sum of credit entries made from sales invoice
	credit_note_amt = sum(
		frappe.db.get_all(
			"GL Entry",
			{
				"is_cancelled": 0,
				"credit": [">", 0],
				"party_type": "Customer",
				"party": ["in", parties],
				"posting_date": ["between", (tax_details.from_date, tax_details.to_date)],
				"company": inv.company,
				"voucher_type": "Sales Invoice",
			},
			pluck="credit",
		)
	)

	cumulative_threshold = tax_details.get("cumulative_threshold", 0)
	advance_adjusted = get_advance_adjusted_in_invoice(inv)

	current_invoice_total = get_invoice_total_without_tcs(inv, tax_details)
	total_invoiced_amt = (
		current_invoice_total + invoiced_amt + advance_amt - credit_note_amt - advance_adjusted
	)

	if cumulative_threshold and total_invoiced_amt >= cumulative_threshold:
		chargeable_amt = total_invoiced_amt - cumulative_threshold
		tcs_amount = chargeable_amt * tax_details.rate / 100 if chargeable_amt > 0 else 0

	return tcs_amount


def get_advance_adjusted_in_invoice(inv):
	advances_adjusted = 0
	for row in inv.get("advances", []):
		advances_adjusted += row.allocated_amount

	return advances_adjusted


def get_invoice_total_without_tcs(inv, tax_details):
	tcs_tax_row = [d for d in inv.taxes if d.account_head == tax_details.account_head]
	tcs_tax_row_amount = tcs_tax_row[0].base_tax_amount if tcs_tax_row else 0

	return inv.grand_total - tcs_tax_row_amount


def get_limit_consumed(ldc, parties):
	limit_consumed = frappe.db.get_value(
		"Purchase Invoice",
		{
			"supplier": ("in", parties),
			"apply_tds": 1,
			"docstatus": 1,
			"tax_withholding_category": ldc.tax_withholding_category,
			"posting_date": ("between", (ldc.valid_from, ldc.valid_upto)),
			"company": ldc.company,
		},
		[{"SUM": "tax_withholding_net_total"}],
	)

	return limit_consumed


def get_lower_deduction_amount(current_amount, limit_consumed, certificate_limit, rate, tax_details):
	if certificate_limit - flt(limit_consumed) - flt(current_amount) >= 0:
		return current_amount * rate / 100
	else:
		ltds_amount = certificate_limit - flt(limit_consumed)
		tds_amount = current_amount - ltds_amount

		return ltds_amount * rate / 100 + tds_amount * tax_details.rate / 100


def is_valid_certificate(ldc, posting_date, limit_consumed):
	available_amount = flt(ldc.certificate_limit) - flt(limit_consumed)
	if (getdate(ldc.valid_from) <= getdate(posting_date) <= getdate(ldc.valid_upto)) and available_amount > 0:
		return True

	return False


def normal_round(number):
	"""
	Rounds a number to the nearest integer.
	:param number: The number to round.
	"""
	decimal_part = number - int(number)

	if decimal_part >= 0.5:
		decimal_part = 1
	else:
		decimal_part = 0

	number = int(number) + decimal_part

	return number
=======
@allow_regional
def get_tax_id_for_party(party_type, party):
	return None
>>>>>>> c66f78c784 (feat: Introduce tax withholding entry)
