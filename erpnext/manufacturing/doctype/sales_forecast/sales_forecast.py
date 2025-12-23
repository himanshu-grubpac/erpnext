# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict
from datetime import datetime, date as date_type

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import DateFormat, Sum, YearWeek
from frappe.utils import add_to_date, cint, date_diff, flt
from frappe.utils.nestedset import get_descendants_of


class SalesForecast(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.sales_forecast_item.sales_forecast_item import SalesForecastItem

		amended_from: DF.Link | None
		company: DF.Link
		demand_number: DF.Int
		forecasting_method: DF.Literal["Holt-Winters", "Manual"]
		frequency: DF.Literal["Weekly", "Monthly"]
		from_date: DF.Date
		items: DF.Table[SalesForecastItem]
		naming_series: DF.Literal["SF.YY.-.######"]
		parent_warehouse: DF.Link
		posting_date: DF.Date | None
		selected_items: DF.TableMultiSelect[SalesForecastItem]
		status: DF.Literal["Planned", "MPS Generated"]
	# end: auto-generated types

	def validate(self):
		self.validate_demand_qty()

	def validate_demand_qty(self):
		if self.forecasting_method == "Manual":
			return

		for row in self.items:
			demand_qty = row.forecast_qty + flt(row.adjust_qty)
			if row.demand_qty != demand_qty:
				row.demand_qty = demand_qty

	def get_sales_data(self):
		to_date = self.from_date
		from_date = add_to_date(to_date, years=-3)

		doctype = frappe.qb.DocType("Sales Order")
		child_doctype = frappe.qb.DocType("Sales Order Item")

		query = (
			frappe.qb.from_(doctype)
			.inner_join(child_doctype)
			.on(child_doctype.parent == doctype.name)
			.select(child_doctype.item_code, Sum(child_doctype.qty).as_("qty"), doctype.transaction_date)
			.where((doctype.docstatus == 1) & (doctype.transaction_date.between(from_date, to_date)))
			.groupby(child_doctype.item_code)
		)

		if self.selected_items:
			items = [item.item_code for item in self.selected_items]
			query = query.where(child_doctype.item_code.isin(items))

		if self.parent_warehouse:
			warehouses = get_descendants_of("Warehouse", self.parent_warehouse)
			query = query.where(child_doctype.warehouse.isin(warehouses))

		query = query.groupby(doctype.transaction_date)

		return query.run(as_dict=True)

	def generate_manual_demand(self):
		forecast_demand = []
		for row in self.selected_items:
			item_details = frappe.db.get_value(
				"Item", row.item_code, ["item_name", "stock_uom as uom"], as_dict=True
			)

			for index in range(self.demand_number):
				if self.frequency == "Monthly":
					delivery_date = add_to_date(self.from_date, months=index + 1)
				else:
					delivery_date = add_to_date(self.from_date, weeks=index + 1)

				forecast_demand.append(
					{
						"item_code": row.item_code,
						"delivery_date": delivery_date,
						"item_name": item_details.item_name,
						"uom": item_details.uom,
						"demand_qty": 1.0,
					}
				)

		for demand in forecast_demand:
			self.append("items", demand)

	@frappe.whitelist()
	def generate_demand(self):
		from statsmodels.tsa.holtwinters import ExponentialSmoothing

		self.set("items", [])

		if self.forecasting_method == "Manual":
			self.generate_manual_demand()
			return

		sales_data = self.get_sales_data()
		if not sales_data:
			frappe.throw(_("No sales data found for the selected items."))

		itemwise_data = self.group_sales_data_by_item(sales_data)

		for item_code, data in itemwise_data.items():
			seasonal_periods = self.get_seasonal_periods(data)

			# Resample sales data by month or week and sum quantities
			resampled_data = self.resample_sales_data(data.date, data.qty, self.frequency)

			model = ExponentialSmoothing(
				resampled_data, trend="add", seasonal="add", seasonal_periods=seasonal_periods
			)

			fit = model.fit()
			forecast = fit.forecast(self.demand_number)

			forecast_data = forecast.to_dict()
			if forecast_data:
				self.add_sales_forecast_item(item_code, forecast_data)

	def add_sales_forecast_item(self, item_code, forecast_data):
		item_details = frappe.db.get_value(
			"Item", item_code, ["item_name", "stock_uom as uom", "name as item_code"], as_dict=True
		)

		uom_whole_number = frappe.get_cached_value("UOM", item_details.uom, "must_be_whole_number")

		for date, qty in forecast_data.items():
			if uom_whole_number:
				qty = round(qty)

			item_details.update(
				{
					"delivery_date": date,
					"forecast_qty": qty,
					"demand_qty": qty,
					"warehouse": self.parent_warehouse,
				}
			)

			self.append("items", item_details)

	def resample_sales_data(self, dates, quantities, frequency):
		"""
		Resample sales data by month or week and sum quantities.
		This replaces pandas DataFrame resample functionality.
		
		Args:
			dates: List of datetime objects
			quantities: List of quantities corresponding to dates
			frequency: "Monthly" or "Weekly"
		
		Returns:
			List of summed quantities per period
		"""
		# Group quantities by period (year-month or year-week)
		period_qty = defaultdict(float)
		
		for date, qty in zip(dates, quantities):
			if frequency == "Monthly":
				# Group by year-month
				period_key = (date.year, date.month)
			else:
				# Group by year-week (ISO week)
				# isocalendar() returns (year, week, weekday)
				period_key = date.isocalendar()[:2]
			
			period_qty[period_key] += qty
		
		# Sort by period and return values as a list
		sorted_periods = sorted(period_qty.items())
		return [qty for period, qty in sorted_periods]

	def get_seasonal_periods(self, data):
		days = date_diff(data["end_date"], data["start_date"])
		if self.frequency == "Monthly":
			months = (days / 365) * 12
			seasonal_periods = cint(months / 2)
			if seasonal_periods > 12:
				seasonal_periods = 12
		else:
			weeks = days / 7
			seasonal_periods = cint(weeks / 2)
			if seasonal_periods > 52:
				seasonal_periods = 52

		return seasonal_periods

	def group_sales_data_by_item(self, sales_data):
		"""
		Group sales data by item code and calculate total quantity sold.
		"""
		itemwise_data = frappe._dict({})
		for row in sales_data:
			if row.item_code not in itemwise_data:
				itemwise_data[row.item_code] = frappe._dict(
					{
						"start_date": row.transaction_date,
						"item": [],
						"date": [],
						"qty": [],
						"end_date": "",
					}
				)

			item_data = itemwise_data[row.item_code]
			item_data["item"].append(row.item_code)
			# Convert date to datetime object for consistency
			if isinstance(row.transaction_date, str):
				date_obj = datetime.strptime(row.transaction_date, "%Y-%m-%d")
			elif isinstance(row.transaction_date, datetime):
				date_obj = row.transaction_date
			elif isinstance(row.transaction_date, date_type):
				# Handle date objects by converting to datetime
				date_obj = datetime.combine(row.transaction_date, datetime.min.time())
			else:
				date_obj = row.transaction_date
			item_data["date"].append(date_obj)
			item_data["qty"].append(row.qty)
			item_data["end_date"] = row.transaction_date

		return itemwise_data


@frappe.whitelist()
def create_mps(source_name, target_doc=None):
	def postprocess(source, doc):
		doc.naming_series = "MPS.YY.-.######"

	doc = get_mapped_doc(
		"Sales Forecast",
		source_name,
		{
			"Sales Forecast": {
				"doctype": "Master Production Schedule",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {
					"name": "sales_forecast",
					"from_date": "from_date",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doc
