
var attTable = new StandardTable();
var endDate = Date.today();
var maxEndDate;
var msPerDay = 1000 * 60 * 60 * 24;
var dayTypeArray = [];
var maxRows;
var maxColumns;
var generatedHeader = "";
var datesArray;
var dataFieldArray = [];
var dataMapping =
	// a set of binary masks to decode or encode individual
	//cell values. This is a copy of the masks in the python
	//file "models.py" from the class studentAttendanceData
	//These two must be kept consistent
	{"valid":128, "known":64, "school_day":32,"present":1};
var valueImages = {
	"notactive":{"alt_text":"X", "image":"/media/hash.gif", "name":"notactive"},
	"noedit":{"alt_text":"N", "image":"/media/dash.gif", "name":"noedit"},
    "unknown":{"alt_text":"U",	"image":"/media/yellow-question.gif", "name":"unknown"},
    "present":{"alt_text":"P", "image":"/media/green-check.png", "name":"present"},
    "absent":{"alt_text":"A", "image":"/media/red-x.png","name":"absent"}
};

function DataField() {
	this.imageName = "noEdit";
	this.className = "attTblDayInvalid";
	this.$dayField = null;
	this.valid = false;
	this.known = false;
	this.schoolDay = false;
	this.present = false;
	this.dayColumn = null;
	this.row = 0;
	this.column = 0;
}

DataField.prototype.getDayTypeInformation = function() {
	//compute only when needed
	this.className = "attTblDayInvalid";
	this.imageName = "notactive";
	if (this.valid) {
		this.imageName = "noedit"
		this.className = "attTblDayValid";
		if (this.schoolDay) {
			this.className = "attTblDaySchoolday";
			this.imageName = "unknown";
			if (this.known) {
				this.imageName = (this.present) ? "present" : "absent";
			}	
		}
	}
	return ({"classname":this.className, "imageName":this.imageName});	
};

DataField.prototype.unpackValues = function(dataTablePackedValue, row, column, dayColumn ) {
	this.row = row;
	this.column = column;
	this.dayColumn = dayColumn;
	this.valid = ((dataTablePackedValue & dataMapping.valid) !== 0);
	this.known = ((dataTablePackedValue & dataMapping.known) !==  0);
	this.schoolDay = ((dataTablePackedValue & dataMapping.school_day) !== 0);
	this.present = ((dataTablePackedValue & dataMapping.present) !== 0);
};

DataField.prototype.packValues = function() {
	var valid = (this.valid)?dataMapping.valid:0;
	var known = (this.known)?dataMapping.known:0;
	var schoolDay = (this.schoolDay)?dataMapping.school_day:0;
	var present = (this.present)?dataMapping.present:0;	
	var packed =  valid + known + schoolDay + present;
	return packed;	
};

function convertDateToJson(date) {
	var month = date.getMonth() + 1;
	var day = date.getDate();
	var year = date.getFullYear();
	var dateArray = [year, month, day];
	return JSON.stringify(dateArray);	
}

function getDataFieldFromTd($dayField){
	var dataFieldIndex = $dayField.val();
	return dataFieldArray[dataFieldIndex];
}

function setDataFieldFromClassnames($dayField){
	//This needs to be done only once to connect day fields
	//and dataField objects
	var rowRe = /attRow-(\d+)/;
	var colRe = /attCol-(\d+)/;
	var classes = $dayField.attr("class");
	var rowVals = rowRe.exec(classes);
	var colVals = colRe.exec(classes);
	var row = (rowVals !== null)?Number(rowVals[1]):0;
	var column = (colVals !== null)?Number(colVals[1]):0;
	var dataField;
	//this should be at a computable index but search just to be sure
	for (var i = 0; i < dataFieldArray.length; i++) {
		dataField = dataFieldArray[i];
		if ((dataField.row == row) && (dataField.column == column)) {
			break;
		}
	}
	$dayField.val(i);
	dataField.dayField = $dayField;
	return dataField;
} 

function formatTable(dataTable){
	maxRows = attTable.dataTable.getNumberOfRows();
	maxColumns = attTable.dataTable.getNumberOfColumns() -1;
	var periodClassnames = [" attTblMorn attTblMornNormal "," attTblAft attTblAftNormal "];
	var dataFieldIndex = 0;	
	$("#table_header_div").html(generatedHeader);
	for (var row = 0; row < maxRows; row++) {
		//set name column
		var rowClass = " attRow-" + row;		
		var classString = "attTblRecordBase attTblStudentName attColName " + rowClass;
		attTable.dataTable.setCell(row,0,undefined,undefined,{
			className:classString});
		//set data columns
		for (var column = 0; column < maxColumns; column++) {
			var colClass = " attCol-" + column;
			var period = column % 2;
			var dayIndex =  Math.floor(column / 2);
			var dayClass = " attDay-" +	dayIndex;
			var dataField = new DataField();
			dataField.unpackValues(attTable.dataTable.getValue(row,column + 1),
				row, column, dayIndex);
			dataFieldArray[dataFieldIndex] = dataField;
			dataFieldIndex++;
			classString =  'attTblRecordBase attDayField ' + 
				colClass + rowClass + 
				dayClass + periodClassnames[period] + 
				dataField.getDayTypeInformation().classname;
			attTable.dataTable.setCell(row,column + 1,undefined,undefined,{className:classString});
		}
	}
	setupTooltips();
}

