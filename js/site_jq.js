
//setup autocomplete field event handlers

function showQueryActive(domElement) {
	domElement.removeClass("ac_nodata");
	domElement.removeClass("ac_error");
//	domElement.addClass("ac_loading");
}

function showQueryCompleted(domElement) {
//	domElement.removeClass("ac_loading");
	domElement.removeClass("ui-autocomplete-loading");
	domElement.addClass("ac_flash");
	setTimeout(function(){domElement.removeClass("ac_flash");},300);
}

function showQueryNoData(domElement) {
	domElement.removeClass("ui-autocomplete-loading");
	domElement.addClass("ac_flash");
	setTimeout(function(){
		domElement.removeClass("ac_flash");
		domElement.addClass("ac_nodata");
		},300);
}

function showQueryError(domElement) {
	domElement.removeClass("ui-autocomplete-loading");
	domElement.addClass("ac_flash");
	setTimeout(function(){
			domElement.removeClass("ac_flash");
			domElement.addClass("ac_error");},300);	
}

var controlNowPressed = false;
var pageHelpText = "";

function setupEntryFields(){
	var entryFields = $(".entry-field");
	
	$(".entry-field").keydown(function(event){
		//capture enter key and move to next input field
		if (event.keyCode === 13) {
			//Dont do this in textboxes
			if ($(this).attr("type") !== "textarea") {
				event.preventDefault();
				var maxIndex = entryFields.length;
				var currentFieldIndex = entryFields.index(this);
				if (currentFieldIndex < (maxIndex - 1)) {
					var nextField = entryFields[currentFieldIndex + 1];
					nextField.focus();
					nextField.select();
				}
				return false;
			}
		}
	});
	
	$(document).keydown(function(event){
		//prevent form save on enter key everywhere
		if (event.keyCode === 13) {
			var initialTarget = $(event.target);
			if (initialTarget.attr("type") !== "textarea") {
				event.preventDefault();
			}
		}
	});
	
	// use the input filters plugin for numeric fields
	$(".integer-field").numeric({
		allowDecimal: false
	});
	
	// use the input filters plugin for numeric fields
	$(".numeric-field").numeric({
		allowDecimal: true,
		maxDecimals: 1
	});
}

var server_error_text = "Unknown error.";

function saveAnnounce() {
	// perform special actions here
	$("#id_requested_action").val("Save");
	$("#save_button").val("Saving");
	$("#save_button").attr("title","Performing the save now. Please wait.");
	$("#save_button").attr("disable","disable");
	$.loadanim.start({message:"Saving"});				
}

function standardSave() {
	// perform special actions here
	if (validator.form() ){
		$("#save_button").unbind('click');
		saveAnnounce();		
		$("#form1").submit();			
	}
}

function return_to_active_page() {
		var next_page = $.cookie("return_to_page");
		if (next_page !== null) {
			location = next_page;
		} else {
			location = "/index";
		}		
	}	
/*
 * A simple function for counting clicks on an dom element. This can be used
 * to emulate a multiple click event on any element. Each click extends the
 * active period by the clickPeriod. Returns current count.
 */
var clickCount = 0;
var clickTimeoutId = null;
function countClicks(domElement, clickActivePeriod) {
	clickCount += 1;
	window.clearTimeout(clickTimeoutId);
	clickTimeoutId = window.setTimeout(function() {
		clickCount = 0;
	} ,clickActivePeriod);
	return clickCount;
}

//empty function for local redefinition
function cleanupForCancel() {}

/* 
 * Setup the actions for the standard buttons at the bottom of the pages.
 * This is called automatically upon form initialization but may be
 * called again later if the form buttons are changed.
 */
function initializeBottomButtons() {
	
	$("#cancel_button").click(function(){
		//redefine this funcion as needed locally
		cleanupForCancel();
		history.back();
	});
	
	$("#back_button").click(function(){
		history.back();
	});

	$("#return_active_button").click(function(){
		return_to_active_page();
		});
		
	
    $("#close_button").click(function(){
        close();
    });

	$("#save_button").click(standardSave);
}

function openHelpManual(){
	window.open("/static_pages/manual.html");
}

