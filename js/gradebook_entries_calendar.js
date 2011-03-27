/**
 * @author master
 */


var calendarStartDate = null;
var calendarEndDate = null;


function openGradebookEntryEditPage(domElement, gradebookEntry) {
	$('#id_selection_key').val(gradebookEntry.key);
	$('#id_object_instance').val(gradebookEntry.key);
	$('#id_state').val("Exists");
	$('#id_requested_action').val("Edit");
	$('#form2').submit();
}


function openNewGradebookEntry(domElement, selectedDate) {
	var dateString = $.fullCalendar.formatDate(selectedDate, "MM'/'dd'/'yyyy");
	$("#id_date").val(dateString);
	$('#id_state').val("New");
	$('id_requested_action').val("Create");
	$.cookie("calendar_selected_date", dateString);
	openEditWindow("grading_event", null, null);
	$('#form2').submit();
}


function openGradebookEntry(domElement, gradebookEntry, selectedDate){
	var gradebookEntryKey = (gradebookEntry === null)?null:gradebookEntry.key;
	var dateString = $.fullCalendar.formatDate(selectedDate, "MM'/'dd'/'yyyy");
	$("#id_date").val(dateString);
	$.cookie("calendar_selected_date", dateString);
	openEditWindow("grading_event", gradebookEntryKey, null);	
}

function clearGradebookEntrySelection() {
	$('#id_selection_key').val("");
	$('#id_object_instance').val("");
	$("#id_date").val("");		
}

function changeEntryDate(gradebookEntry, deltaDays) {
		$.ajax( {
		url: "/ajax/change_date/",
		type: "POST",
		dataType: "json",
        data: {"class":"grading_event",
				"key":gradebookEntry.key,
				"delta_days":deltaDays
			},
		error:	function(ajaxResponse) {
			//if the date change has failed reload all calendar data 
			//to assure currency
			getCalendarInfo(calendarStartDate, calendarEndDate);
			}
	});
}

$(function() {
	var tooltipsApi = $("[title]").data("title");
	setActiveClassSessionIfCookieAvailable();
	var gradebookEntrys = new selectableElements();
		gradebookEntrys.selectableCssName = "selectable-event";
		gradebookEntrys.selectedCssName = "selected-event";
		gradebookEntrys.doubleClickFunction = openGradebookEntry;
		gradebookEntrys.initialize();
	var entries = new selectableElements();
		entries.ignoreSelectableCssName = true;
		entries.doubleClickFunction = openNewGradebookEntry;
		entries.initialize();
	$("#new_button").click(function(){
		openNewGradebookEntry($(this), selectedDate);
	});
    $('#calendar').fullCalendar({
 		theme: true,
		header: {
				left: 'prev,next today',
				center: 'title',
				right: ''
		},
		editable: true,
		disableResizing: true,
		selectable: true,
		eventClick: function(gradebookEntry, jsEvent, view){
			gradebookEntrys.elementClicked($(this), gradebookEntry);
		},
		dayClick: function(selectedDate, allDay, jsEvent, view) {
			entries.elementClicked($(this), selectedDate);
		},
		eventDragStart: function(event, jsEvent, jsUiObj) {
			tooltipsApi.hide();
		},
		eventDrop: function(gradebookEntry, deltaDays) {
//			$(this).tooltip.hide();
			if (deltaDays != 0) {
				changeEntryDate(gradebookEntry, deltaDays);
			}
		},
		viewDisplay: function(view) {
			$.loadanim.start({message:"Loading Grades Calendar"});
			calendarStartDate = view.visStart;
			calendarEndDate = view.visEnd;
			getCalendarInfo(calendarStartDate, calendarEndDate);
		},
		eventRender: function(gradebookEntry, element) {
			if (gradebookEntry.info !== null) {
				element.attr("title", gradebookEntry.info);
			}
		}
    });

	function createEntry(data){
		/*
			gradebookEntry is single element of json return containing a 
			dictionary of information
			The information uses short keys to limit the response size.
			Keys are: k:key, n:name c:geintry type, g:grades are already recorded,
			i:information to be shown in info bubble
		*/
		var gradebookEntry = {};
		gradebookEntry.start = new Date(data.d[0], data.d[1], data.d[2]);
		gradebookEntry.allDay = true;
		gradebookEntry.key = data.k;
		var title = data.n;
		gradebookEntry.info = data.n;
		var showInfo = true;
		switch (data.c) {
			case "Single":
				gradebookEntry.className = "calendar-single-grade selectable-event";
				break;
			case "Recurring":
				gradebookEntry.className = "calendar-recurring-grade selectable-event";
				break;
			case "UpperLevel":
				gradebookEntry.className = "calendar-ul-grade selectable-event";
				break;
			default:
				gradebookEntry.className = "calendar-markerday";
		}
		if (data.g) {
			gradebookEntry.className += "calendar-grades-entered"
		}			
		if ((data.i !== null) && (data.i.length > 0)) {
			gradebookEntry.info = gradebookEntry.info + "<hr>" + data.i;
		}
		gradebookEntry.info = gradebookEntry.info + "<hr>" + data.o;
		if (! showInfo){
			gradebookEntry.info = null;
		}
		gradebookEntry.title = title;
		return gradebookEntry;
	}
	
	function getCalendarInfo(startDate, endDate) {
		//Request the information about gradebook entries for the time period
		$.ajax( {
			url: "/ajax/get_gradebook_entries/",
			type: "POST",
			dataType: "json",
	        data: {"class":"grading_instance",
				"start_date":convertDateToJson(startDate),
				"end_date":convertDateToJson(endDate),
				"class_session":$("#id_class_session").val()},
			success: function(ajaxResponse){
				$.loadanim.stop();
				clearGradebookEntrySelection();
				for (var i=0; i < ajaxResponse.length; i++) {
					var newGradebookEntry = createEntry(ajaxResponse[i]);
					$('#calendar').fullCalendar("renderEvent", newGradebookEntry);
				}
				setupTooltips();
			},
			error:	function(ajaxResponse) {
				$.loadanim.stop();
				reportError(ajaxResponse, "Failed to Load Calendar");
				}
		});
	}
	$("create_day_dialog").dialog(std_delete_dialog);	
});
