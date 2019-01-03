# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import os
import json
from frappe.utils.nestedset import rebuild_tree
import copy

class AdministrativeAreaImportTool(Document):
	pass

def get_country_files(doctype, txt, searchfield, start, page_len, filters):
	data_files = os.listdir('../apps/address_data/address_data/address_data/data')
	countries_with_data = []
	for filename in data_files:
		with open('../apps/address_data/address_data/address_data/data/' + filename, 'r') as f:
			administrative_areas = json.loads(f.read())
			countries_with_data.extend(administrative_areas.keys())
	return frappe.db.sql('SELECT * FROM `tabCountry` WHERE name IN ("{0}")'.format('","'.join(countries_with_data)))

@frappe.whitelist()
def make_administrative_area_fixtures(country_list):
	
	#make_administrative_areas(country_list)
	
	frappe.utils.background_jobs.enqueue(
		make_administrative_areas,
		country_list = country_list, 
		queue="long",
		timeout=36000,
		enqueue_after_commit=True,
	)
	
	
def make_administrative_areas(country_list):
	file_country_mapping = {}
	data_files = os.listdir('../apps/address_data/address_data/address_data/data')
	for filename in data_files:
		with open('../apps/address_data/address_data/address_data/data/' + filename, 'r') as f:
			administrative_areas_data = json.loads(f.read())
			for con in administrative_areas_data.keys():
				file_country_mapping[con] = filename
	
	world_record = {
		"doctype": "Administrative Area",
		"title": "World",
		"administrative_area_type": "world",
		"is_group": 1,
		"parent": "",
		"parent_unique_name": "",
		"self_unique_name": "World"
	}
	make_fixture_record(world_record)

	for country in json.loads(country_list):
		with open("../apps/address_data/address_data/address_data/data/" + file_country_mapping[country]) as f:
			administrative_areas = json.loads(f.read())[country]
		
		country_record = {
			"doctype": "Administrative Area",
			"title": country.title(),
			"administrative_area_type": "country",
			"is_group": 1,
			"parent": "",
			"parent_administrative_area": "World",
			"parent_unique_name": "",
			"self_unique_name": country.title()
		}
		make_fixture_record(country_record)

		for record in administrative_areas:
			record.update({
				"parent_unique_name": "".join(record['parent']),
				"self_unique_name": "".join(record['parent']) + "" + record['title']
			})

		for record in administrative_areas:
			record.update({
				"doctype": "Administrative Area",
				"parent_administrative_area": get_parent_name(country, record, administrative_areas),
				"is_group": 1
			})

			make_fixture_record(record)

		# use rebuild_tree function from nestedset to calculate lft, rgt for all nodes
		rebuild_tree("Administrative Area", "parent_administrative_area")


def get_parent_name(country, record, administrative_areas):
	if record['parent_unique_name'] == "":
		return country.title()
	else:
		parent_details = [area for area in administrative_areas if area['self_unique_name'] == record['parent_unique_name']]
		if len(parent_details) == 0:
			frappe.throw("wrong parent hierarchy")
		elif len(parent_details) > 1:
			frappe.throw("duplicate entry")
		else:
			try:
				return parent_details[0]["name"]
			except KeyError:
				pass
				frappe.throw("parent occurs after child in json file")

def make_fixture_record(record):
	record_to_insert = copy.deepcopy(record)
	# create a copy and delete keys which are not docfields
	del record_to_insert['parent']
	del record_to_insert['parent_unique_name']
	del record_to_insert['self_unique_name']
	
	from frappe.modules import scrub
	doc = frappe.new_doc(record_to_insert.get("doctype"))
	doc.update(record_to_insert)
	# ignore mandatory for root
	parent_link_field = ("parent_" + scrub(doc.doctype))
	if doc.meta.get_field(parent_link_field) and not doc.get(parent_link_field):
		doc.flags.ignore_mandatory = True

	try:
		doc.db_insert()
		record.update({"name": doc.name})
		frappe.db.commit()
	except frappe.DuplicateEntryError as e:
		# pass DuplicateEntryError and continue
		if e.args and e.args[0] == doc.doctype and e.args[1] == doc.name:
			# make sure DuplicateEntryError is for the exact same doc and not a related doc
			record.update({"name": e.args[1]})
		else:
			raise
	except frappe.ValidationError as e:
		area_name = str(e).split(" already exists")[0]
		record.update({"name": area_name})


