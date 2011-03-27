/**
 * @author master
 * Perform all special actions for the student edit form
 */

$("#dialog_duplicate_warning").dialog(simple_ok_dialog);

function showMatchWarn(first_name, last_name, municipality, community, birthdate){
	$("#duplicate_student_name").text("Name: " +first_name + " " + last_name);
	$("#duplicate_municipality").text("Municipality: " + municipality);
	$("#duplicate_community").text("Barangay: " + community);
	$("#duplicate_birthdate").text("Birthdate: " + birthdate);
	$("#dialog_duplicate_warning").dialog('open');
}
	
function showMatchWarnIfNeeded(matchInfo) {
	if (matchInfo.FoundMatch) {
		var match = matchInfo.match;
		showMatchWarn(match.first_name, match.last_name, 
		match.municipality, match.community, match.birthdate);
	}
}

function sendCheckRequest(){
	//If this is a new record check to see if it is a duplicate
	//for the same student
	if ($("#id_object_instance").val() == "NOTSET") {
		$.ajax({
			url: "/ajax/find_similar_students/",
			data: {
				"last_name": $("#id_last_name").val(),
				"first_name": $('#id_first_name').val(),
				"community": $('#id_community').val(),
				"birthdate": $('#id_birthdate').val()
			},
			dataType: "json",
			success: function(ajaxResponse){
				var parsedData = eval(ajaxResponse);
				showMatchWarnIfNeeded(parsedData);
			}
		});
	}
}

$("#id_birthdate").change(function(){
	//Once the birthdate is entered then it is time to check for
	//duplicate entries
	sendCheckRequest();	
});
	
function change_element_display(element_id, display_action)
{
    var element = document.getElementById(element_id);
    element.style.display = display_action;
}

function request_update_date_field(fieldname, name_for_alert)
{
    var field_id = "id_" + fieldname + "_change_date";
    var label_td_id = "id_" + fieldname + "_change_date_label";
    var form_td_id = "id_" + fieldname + "_change_date_field";
    var warning_element_id = "id_" + fieldname + "_warning";
    var field = document.getElementById(field_id);
    field.value = "";
    change_element_display(warning_element_id, "table-row");
    change_element_display(label_td_id, "table-cell");
    change_element_display(form_td_id, "table-cell");
}


function updateParentsTable(){
	updateRelationsTable("parent", "priority|cell_phone|relationship", parentsTable);
	parentsTable.fnSort([[2, "asc"]]);
}

function updateSiblingsTable(){
	updateRelationsTable("siblings", "class_year|section", siblingsTable);
}
	
var cachedFamilyKey = null;
var newlyCreatedFamilyKey = null;
var shouldCreateFamily = false;

$('#id_sibling_select').html('<table cellpadding="0" cellspacing="0" border="0" class="display datatable striped" width="100%" id="siblingSelectTable"></table>');
var siblingSelectTable = $("#siblingSelectTable").dataTable({
	"bJQueryUI": true,
	"aaData": [],
	"bPaginate": false,
	"bAutowidth": false,
	"sDom": '<"H">t<"F">',
	"aoColumns": [{
		//sibling key
		"bSortable": false,
		"bVisible": false,
		"bSearchable": false
	}, {
		"sTitle": "Name",
		"bSortable": false,
		"bSearchable": true,
		"sWidth": "60%"
	}, {
		"sTitle": "Class Year",
		"bSortable": false,
		"bSearchable": false,
		"sWidth": "20%"
	}, {
		"sTitle": "Section",
		"bSortable": false,
		"bSearchable": false,
		"sWidth": "20%"
	}]
});

fnSetRowSelect("#id_sibling_select", true);

$('#id_siblings').html('<table cellpadding="0" cellspacing="0" border="0" class="display datatable striped" width="100%" id="siblingsTable"></table>');
var siblingsTable = $("#siblingsTable").dataTable({
	"bJQueryUI": true,
	"aaData": [],
	"bPaginate": false,
	"bAutowidth": false,
	"sDom": '<"H">t<"F">',
	"aoColumns": [{
		"bSortable": false,
		"bVisible": false,
		"bSearchable": false
	}, {
		"sTitle": "Name",
		"bSortable": false,
		"bSearchable": true,
		"sWidth": "60%"
	}, {
		"sTitle": "Class Year",
		"bSortable": false,
		"bSearchable": false,
		"sWidth": "20%"
	}, {
		"sTitle": "Section",
		"bSortable": false,
		"bSearchable": false,
		"sWidth": "20%"
	}]
});