function cleanupFormActions() {
	//perform event reassignment 
	$("#save_button").unbind("click");
	
	function attendanceSave() {
		saveAnnounce();
		returnResults();
		};	
				
	$("#save_button").one("click", attendanceSave);	
}

function identifyDayFields($dayTd) {
	var dayClass = $dayTd.attr("id");
	var day = $("." + dayClass);
	var morn = day.filter(".attTblMorn");
	var aftn = day.filter(".attTblAft");
	return ({"morn":morn, "aftn":aftn});
}	

function getDayFieldValue($dayField){
	var image = $dayField.children("img");
	var value = image.attr("name");
	return value;
}

function getImage(imageName) {
	var valueImage = valueImages[imageName];
	if (! valueImage) {
		valueImage = valueImages.unknown;
	}
	var image = document.createElement("img");
	image.setAttribute("alt", valueImage.alt_text);
	image.setAttribute("src", valueImage.image);
	image.setAttribute("name", valueImage.name);
	return image;
}

function setImage($dayField, imageName){
	var image = getImage(imageName);
	if (image) {
		$dayField.empty("img");
		$(image).appendTo($dayField);
	}	
}

function setDayFieldValue($dayField, value){
	//set image and dataTable
	var dataField = getDataFieldFromTd($dayField);
	if ((value == "present") || (value == "absent")) {
		dataField.known = true;
		dataField.present = (value == "present");
	}
	setImage($dayField,value);
}

function initializeDayFields() {
	$(".attDayField").each(function(i){
		var dataField = setDataFieldFromClassnames($(this));
		var typeInfo = dataField.getDayTypeInformation();
		var imageName = typeInfo.imageName;
		setImage($(this), imageName);
	});
}

function toggleField($dayField) {
	//invert present/absent values
	var newValue = "present";
	var dataField = getDataFieldFromTd($dayField);	
	if (dataField.present) {
		newValue = "absent";
	}
	setDayFieldValue($dayField, newValue);	
}

function activateDayFields($dayFields){
	$dayFields.click(function(){
		toggleField($(this));	
	});
	$dayFields.each(function(i){
		var value = getDayFieldValue($(this));
		if (value == "unknown" || (value === null)) {
			setDayFieldValue($(this), "present");
		}
	});
}

function deactivateDayFields($dayFields) {
	$dayFields.unbind("click");		
}


function deactivateDayCol(){
	//find active
	var $currentActiveDay = $(".attTblHeaderActive");
	if ($currentActiveDay) {
		$currentActiveDay.removeClass("attTblHeaderActive ui-state-active");
		var dayFields = identifyDayFields($currentActiveDay);
		dayFields.morn.removeClass("attTblMornActive ui-state-active");
		dayFields.aftn.removeClass("attTblAftActive ui-state-active");
		deactivateDayFields(dayFields.morn);
		deactivateDayFields(dayFields.aftn);
	}
}
	
function activateDayCol($dayTd){
	deactivateDayCol();	
	$dayTd.addClass("attTblHeaderActive ui-state-active");
	var dayFields = identifyDayFields($dayTd);
	dayFields.morn.addClass("attTblMornActive ui-state-active");
	dayFields.aftn.addClass("attTblAftActive ui-state-active");
	activateDayFields(dayFields.morn);
	activateDayFields(dayFields.aftn);
}

function toggleDayCol($dayTd){
	var currentActiveDay = $(".attTblHeaderActive").attr("id");
	if ($dayTd.attr("id") != currentActiveDay) {
		activateDayCol($dayTd);
	} else {
		deactivateDayCol();
	}
}

function clearClass(cssClass) {
	$(".attTblHeaderBase").removeClass(cssClass);
	$(".attTblMorn").removeClass(cssClass);
	$(".attTblAft").removeClass(cssClass);		
}

function setClassForDayCol($dayTd, cssClass){
	clearClass(cssClass);
	var dayFields = identifyDayFields($dayTd);
	dayFields.morn.addClass(cssClass);
	dayFields.aftn.addClass(cssClass);
	$dayTd.addClass(cssClass);
}

function toggleRow($rowTd) {
	//can't set row id so need to get css class name by searching
	var rowClasses = $rowTd.attr("class");
	var selectRe = /attRow-\d+/;
	var matches = rowClasses.match(selectRe);
	if (matches !== null) {
		var rowClass = matches[0];
		var $dayFields =$("." + rowClass).filter(".ui-state-active");
		$dayFields.each(function(i){
			toggleField($(this));
		});
	}
}

