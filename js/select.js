/**
 * @author master
 */
var selectionTable = new StandardTable();
selectionTable.maxHeight = 400;
var requestedAction;
function createWidgetTable(ajaxResponse) {
	if (ajaxResponse) {
		selectionTable.loadAjaxResponse(ajaxResponse);
		selectionTable.setHeight(selectionTable.keysArray.length);
		selectionTable.initializeTableParams();
		selectionTable.finalizeTable();
	}
}

function submitSelection(selectedKey, action) {
	if (selectedKey) {
		$("#id_state").val("Exists");
		$("#id_selection_key").val(selectedKey);
		$("#id_requested_action").val(action);
		$("#id_prior_selection").val(localParams.priorSelection);
		$("#form2").submit();
	}
	return false;
}

function processKey(event) {
	if (event.keyCode == 13) {
		if (selectionTable.isInitialized()) {
			event.preventDefault();
			var selectedKey = selectionTable.getSingleSelectedKeyNoWarn();
			if (selectedKey !== null) {
				submitSelection(selectedKey, requestedAction);
			}
		}
	}
}

function modifyHelpBalloonText(balloonHelp){
	for (var DomID in balloonHelp) {
		if (DomID =="select_new_button") {
			balloonHelp.select_new_button = balloonHelp.select_new_button +
			localParams.titleName;
		}
		else if (DomID =="select_edit_button") {
			balloonHelp.select_edit_button = balloonHelp.select_edit_button +
			localParams.titleName;
		}
		else if (DomID == "select_view_button") {
			balloonHelp.select_view_button = balloonHelp.select_view_button +
			localParams.titleName;
		}
	}
	return balloonHelp;
}

$(function() {
	$("#title_div").text(localParams.title);
	$('#no_table_fill').text(localParams.titleNamePlural);
	$("#no_selection_fill").text(localParams.titleName);
	$("#multiple_selection_fill").text(localParams.titleName);
	selectionTable.setSelectionDialogs($("#dialog_no_table"),
		$("#dialog_no_selection"), 
		$("#dialog_multiple_selection"));
	selectionTable.setDom(document.getElementById('table_div'));
	requestedAction = localParams.template_requested_action;
	
	function showSelection() {
		//hide top buttons, show select page
		$("#initial_div").slideUp("fast");
		$("#select_div").slideDown("slow");
	}
	
	$("#select_new_button").click(function(){
		$("#id_state").val("New");
		$("#id_requested_action").val("Create");
		$("#id_prior_selection").val(localParams.priorSelection);
		a = $("#id_requested_action").val();
		$("#form2").submit();
	});
	
	$("#select_edit_button").click(function(){
		$("#title_div").text("Edit a " + localParams.titleName);
		requestedAction = "Edit";
		showSelection();
	});

	$("#select_view_button").click(function(){
		$("#title_div").text("View a " + localParams.titleName);
		requestedAction = "View";
		showSelection();
	});		
	
	$("#select_select_button").click(function() {
		var selectedKey = selectionTable.getSingleSelectedKey();
		if (selectedKey) {
			submitSelection(selectedKey,requestedAction);
		}
		return false;
	});
	
	$("#select_cancel_button").click(standardCancel);
	
	$(document).keydown(function(event){
		if (event.keyCode == 13) {
			event.preventDefault();
			var selectedKey = selectionTable.getSingleSelectedKeyNoWarn();
			submitSelection(selectedKey, requestedAction);
		}
	});
	
});