function displayHelpDialog(helpDialogText){
	var dialogHeight = "auto";
	var dialogWidth = "auto";
	if (pageHelpText.length > 200) {
		dialogHeight = 400;
		dialogWidth = 600;
	}
	var helpDialog = $('#help_div').html(helpDialogText).dialog({
		autoOpen: false,
		position: ['right', 'top'],
		height:dialogHeight,
		width:dialogWidth,
		title: 'Help',
		buttons: {
			"Ok": function(){
				$(this).dialog("close");
			},
			"View Manual": function(){
				$(this).dialog("close");
				openHelpManual();
			}
		}
	});
	helpDialog.dialog('open');
}

function requestHelpDialog(helpPagename, testText) {
	//create an Ajax request for the contents of a help page that will be
	//displayed after the Ajax response. If no help page is known (the pagename is
	//"None"), just create a generic dialog content and display immediately,
	if (helpPagename !== "None") {
	    $.ajax( {
			url: "/ajax/generate_dialog_content/",
			type:"POST",
	        dataType: "json",
	        data: {"class":"versioned_text_manager",
	                "text_manager_name":helpPagename,
	                "test_text":testText},
	        success: function(ajaxResponse) {
					var helpData = json_parse(ajaxResponse);					
					var helpDialogHtml = helpData.dialog_help; //json_parse(ajaxResponse);
					displayHelpDialog(helpDialogHtml);
	                },
			error: function(ajaxResponse) {
				displayHelpDialog(
					'Error in getting help for this page.<br>Click "View Manual" to see the entire manual.');
				}		
		});
	} else {
		displayHelpDialog(
			'Help for this page coming soon...<br>Click "View Manual" to see the entire manual.');
	}
}

function loadHelpDialog(helpDialogHtml) {
	pageHelpText = helpDialogHtml;
}

function loadHelpBalloonTexts(balloonHelp){
	var DomID;
	modifyHelpBalloonText(balloonHelp);
	for (DomID in balloonHelp) {
		$("#"+DomID).attr({
			"title": balloonHelp[DomID]
		});
	}
}

function getHelpInfo(pagename, testText) {
	//create an Ajax request for the contents of a help page that will be
	//displayed after the Ajax response. If no help page is known (the pagename is
	//"None"), just create a generic dialog content and display immediately,
	if (pagename !== "None") {
	    $.ajax( {
			url: "/ajax/generate_dialog_content/",
			type:"POST",
	        dataType: "json",
	        data: {"class":"versioned_text_manager",
	                "text_manager_name":pagename,
	                "test_text":testText},
	        success: function(ajaxResponse) {
					var helpData = ajaxResponse;					
					var helpDialogHtml = helpData.dialog_help;
					var balloonHelp = helpData.balloon_help;
					loadHelpDialog(helpDialogHtml);
					loadHelpBalloonTexts(balloonHelp);					
					setupTooltips();
	                },
			error: function(ajaxResponse) {
				var helpDialogHtml = 
					('Error in getting help for this page.<br>Click "View Manual" to see the entire manual.');
					loadHelpDialog(helpDialogHtml);
					setupTooltips();
				}		
		});
	} else {
		displayHelpDialog(
			'Help for this page coming soon...<br>Click "View Manual" to see the entire manual.');
	}
}