$('#id_parents').html('<table cellpadding="0" cellspacing="0" border="0" class="display datatable striped" width="100%" id="parentsTable"></table>');
var parentsTable = $("#parentsTable").dataTable({
	"bJQueryUI": true,
	"aaData": [],
	"bPaginate": false,
	"bAutowidth": false,
	"sDom": '<"H">t<"F">',
	"aoColumns": [{
		//parent key
		"bSortable": false,
		"bVisible": false,
		"bSearchable": false
	}, {
		"sTitle": "Name",
		"bSortable": false,
		"bSearchable": true,
		"sWidth": "60%"
	}, {
		//contact order
		"bSortable": true,
		"bVisible": false,
		"bSearchable": false
	}, {
		"sTitle": "Phone",
		"bSortable": false,
		"bSearchable": false,
		"sWidth": "20%"
	}, {
		"sTitle": "Relation",
		"bSortable": false,
		"bSearchable": false,
		"sWidth": "20%"
	}]
});

fnSetRowSelect("#id_parents", true);


function updateRelationsTable(relationship, extra_fields, table){
	$.ajax({
		url: "/ajax/students_family/",
		data: {
			"class": "family",
			"key": $("#id_family").val(),
			"secondary_class": "student",
			"secondary_key": $("#id_object_instance").val(),
			"relationship": relationship,
			"extra_fields": extra_fields
		},
		dataType: "json",
		success: function(returnData){
			fnUpdateTable(table, returnData);
		}
	});
}

function revertRelations(){
	updateRelations(cachedFamilyKey);
}

function updateRelations(familyKey){
	$("#id_family").val(familyKey);
	updateParentsTable();
	updateSiblingsTable();
}

function delayedTableUpdate() {
	setTimeout("updateParentsTable()",1200);
}

function deleteParent(instance_key){
	$.ajax({
		type: "POST",
		url: "/ajax/delete_instance/",
		data: {
			"class": "parent_or_guardian",
			"key": instance_key
		},
		dataType: "json",
		success: function(returnData){
			updateParentsTable();
		}
	});
}

function createFamily(){
	$.ajax({
		type: "POST",
		url: "ajax/create_family/",
		data: {
			"name": $("#id_last_name").val()
		},
		dataType: "json",
		success: function(returnData){
			$("#id_family").val(returnData);
			newlyCreatedFamilyKey = returnData;
		}
	});
}

function setFamilyFromSibling(siblingsKey){
	$.ajax({
		type: "POST",
		url: "ajax/students_family_key/",
		data: {
			"class": "student",
			"key": siblingsKey
		},
		dataType: "json",
		success: function(returnData){
			updateRelations(returnData);
		}
	});
}

function suggestSiblings(){
	$.ajax({
		type: "POST",
		url: "ajax/suggest_siblings/",
		data: {
			"class": "student",
			"key": getInstanceKey(),
			"filter-last_name": $("#id_last_name").val(),
			"extra_fields" : "class_year|section"
		},
		dataType: "json",
		success: function(returnData){
			fnUpdateTable(siblingSelectTable, returnData);
			var siblingsCount = 0;
			if (returnData) {
				siblingsCount = returnData.length;
			}
			siblingsSuggested(siblingsCount);
		}
	});
}

function siblingsSuggested(count){
	$("#sibling_select_display").slideDown("fast");
}

function createFamilyAndParent(){
	createFamily();
	openEditWindow("parent", null, null);
	shouldCreateFamily = false;
}

$("#dialog_no_lastname").dialog(std_ok_dialog);
$("#dialog_select_sibling").dialog(std_ok_dialog);
$("#dialog_select_edit").dialog(std_ok_dialog);
$("#dialog_select_delete").dialog(std_ok_dialog);
$("#dialog_siblings_check").dialog({
	modal: true,
	autoOpen: false,
	buttons: {
		"Ok": function(){
			suggestSiblings();
			$(this).dialog("close");
		},
		"Cancel": function(){
			createFamilyAndParent();
			$(this).dialog("close");
		}
	}
});

$("#dialog_confirm_delete").dialog(std_delete_dialog);

function warnNoSiblingSelection(){
	$("#dialog_select_sibling").dialog('open');
}
function warnNoLastName(){
	$("#dialog_no_lastname").dialog('open');
}

