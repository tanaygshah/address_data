// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Administrative Area Import Tool', {
	refresh: function(frm) {
		frm.disable_save();
		frm.country_list = []
		frm.set_query('add_country', () => ({
			query: 'address_data.address_data.doctype.administrative_area_import_tool.administrative_area_import_tool.get_country_files'
		  }));0
	  
	},

	add_country: function(frm){
		if(frm.doc.add_country){
			var child = frm.add_child('countries_to_import')
			child.country = frm.doc.add_country
			frm.refresh_field('countries_to_import')
			frm.set_value("add_country", "")
			frm.refresh_field("add_country")
		}
	},

	import_data: function(frm){
		frm.doc.countries_to_import.forEach(function(entry){
			frm.country_list.push(entry.country)
		})
		frappe.call({
			method: 'address_data.address_data.doctype.administrative_area_import_tool.administrative_area_import_tool.make_administrative_area_fixtures',
			args: {"country_list": frm.country_list},
			callback: function(resp){
				frappe.msgprint("This import will run as a background job and might take several minutes to finish. Please check status of background job before shutting down frappe")
				console.log("resp", resp)
			}
		})
	}
});