$(function() {
    $('input.popup-calendar').datepicker({ });
	$('input.date-mask').mask("99/99/9999");
	$('input.month-mask').mask("99/9999");
	$('input.time-mask').mask("99:99");
	$('input.year-mask').mask("9999");
	$('input.percentage-mask').mask("999.9");
	$('input.integer-mask').mask("99999")
	

	validator = $('#form1').validate({
		invalidHandler: function(e, validator){
			var errors = validator.numberOfInvalids();
			if (errors) {
				var message = errors === 1 ? 'You missed 1 field. It has been highlighted below' : 'You missed ' + errors + ' fields.  They have been highlighted below';
				$("div.form_error span").html(message);
				$("div.form_error").show();
			} else {
				$("div.form_error").hide();
			}
		},
		submitHandler: function(form) {
			$("div.form_error").hide();
			form.submit();
		}
	});

	initializeBottomButtons();
	
	$(".history-entry").change(function(){
		$(this).parents("tr").prev().removeClass("hidden");
	});
	$(".history-datefield").change(function(){
		$(this).parents("tr").prev().addClass("hidden");
	});
	
	setupEntryFields();
	
	$('#help_button').click(function() {
		displayHelpDialog(pageHelpText);
	});		
	
	getHelpInfo( $('#help_pagename_div').text());
	
	var notReadyDialog =  $('#local_error_div')
		.html('Not yet ready. Coming soon...')
		.dialog({
			autoOpen: false,
			title: 'Not Ready',
			buttons: { "Ok": function() { $(this).dialog("close");}}			
		});		
	//a standard action for buttons that are not yet active
	$('.not-ready').click(function() {
		notReadyDialog.dialog('open');
	});
	//setup default values for the autocomplete
	$.ajaxSetup({
		type: "POST",
		timeout: 35000,
		dataType: "json"
	});
	//change the select action to compare from first letter
	$.extend( $.ui.autocomplete, {
		filter: function(array, term) {
			var matcher = new RegExp( "^" + $.ui.autocomplete.escapeRegex(term), "i" );
			return $.grep( array, function(value) {
				return matcher.test( value.label || value.value || value );
			});
		}
	});
});

//setup tooltips
function setupTooltips(){
	$(".btn[title]").tooltip({
		effect: "slide",
		opacity: 0.9,
		predelay: 600,
		delay: 0,
		events: {
			input: 'mouseover, mouseout mousedown click',
			def: 'mouseover, mouseout mousedown click'
		}
	}).dynamic();
	$("[title]").tooltip({
		effect: "slide",
		opacity: 0.9,
		predelay: 600,
		delay: 0,
		events: {
			input: 'mouseover, mouseout click',
			def: 'mouseover, mouseout click'
		}
}).dynamic();
}

function modifyHelpBalloonText(balloonHelp){
	return (balloonHelp)
}

$.datepicker.setDefaults({
	changeMonth: true,
	showOn: 'button',
	buttonImageOnly: true,
	buttonImage: '/media/calendar.gif',
	buttonText: 'Calendar' 
});

function convertDateToJson(date) {
	if (date !== null) {
		var month = date.getMonth() + 1;
		var day = date.getDate();
		var year = date.getFullYear();
		var dateArray = [year, month, day];
		return JSON.stringify(dateArray);
	} else {
		return null;
	}	
}

function getInstanceKey(){
    return $("#id_object_instance").val();
}

function getFormIsSaved() {
    var instanceKey = getInstanceKey();
    var saved = (instanceKey !== "NOTSET");
    return saved;
}

function addCommaIfNeeded(resString, count, max){
    if (count < (max - 1)) {
	    resString = resString + ", ";
    }
    return resString;
}

function edit_history(field_name, display_name) {
	var otherGetParamText = "&field_name=" + field_name + "&display_name=" + display_name;
	var current_object = $('#id_object_instance').val();
	openEditWindow("history", current_object, null, otherGetParamText);
}

function openEditWindow(requestUrl, requestKey, notSavedAction, otherGetParamText) {
	var instanceArgument = "";
	if (!otherGetParamText) {
		otherGetParamText = "";
	}
    if ((! getFormIsSaved()) && notSavedAction) {
	    notSavedAction();
	    return false;
    }
    if (requestKey) {
	    instanceArgument = "?selection_key=" + requestKey;
    }
	var windowUrl = requestUrl + instanceArgument + otherGetParamText;
	var childWindow = window.open(windowUrl,
    "temp_data_window", "scrollbars=yes,resizable=yes,height=600,width=800,left=40,top=40,status=yes,alwaysRaised=yes,dependent=yes,menubar=no,directories=no");
    return childWindow;
}

function setActiveSectionIfCookieAvailable() {
	var sectionName = $.cookie("aSn");
	var sectionKey = $.cookie("aS");
	if ((sectionName !== null) && (sectionKey !== null)) {
		$("#id_section_name").val(sectionName);
		$("#id_section").val(sectionKey);
	}
}

