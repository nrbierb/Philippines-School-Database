/**
 * @author master
 */


$(function() {
	function openSchoolDayEditPage(domElement, schoolDay) {
		$('#id_selection_key').val(schoolDay.key);
		$('#id_object_instance').val(schoolDay.key);
		$('#id_state').val("Exists");
		$('#id_requested_action').val("Edit");
		$('#form2').submit();
	}

	function openNewSchoolDay(domElement, selectedDate) {
		var dateString = $.fullCalendar.formatDate(selectedDate, "MM'/'dd'/'yyyy");
		$("#id_date").val(dateString);
		$('#id_state').val("New");
		$('id_requested_action').val("Create");
		$.cookie("calendar_selected_date", dateString);
		$('#form2').submit();
	}
	
	function moveSchoolDay(event){
		$.ajax( {
			url: "/ajax/set_schoolday_date/",
			type: "POST",
			dataType: "json",
	        data: {"class":"school_day",
				"key":event.key,
				"new_date":convertDateToJson(event.start)},
			success: function(ajaxResponse){
				//This will also handle the date not changed result
				if (ajaxResponse.changeMade) {
					event.databaseDate = new Date(event.start.valueOf());
					reportError(ajaxResponse.dialogText, "Date Changed");					
				} else {
					event.start = new Date(event.databaseDate.valueOf());
					reportError(ajaxResponse.dialogText, "Date Was Not Changed");
					$('#calendar').fullCalendar("updateEvent", event);										
				}
				setupTooltips();
			},
			error:	function(xhr, textStatus, errorThrown) {
				event.start = event.databaseDate;
				reportServerError(xhr, textStatus, errorThrown);				
				}
		});
	}
	
	function clearSchoolDaySelection() {
		$('#id_selection_key').val("");
		$('#id_object_instance').val("");
		$("#id_date").val("");		
	}
	var events = new selectableElements();
		events.selectableCssName = "selectable-event";
		events.selectedCssName = "selected-event";
		events.doubleClickFunction = openSchoolDayEditPage;
		events.initialize();
	var days = new selectableElements();
		days.ignoreSelectableCssName = true;
		days.doubleClickFunction = openNewSchoolDay;
		days.initialize();
    $('#calendar').fullCalendar({
 		theme: true,
		header: {
				left: 'prev,next today',
				center: 'title',
				right: ''
		},
		editable: true,
		disableDragging: false,
		selectable: true,
		eventClick: function(schoolDay, allDay, jsEvent, view){
			events.elementClicked($(this), schoolDay);
		},
		dayClick: function(selectedDate, allDay, jsEvent, view) {
			days.elementClicked($(this), selectedDate);
		},
		viewDisplay: function(view) {
			$.loadanim.start({message:"Loading Calendar"});
			getCalendarInfo(view.visStart, view.visEnd);
		},
		eventRender: function(event, element) {
			if (event.info !== null) {
				element.attr("title", event.info);
			}
		},
		eventDrop: function(event, dayDelta, minuteDelta, allDay, revertFunc, jsEvent, ui, view){
			moveSchoolDay(event);
		}
				
    });

	function createEvent(data){
		//data is single element of json return containing a dictionary of information
		var event = {};
		event.start = new Date(data.d[0], data.d[1], data.d[2]);
		event.databaseDate = new Date(data.d[0], data.d[1], data.d[2]);
		event.allDay = true;
		event.key = data.k;
		var title = data.c;
		event.info = data.c;
		var showInfo = true;
		switch (data.c) {
			case "School Day":
				event.className = "calendar-regular selectable-event";
				showInfo = false;
				break;
			case "Weekend":
				event.className = "calendar-weekend selectable-event";
				showInfo = false;
				break;
			case "Not In Session":
			case "Break":
				event.className = "calendar-vacation selectable-event";
				showInfo = false;
				break;
			case "Other Not Attend":
				event.className = "calendar-vacation selectable-event";
				break;
			case "National Holiday":
			case "Local Holiday":
				event.className = "calendar-holiday selectable-event";
				break;
			case "Makeup Full Day":
			case "Makeup Half Day Morning":
			case "Makeup Half Day Afternoon":
				event.className = "calendar-makeup selectable-event";
				break;
			default:
				event.className = "calendar-markerday";
		}
		if ((data.i !== null) && (data.i.length > 0)) {
			event.info = event.info + "<hr>" + data.i;
		}
		event.info = event.info + "<hr>" + data.o;
		if (! showInfo){
			event.info = null;
		}
		event.title = title;
		return event;
	}
	
	function getCalendarInfo(startDate, endDate) {
		//Request the information for a calendar date range
		$.ajax( {
			url: "/ajax/get_calendar/",
			type: "POST",
			dataType: "json",
	        data: {"class":"school_day",
				"start_date":convertDateToJson(startDate),
				"end_date":convertDateToJson(endDate)},
			success: function(ajaxResponse){
				$.loadanim.stop();
				clearSchoolDaySelection();
				for (var i=0; i < ajaxResponse.length; i++) {
					var newEvent = createEvent(ajaxResponse[i]);
					$('#calendar').fullCalendar("renderEvent", newEvent);
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
