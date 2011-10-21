/**
 * @author master
 * Perform all special actions for the student edit form
 */

var parentsTable = new StandardTable();
parentsTable.initializeTableParams();
parentsTable.maxHeight = 250;
parentsTable.objectClass = "parent_or_guardian";
parentsTable.sortOrder = 1;
parentsTable.initializeTableParams();
parentsTable.setDom(document.getElementById('id_parents'));
parentsTable.setSelectionDialogs(null, $("#dialog_select_edit"), $("#dialog_multi_select"), 
	$("#dialog_confirm_parent_delete"));

var siblingsTable = new StandardTable();
parentsTable.initializeTableParams();
siblingsTable.maxHeight = 200;
siblingsTable.objectClass = "student";
siblingsTable.initializeTableParams();
siblingsTable.setDom(document.getElementById('id_siblings'));

var siblingSelectTable = new StandardTable();
parentsTable.initializeTableParams();
siblingSelectTable.maxHeight = 400;
siblingSelectTable.objectClass = "student";
siblingSelectTable.initializeTableParams();
siblingSelectTable.setDom(document.getElementById('id_sibling_select'));
siblingSelectTable.setSelectionDialogs(null, $("#dialog_select_sibling"), 
	$("#dialog_multi_select"), null);
		

var cachedFamilyKey = null;
var newlyCreatedFamilyKey = null;
var shouldCreateFamily = false;

function updateRelationsTable(relationship, extra_fields, table){
	var params = {
			"class": "family",
			"key": $("#id_family").val(),
			"secondary_class": "student",
			"secondary_key": getInstanceKey(),
			"relationship": relationship,
			"extra_fields": extra_fields
		}
	requestTable("/ajax/students_family/", params, table);
}

function updateParentsTable(){
	updateRelationsTable("parent", "contact_order|cell_phone|relationship", parentsTable);
}

parentsTable.updateTableFunction = updateParentsTable;

function updateSiblingsTable(){
	updateRelationsTable("siblings", "class_year|section", siblingsTable);
}

function updateSiblingSelectTable(){
	var params = {
			"class": "student",
			"key": getInstanceKey(),
			"filter-last_name": $("#id_last_name").val(),
			"extra_fields" : "class_year|section"
		};
	requestTable("/ajax/suggest_siblings", params, siblingSelectTable);
}
	
function showMatchWarnIfNeeded(matchInfo) {
	if (matchInfo.FoundMatch) {
		reportError( matchInfo.dialogHtml, "Student Already in Database");
	}
}

function sendCheckRequest(){
	//If this is a new record check to see if it is a duplicate
	//for the same student
	if ($("#id_object_instance").val() == "NOTSET") {
		$.ajax({
			url: "/ajax/find_similar_students/",
			type: "POST",
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
		url: "/ajax/students_family_key/",
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
	updateSiblingSelectTable();
	$("#sibling_select_display").slideDown();
}

function createFamilyAndParent(){
	createFamily();
	openEditWindow("parent_or_guardian", null, null);
	shouldCreateFamily = false;
}

$("#dialog_no_lastname").dialog(std_ok_dialog);
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

function warnNoLastName(){
	$("#dialog_no_lastname").dialog('open');
}

function adviseSiblingsCheck(){
	$("#dialog_siblings_check").dialog("open");
}

$("#check_sibling_select_btn").click(function(){
	var siblingKey = siblingSelectTable.getSingleSelectedKey();
	if (siblingKey) {
		setFamilyFromSibling(siblingKey);
	}
});

$("#keep_sibling_select_btn").click(function(){
	var siblingKey = siblingSelectTable.getSingleSelectedKey();
	if (siblingKey) {
		setFamilyFromSibling(siblingKey);
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
		openEditWindow("parent_or_guardian", null, null);
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
    var editKey = parentsTable.getSingleSelectedKey();
    if (editKey) {
        openEditWindow("/parent_or_guardian", editKey, null);
    }
});

$("#delete_parent_btn").click(function(){
	parentsTable.deleteSelectedRow();
});

$("#view_parent_btn").click(function(){
    var viewKey = parentsTable.getSingleSelectedKey();
    if (viewKey) {
        openEditWindow("/parent_or_guardian", viewKey, null, '&requested_action="View"');
    }
});

$.windowMsg("child_closing", function(message){
	delayedTableUpdate();
});

$('#id_birthdate').datepicker({
	//minDate: '-25Y',
	//maxDate: '-9Y',
	defaultDate: "-13Y",
	yearRange: "-25:-9",
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
		type: "POST",
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
//Initialize form
updateParentsTable();
updateSiblingsTable();
$.initWindowMsg();