function setActiveClassSessionIfCookieAvailable() {
	var classSessionName = $.cookie("aCn");
	var classSessionKey = $.cookie("aC");
	if ((classSessionName !== null) && (classSessionKey !== null)) {
		$("#id_class_session_name").val(classSessionName);
		$("#id_class_session").val(classSessionKey);
	}
}

/*
function createDialogDiv(dialogDiv, dialogInfo) {
	//assumes dialogTemplate of the form <div id=dialogTemplateId><p>text1</p><p></p>
	// <p>text2</p></div>
	var dialogDivName = "#" + dialogTemplateName;
	var dialogDivName = "#confirmDeleteDiv";
	$("#confirmDeleteDiv span").html(dialogInfo);
	dialogDiv=$(dialogDivName);		
	dialogDiv.removeClass('hidden').addClass("dialog");
	return dialogDiv;
}

function defaultDeleteConfirm(dialogDiv, dialogInfo, deleteAction, deleteObjectKey, deleteObjectClass) {
	var dialogDiv = createDialogDiv(dialogDiv, dialogInfo);
	dialogDiv.dialog({
		modal:true,
		autoOpen:true,
		buttons: { "Ok": function() { $(this).dialog("destroy"); deleteAction(deleteObjectKey, deleteObjectClass);},
		         "Cancel": function() { $(this).dialog("destroy");}}});
}
*/

function changeBottomButtonsToFinished() {
	var finishButtonHtml = '<tr><td class="buttons centered">' +
		'<input value="Finished" id="return_active_button" name="action" title="Click to return back to your work" class="btn tb action"/>' +
		'</td></tr>';
	$("#cancel_save_button_fieldset tr").replaceWith(finishButtonHtml);
	$("#cancel_save_button_fieldset").removeClass("one-col-buttons").addClass("single-button");
	initializeBottomButtons();
}

function makePageReadOnly() {
	$("input:not(.same-in-view),textarea,select").attr("disabled","disabled");
	$("input:not(.same-in-view),textarea,select,body,fieldset:not(.same-in-view)").addClass("viewonly");
	$("input:button:not(.same-in-view)").attr("class","hidden");
	$(".ui-datepicker-trigger").remove();
	$(".ui-datepicker").remove();
	changeBottomButtonsToFinished();
}

var simple_ok_dialog = { modal: false, autoOpen: false,
		buttons: { "Ok": function() { $(this).dialog("close"); }}};

var std_ok_dialog = { modal: true, autoOpen: false,
		buttons: { "Ok": function() { $(this).dialog("close"); }}};
		
var std_delete_dialog = { modal: true, autoOpen: false,
		buttons: { "Ok": function() { $(this).dialog("close"); confirmDialogOk = true;},
		         "Cancel": function() { $(this).dialog("close"); confirmDialogOk = false;}}};

function loadParentWindowKey(parent_field_id, local_field_id) {
    var parent_key_dom = window.opener.document.getElementById(parent_field_id);
    if (parent_key_dom){
	    var parent_key = parent_key_dom.value;
	    if (parent_key !== "NOTSET") {
		    $("#" + local_field_id).val(parent_key);
	    }
    }
}

function setSingleValue(target_class, key, value_name, value) {
	//Send ajax message with a single value to be set according to 
	//target and target key. No response expected.
	valueJson = JSON.stringify(value);
	$.ajax( {
		url: "/ajax/set_single_value/",
		type: "POST",
		dataType: "json",
        data: {"class":target_class,
			"key":key,
			"value_name":value_name,
			"value":valueJson}
	});
}

function setUserPreferences(preferences) {
	//Send ajax message with an associative array of values keyed by preference name
	//This will be saved for the current user. No response expected.
	var preferencesJSON = JSON.stringify(preferences);
	$.ajax( {
		url: "/ajax/set_user_preferences/",
		type: "POST",
		dataType: "json",
        data: {"user_preferences":preferencesJSON}
	});	
}