function initializeTableActions() {
	initializeDayFields();
	$(".headerTdSd").click(function() {
		toggleDayCol($(this));
	});
	$(".headerTdSd").hover(
		function() {
			setClassForDayCol($(this),"ui-state-hover");
		},
		function() {
			clearClass("ui-state-hover");
		}
	);
	$(".attTblStudentName").click(function() {
		toggleRow($(this));
	});
	$.loadanim.stop();
}

function extractDayTypeArray(ajaxResponse) {
	if (ajaxResponse) {
		if (ajaxResponse.length > 2) {
			dayTypeArray = json_parse(ajaxResponse[2]);
		}
	}
}

function extractHeader(ajaxResponse) {
	if (ajaxResponse) {
		if (ajaxResponse.length > 3) {
			generatedHeader = json_parse(ajaxResponse[3]);
		}
	}
}

function extractDatesArray(ajaxResponse) {
	if (ajaxResponse) {
		if (ajaxResponse.length > 4) {
			datesArray = json_parse(ajaxResponse[4]);
		}
	}
}

attTable.tableParameters = {"sort":"disable", "width":986};
attTable.formatFunction = formatTable;
attTable.readyFunction = initializeTableActions;

function buildAttendanceTable(ajaxResponse){
	attTable.initializeTableParams();
	attTable.tableParameters.cssClassNames.headerRow="hidden";
	attTable.tableParameters.cssClassNames.selectedTableRow="";
	attTable.loadAjaxResponse(ajaxResponse);
	attTable.finalizeTable();	
}

function loadPage(sectionKey, endDate) {
    $.ajax( {
		url: "/ajax/get_attendance/",
		type:"POST",
        dataType: "json",
        data: {"class":"section",
                "key":sectionKey,
                "end_date":convertDateToJson(endDate)},
        success: function(ajaxResponse) {
				dayTypeArray = json_parse(ajaxResponse.dayTypeArray);
				generatedHeader = json_parse(ajaxResponse.generatedHeader);
				datesArray = json_parse(ajaxResponse.dateArray);
                buildAttendanceTable(ajaxResponse);
				cleanupFormActions();
                },
		error: function(ajaxResponse, textStatus) {
			reportServerError(ajaxResponse, textStatus);
			}		
        });
}

function marshallResults(){
	var attendanceData = new Array(maxRows);
	for (var i=0; i < maxRows; i++){
		attendanceData[i] = new Array(maxColumns);
	}
	for (i = 0; i < dataFieldArray.length; i++) {
		var dataField = dataFieldArray[i];
		attendanceData[dataField.row][dataField.column] = 
			dataField.packValues();
	}
	var theData = {"keys":attTable.keysArray, "dates":datesArray, "attendance_data":attendanceData};
	return (JSON.stringify(theData));
}

function returnResults() {
	$.ajax( {
		url: "/ajax/set_attendance/",
		type: "POST",
		dataType: "json",
        data: {"json_attendance_data": marshallResults()},
		timeout: 20000,
		success: function(returnData){
			successfulSave(returnData);
			},
		error: function(initialRequest, status, error) {
			warnSaveFailure(initialRequest, status, error);
		}
	});
}


$(function() {
// Initialization actions
	var sectionKey = $("#id_section").val();
	if ((sectionKey == "") && ($.cookie("active_section") != null)){
		sectionKey = $.cookie("active_section");
	}

	var samePeriodDialog =  $('#local_error_div')
		.html('Same weeks that you see now.')
		.dialog({
			autoOpen: false,
			title: 'No Change',
			buttons: { "Ok": function() { $(this).dialog("close");}}			
		});

	$("#date_select").datepicker({buttonText:'Choose a date to view', 
		showWeek:true, gotoCurrent:true, buttonImageOnly:false,
		showOtherMonths: true, selectOtherMonths: true, 
		maxDate:"-1d", minDate:"-2m",
		onClose: function(dateText, inst) {
			var priorEndDate = endDate;
			var startDate = Date.parse(dateText);
			if (!startDate.is().sunday()) {
				startDate.last().sunday();
			}
			endDate = startDate.add(13).days();
			if (maxEndDate.compareTo(endDate) == -1) {
				endDate = maxEndDate;
			}
			var endWeek = endDate.getWeekOfYear();
			var priorEndWeek = priorEndDate.getWeekOfYear();
			if (endWeek != priorEndWeek) {
				var animText = (endWeek > priorEndWeek)? 
					"later" : "earlier";
				$.loadanim.start({
					message: "Loading " + animText + " Records"
				});
				loadPage(sectionKey, endDate);
			} else {
				samePeriodDialog.dialog("open");
			}
		}} );		
	maxEndDate = Date.today();
	if (!maxEndDate.is().saturday()) {
		maxEndDate = maxEndDate.next().saturday();
	}	
	attTable.setDom(document.getElementById('table_div'));
	$.loadanim.start({message:"Loading Student Records"});
	loadPage(sectionKey, maxEndDate);
});

	
