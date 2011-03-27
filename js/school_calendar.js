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
		}
    });

	function createEvent(data){
		//date is single element of json return containing a dictionary of information
		var event = {};
		event.start = new Date(data.d[0], data.d[1], data.d[2]);
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
			case "Other Not Attend":
				event.className = "calendar-vacation selectable-event";
				break;
			case "National Holiday":
			case "Local Holiday":
				event.className = "calendar-holiday selectable-event";
				break;
			case "Makeup Full Day":
				event.className = "calendar-makeup selectable-event";
				break;
			case "Makeup Half Day":
				event.className = "calendar-makeup selectable-event";
				event.allDay = false;
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
		//Request the information for a clandar date range and 
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