function getUserPreferences(preference_names){
	//Send ajax message with a list of user preference names.
	//An associative array will be returned with the values for the current user.
	$.ajax( {
		url: "/ajax/get_user_preferences/",
		type: "POST",
		dataType: "json",
        data: {"user_preferences":preference_names},
		success: function(ajaxResponse){
			return (json_parse(ajaxResponse));
			},
		error: function(xhr, textStatus, errorThrown){
			// just return empty values
			var emptyValues = {};
			var i;
			for (i=0; i < preference_names.length; i++) {
				emptyValues[preference_names] = "";
			}
			return emptyValues;
		}
	});
}

function checkboxHideContents(theCheckbox){
	//Use a checkbox to hide the next table td contents. When box is checked
	//contents visible, when not checked it is hidden. Leaves next td visible
	//to keep table aligned
	var nextColumnContents = theCheckbox.parent().next().children(":first");
	if (theCheckbox.attr("checked")) {
		$(nextColumnContents).removeClass("hidden");
	} else {
		$(nextColumnContents).addClass("hidden");
	}	
}

//select field constructor functions

function buildLabeledInputField(varName, labelText, value) {
	var valueString = "";
	if (value) {
		valueString = "value=" + value;
	}
	var inputFieldHtml = '<tr><td><label for="id_' + varName + '">' + labelText +
	':</label></td><td><input id="id_' + varName +
	'" type="text" class="autofill" name="' +varName +'" ' + valueString +' /></td></tr>\n';
	return inputFieldHtml;
}

function buildHiddenInputField(varName, value) {
	var valueString = "";
	if (value) {
		valueString = "value=" + value;
	}
	var inputFieldHtml = '<input type="hidden"  name="' + varName + '" id="id_' +
		varName + '" ' + valueString + ' />\n';
	return inputFieldHtml;
}

function buildFixedField(varName, value){
	var fixedFieldHtml = '<div class="hidden" id="id_' + varName + '">' + value + '</div>\n';
	return fixedFieldHtml;
}

function buildInputFields(fieldInfo, selectFieldLabel, divId){
	var htmlText = '<table><tbody>\n';
	if (fieldInfo) {
		var i;
		for (i = 0; i < fieldInfo.length; i++) {
			switch(fieldInfo[i].fieldType) {
				case "fixed":
					htmlText += buildFixedField(fieldInfo[i].name, fieldInfo[i].value);
					break;
				case "hidden":
					htmlText += buildHiddenInputField(fieldInfo[i].name, fieldInfo[i].value||false);
					break;
				default: 
					htmlText += buildLabeledInputField(fieldInfo[i].name, fieldInfo[i].label, fieldInfo[i].value||false);
			}
		}
	}
	htmlText += '<tr><td><label for="id_selection" id="id_selection_label">' + selectFieldLabel +
		':</label></td><td><input type="text" class="autofill" name="selection" id="id_selection"/></td></tr>\n';
	htmlText += '</tbody></table>\n';
	$("#"+divId).html(htmlText);
}
		
function noParse(input){
	return input;
}

// reporting functions for ajax save
function successfulSave(returnData) {
	$.loadanim.stop();
	$("#id_state").val("Exists");
	$("#id_requested_action").val("Save");
	$("form").submit();
}

//No form save, go back to requesting page
function successfulAjaxOnlySave(returnData){
	$.loadanim.stop();
		var next_page = $.cookie("return_to_page");
		if (next_page !== null) {
			location = next_page;
		} else {
			location = "/index";
		}			
}

function warnSaveFailure(ajaxRequest, textStatus, error) {
	$.loadanim.stop();
	if (textStatus === "timeout") {
		reportError("The server has not confirmed that the save was completed.", "No Response From Server.");
	}
	else {
		var warningText = 'The save failed with the error "' + status +
		'" The reason was: ' +
		error;
		reportError(warningText, "Save Failed");
	}
}

function reportError(errorText, title) {
	var errorDialog = $('#<div></div)')
		.html(errorText)
		.dialog({
			autoOpen: false,
			title: title,
			buttons: {
				"Ok": function(){
					$(this).dialog("close");}}
		});
	errorDialog.dialog('open');
}