function adviseSiblingsCheck(){
	$("#dialog_siblings_check").dialog("open");
}

function warnNoEditSelection(){
	$("#dialog_select_edit").dialog('open');
}

function warnNoDeleteSelection(){
	$("#dialog_select_delete").dialog('open');
}

function confirmDelete(){
	$("#dialog_confirm_delete").dialog('open');
	return confirmDialogOk;
}

$("#check_sibling_select_btn").click(function(){
	var sibling = getSelectedRowKeyAndData(siblingSelectTable, warnNoSiblingSelection, null);
	if (sibling && sibling[0]) {
		setFamilyFromSibling(sibling[0]);
	}
});

$("#keep_sibling_select_btn").click(function(){
	var sibling = getSelectedRowKeyAndData(siblingSelectTable, warnNoSiblingSelection, null);
	if (sibling && sibling[0]) {
		setFamilyFromSibling(sibling[0]);
		$("#sibling_select_display").slideUp("fast");
	}
});

$("#cancel_sibling_select_btn").click(function(){
	$("#sibling_select_display").slideUp("fast");
	if (shouldCreateFamily) {
		createFamilyAndParent();
	}
	else {
		revertRelations();
	}
});

$("#add_siblings_btn").click(function(){
	if ($("#id_last_name").val()) {
		cachedFamilyKey = $("#id_family").val();
		suggestSiblings();
	}
	else {
		warnNoLastName();
	}
});

$("#reset_siblings_btn").click(function(){
	$("#sibling_select_display").slideUp("slow");
	updateRelations(newlyCreatedFamilyKey);
});

$("#new_parent_btn").click(function(){
	var family = $("#id_family").val();
	if ((family != "") && (family != "NOTSET")) {
		openEditWindow("parent", null, null);
	}
	else {
		if ($("#id_last_name").val()) {
			if (!shouldCreateFamily) {
				adviseSiblingsCheck();
				shouldCreateFamily = true;
			}
			else {
				createFamilyAndParent();
			}
		}
		else {
			warnNoLastName();
		}
	}
});

$("#edit_parent_btn").click(function(){
	var keyAndData = getSelectedRowKeyAndData(parentsTable, warnNoEditSelection, null);
	if (keyAndData) {
		openEditWindow("parent", keyAndData[0], getInstanceKey(), updateParentsTable);
	}
});

$("#delete_parent_btn").click(function(){
	deleteObject(parentsTable, warnNoDeleteSelection, 
$("#dialog_confirm_parent_delete"), defaultDeleteConfirm, deleteParent);
});

$.initWindowMsg();

$.windowMsg("child_closing", function(message){
	delayedTableUpdate();
});

fnInitializeTable($("#id_parents_initial_val"), parentsTable);
parentsTable.fnSort([[2, "asc"]]);
fnInitializeTable($("#id_siblings_initial_val"), siblingsTable);
$('#id_birthdate').datepicker({
	minDate: '-25Y',
	maxDate: '-10Y',
	defaultDate: "-13Y",
	changeMonth: true,
	changeYear: true
});

$('#childhood_btn').click(function(){
	$('#childhood_history').slideToggle(400, function(){
		if ($('#childhood_btn').val() == "Show Childhood History") {
			$('#childhood_btn').val("Hide Childhood History");
		}
		else {
			$('#childhood_btn').val("Show Childhood History");
		}
	});
});

$('#transfer_btn').click(function(){
	$('#transfer').slideToggle(400, function(){
		if ($('#transfer_btn').val() == "Show School Transfer") {
			$('#transfer_btn').val("Hide School Transfer");
		}
		else {
			$('#transfer_btn').val("Show School Transfer");
		}
	});
});

//clean up after a cancel on a new student if a family has been created


function cleanupForCancel(){
	var studentKey = $("#id_object_instance").val();
	var familyKey = $("#id_family").val();
	if ((studentKey == "NOTSET") && (familyKey != "NOTSET")) {
		$.ajax({
		url: "/ajax/cleanup_family/",
		data: {
			"class": "family",
			"key": familyKey
		},
		dataType: "json"
	});		
	}
}

//tooltips

$(function(){
	//$("[title]").tooltip();
	//$("#add_siblings_btn[title]").tooltip();	
	//$("#id_siblings[title]").tooltip();	
});