function reportServerError(xhr, textStatus, errorThrown){
	if (textStatus === "timeout") {
		reportError("The request server did not return an answer in time. You may wish to try again. If this continues to fail, click the Cancel button", "No Response From Server.");
	} else {
		var errorText = '<p>Your action was not successful. The server reported:</p><p>' +
		'--' +
		xhr.statusText +
		"--</p><p>--" +
		xhr.responseText +
		"--";
		reportError(errorText, 'Error From Server');
	}
}

//check that at least some of the input fields have values set
//each field defined must have the values id, name, and required 
function minimumRequiredFieldsSet(inputFields, numRequired) {
	var setCount = 0;
	var mustSet = String("");
	var errorText = String("");
	var inputFieldNames = "";
	var i;
	for (i=0; i<inputFields.length; i++) {
		inputFieldNames += ' "' + inputFields[i].name +'",'; 
		if ($("#" + inputFields[i].id).val() !== "") {
			setCount++;
		} else if (inputFields[i].required === true){
			mustSet += ' "' + inputFields[i].name + '",';
		}
	}
	if ((setCount >= numRequired) && (mustSet.length === 0)) {
		return true;
	}
	if (setCount < numRequired) {
		errorText = "Please set at least " + numRequired + 
		" of the fields:" + inputFieldNames.substring(0, inputFieldNames.length - 1) + ".\n";
	}
	if (mustSet.length > 0) {
		errorText += "The field" + mustSet.substring(0, mustSet.length - 1) + " must be set.";
	}
	reportError(errorText, "Cannot Create Report");
	return false;		
}
/*
 * Class to support a set of selectable dom elements on a table. The elements are identified by a
 * css class name. A single click will select, a click with control will extend, and cntl-a will
 * select all. A double click on a single element will trigger to "open" action.
 */
function selectableElements() {
	this.selectableCssName = "selectable";
	this.selectedCssName = "selected";
	this.controlPressed = false;
	this.doubleClickFunction = null;
	this.selectallEnabled = false;
	this.ignoreSelectableCssName = false;
	this.doubleClickTimeout = 300;
}

selectableElements.prototype.initialize = function() {
	$(document).keydown(function(event){
		if (event.which === 17) {
			controlNowPressed = true;
		}
		if ((event.which === 65) && controlNowPressed && this.selectallEnabled) {
			$("." + this.selectedCssName).removeClass(this.selectedCssName);
			$("." + this.selectableCssName).addClass(this.selectedCssName);	
			return false;		
		}
	});
	$(document).keyup(function(event){
		if (event.which === 17) {
			controlNowPressed = false;
		}
	});	
};

/*
 * Select a member of the selectable elements by a click. A double click will call the 
 * the doubleClickFunction with the same two arguments.
 */

selectableElements.prototype.elementClicked = function(domElement, clickedObject){
	if (domElement.hasClass(this.selectableCssName) || this.ignoreSelectableCssName) {
		var wasSelected = domElement.hasClass(this.selectedCssName);
		if (!controlNowPressed) {
			$("." + this.selectedCssName).removeClass(this.selectedCssName);
		}
		if (wasSelected) {
			domElement.removeClass(this.selectedCssName);
		} else {
			domElement.addClass(this.selectedCssName);
		}		
		if (countClicks(domElement, this.doubleClickTimeout) > 1) {
			this.doubleClickFunction(domElement, clickedObject);
		}
	}
};

selectableElements.prototype.getSelectedElements = function() {
	return $("." + this.selectedCssName);
};

//Perform an Ajax request for a standard table
//The table must be fully initialized and all parameters set before this call
//The result should be a complete table.
function requestTable(url, params, targetTable){
	$.ajax({
		url: url,
		data: params,
		success: function(ajaxResponse){
			//var responseArray = json_parse(ajaxResponse);
			targetTable.loadAjaxResponse(ajaxResponse);
			//targetTable.initializeTableParams();
			targetTable.finalizeTable();
			$.loadanim.stop();
		},
		error: function(xhr, textStatus, errorThrown){
			$.loadanim.stop();
			reportServerError(xhr, textStatus, errorThrown);
		}
	});
}
		