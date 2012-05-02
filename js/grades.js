/**
 * @author master
 */

var gradesTable = new StandardTable();
gradesTable.maxHeight = 600;
gradesTable.rowHeight = 35;
gradesTable.tableParameters.allowHtml = true;
var gradesTableInfo = null;
var recordsKeyArray = [];
var gradingInstKeyArray = [];
var gradingInstDetails = {};
var datesArray = [];
var studentRecordsJson ="";
var studentGroup = "";
var gradingInstances = "";
var gradingInstOwnerType = "";
var gradingInstOwner = "";
var editedGradingPeriodsArray = [];
var studentKeysArray = [];
var currentGradesArray = [];
var achievementTestKey = "";
var tableName = "";


function resetAchievementTestTableValues() {
	for (var i = 0; i < currentGradesArray.length; i++) {
		y = i.toString();
		for (var j = 0; j < currentGradesArray[0].length; j++) {
			x = (j).toString();
			fieldId = "gradesTable-" + x + "-" + y;
			$("#" + fieldId).val(currentGradesArray[y][x+1]);
		}
	}
	$("#id_spreadsheet_text").val("");
}

function validateSpreadsheet(spreadsheetInfo, studentRowsCount, gradeColumnsCount) {
	var row;
	var valid = false;
	var problem = "";
	if (spreadsheetInfo.length == 0) {
		problem += "Incorrect copy and paste -- Missing Rows At Start"
	} else {
		if (spreadsheetInfo[0] != achievementTestKey) {
			problem = "Incorrect Spreadsheet -- Wrong Achievement Test";
		}
		if (spreadsheetInfo[1] != studentGroup) {
			addProblemLineBuffer(problem);
			problem += "Incorrect Spreadsheet -- Wrong Section";
		}
		if (spreadsheetInfo[2] != gradeColumnsCount) {
			addProblemLineBuffer(problem);
			problem += "Incorrect copy and paste -- Missing Columns";
		}
		if (spreadsheetInfo[3] != studentRowsCount) {
			addProblemLineBuffer(problem);
			problem += "Incorrect copy and paste -- Missing Rows At End";
		}
		if (problem != "") {
			problem += "<br/>Spreadsheet cannot be loaded."
		}
	}
	return problem;
}

function findTableColumnName(columnIndex) {
	 var  key = gradingInstKeyArray[columnIndex];
	 return $("#" + key).val();
}

function findTableStudentName(rowIndex) {
	var fieldId = "gradesTable-0-" + rowIndex.toString();
	$("#" + fieldId).val(grade);
	return $("#" + fieldId).val();
}

function findSpreadsheetColumnName(columnIndex) {
	return "";
}

function findSpreadsheetStudentName(studentRows, studentKey) {
	return studentRows[studentKey][0];
}

function addProblemLineBuffer(problem) {
	if (problem != "")
		problem += "<br/>";
	return problem;
}

function mapColumns(subjectKeys){
	var problem = "";
	var subjectKeysAssoc = {};
	var keyMap = [];
	var extraTableSubjects = [];
	var i;
	for (i = 0; i < subjectKeys.length; i++) {
		subjectKeysAssoc[subjectKeys[i]] = i;
	}	
	for (i = 0; i < gradingInstKeyArray.length; i++) {
		if (subjectKeysAssoc[gradingInstKeyArray[i]] != undefined) {
			keyMap[i] = subjectKeysAssoc[gradingInstKeyArray[i]];
			delete subjectKeysAssoc[gradingInstKeyArray[i]];
		} else {
			keyMap[i] = -1;
			extraTableSubjects.push(findTableColumnName(i));
		} 
	}
	if (extraTableSubjects.length > 0) {
		var n = extraTableSubjects.length;
		problem = n + " subject" + addPlural(n) +
			" in the table " + choosePluralVerb(n) + " not found in the spreadsheet:";
		for (i = 0; i < extraTableSubjects.length; i++) {
			problem += "<br/>" + extraTableSubjects[i];
		}
	}
	var n = 0;
	for (var key in subjectKeysAssoc) {n++}
	if (n > 0) {
		problem = addProblemLineBuffer(problem) + n + " subject " + addPlural(n) +
			"in the spreadsheet " + choosePluralVerb(n) + " not found in the table:"
		for (var key in subjectKeysAssoc) {
			problem += "<br/>" +  findSpreadsheetColumnName(key);	
		}
	}
	return [keyMap,problem];	
}

function matchStudents(studentRows) {
	var problem = "";
	var tmpStudentAssoc = {};
	var tmpStudentKeysRemain = [];
	var problem = "";
	var key;
	for (key in studentRows) {
		tmpStudentAssoc[key] = 1;		
	}
	for (var i = 0; i < studentKeysArray.length; i++) {
		if (tmpStudentAssoc[studentKeysArray[i]] != undefined) {
			delete tmpStudentAssoc[studentKeysArray[i]];
		} else {
			tmpStudentKeysRemain.push(i);
		}
	}
	var n = 0;
	for (var key in tmpStudentAssoc) {n++}
	if (n > 0) {
		problem = n + " student " + addPlural(n) + " in the spreadsheet " + 
			choosePluralVerb(n) + " not in the table:";
		for (key in tmpStudentAssoc) {
			problem += "<br/>" + findSpreadsheetStudentName(studentRows, key);
		}
	}
	if (tmpStudentKeysRemain.length > 0) {
		addProblemLineBuffer(problem);
		n = tmpStudentKeysRemain.length;
		problem += n + " student" + addPlural(n) + " in the table " + 
			choosePluralVerb(n) + " not in the spreadsheet:";
		for (var i = 0; i < n; i++) {
			problem += "<br/>" + findTableStudentName(tmpStudentKeysRemain[i]);
		}
	}
	return (problem);
}

function loadTable(subjectKeys, studentRows) {
	var problem = matchStudents(studentRows);
	var mapResults = mapColumns(subjectKeys);
	var columnMap = mapResults[0];
	var x, y;
	var grade;
	var row;
	var fieldId;
	problem = addProblemLineBuffer(problem) + mapResults[1];
	for (var i = 0; i < studentKeysArray.length; i++) {
		y = i.toString();
		row = studentRows[studentKeysArray[i]];
		for (var j = 0; j < columnMap.length; j++) {
			if ((row != undefined) & (columnMap[j] != -1)) {
				grade = row[columnMap[j + 2]];
			}
			else {
				grade = "";
			}
			x = j.toString();
			fieldId = "gradesTable-" + x + "-" + y;
			$("#" + fieldId).val(grade);
		}
	}
	return problem;
}

function loadAchievementTestTableFromSpreadsheet() {
	var line;
	var row = []; 
	var rows = [];
	var studentRows = {};
	var rowIndex = 0;
	var startIndex = 0;
	var subjectKeys = [];
	var spreadsheetInfo = [];
	var raw_input = $("#id_spreadsheet_text").val();
	var lines = raw_input.split('\n');
	for (line in lines) {
		rows.push(lines[line].split("\t"));
	}
	while (rows[startIndex][0] != "Spreadsheet Start") {
		if (rows[startIndex][0] == "Subject Keys") {
			subjectKeys = rows[startIndex].slice(2);
		}
		startIndex++;
	}
	spreadsheetInfo = rows[startIndex].slice(1);
	var studentRowsPart = rows.slice(++startIndex);
	var studentRowsCount = 0;
	for (i in studentRowsPart) {
		row = studentRowsPart[i];
		if (row.length > 1) {
			studentRowsCount++;
			studentRows[row[1]] = row;
		}
	}
	var gradeColumnsCount = studentRowsPart[0].length - 2;
	var spreadsheetProblems = validateSpreadsheet(spreadsheetInfo, 
		studentRowsCount, gradeColumnsCount);
	if (spreadsheetProblems != "") {
		reportError(spreadsheetProblems, "Failed To Load Spreadsheet");
	}
	else {
		spreadsheetProblems = loadTable(subjectKeys, studentRows);
		if (spreadsheetProblems != "") {
			reportError(spreadsheetProblems, "Spreadsheet Problems");
		}
	}
}

function buildGradesTable(ajaxResponse) {
	gradesTable.loadAjaxResponse(ajaxResponse);
	gradesTable.setHeight(gradesTable.keysArray.length);
	gradesTable.finalizeTable();
}

function buildGdInstDetailBlock(){
	detail_block_html = "";
	if (gradingInstDetails) {
		var info = gradingInstDetails[gradingInstKeyArray[0]];
		detail_block_html = '<table><tr><td>Name:</td><td>' + info.name + '</td></tr>' +
		'<tr><td>Type:</td><td>' +
		info.grdType +
		'</td></tr>' +
		'<tr><td>Percent Grade:</td><td>' +
		info.percent +
		'%</td></tr>' +
		'<tr><td>Weight:</td><td>' +
		'10' +
		'</td></tr>' +
		'<tr><td>Date:</td><td>' +
		'<input id="id_gi_date" type="text" class="popup-calendar date-mask required entry-field" name="gi_date">' +
		'</input></td></tr>' +
		'</table>';
	}
	return (detail_block_html);
}

function buildGdInstDetailsSection() {
	var gdInstDetailBlock = buildGdInstDetailBlock();
	$("#id_grading_instances").replaceWith(gdInstDetailBlock);
}

function gdInstChanges(){
	var giChangeDict = {};
	var gdInst;
	for (gdInst in gradingInstKeyArray) {
		giChangeDict.gdInst = "";		
	}
	return (JSON.stringify(giChangeDict));
}

function returnResults(studentGroupType, studentGroup, gradingInstOwnerType, gradingInstOwner) {
	$.loadanim.start({
		message: "Saving Student Grades"
	});
	//block multiple save attempts
	$("#save_button").unbind("click");
	$.ajax( {
		type: "POST",
		url: "/ajax/set_grades/",
		dataType: "json",
        data: {"class":studentGroupType,
			"key":studentGroup,
			"secondary_class":gradingInstOwnerType,
			"secondary_key":gradingInstOwner,
			"json_grades_data": gradesTable.marshallInputFieldsResults(
				"gradesTable", gradingInstKeyArray),
			"json_student_records": studentRecordsJson,
			"json_gi_changes": gdInstChanges()},
		timeout: 31000,
		success: function(ajaxResponse){
			successfulAjaxOnlySave(ajaxResponse);
			},
		error: function(initialRequest, status, error) {
			//>>>>>>!!!!!fix me<<<<<<<
			warnSaveFailure(initialRequest, status, error);
			//successfulAjaxOnlySave(ajaxResponse);
		}
	});
}


function cleanupFormActions() {
	//perform event reassignment 
	$.loadanim.stop();
	setupEntryFields();
	$("#save_button").unbind("click");
	$("#save_button").click(function() {
		$.loadanim.start({message:"Saving Student Records"});
		returnResults();
		});	
}

$(function() {
	$("#initial_div_cancel_button").click(function(){
		//redefine this function as needed locally
		cleanupForCancel();
		location.href = page_prior_url;
	});
});


function loadGrades(studentGroup, gradingInstances) {
	encoded_data = JSON.stringify({
					"gi_keys":gradingInstances,
                    "requested_action":"full_package"});
    $.ajax( {
		url: "/ajax/get_grades/",
		type:"POST",
        dataType: "json",
        data: {"class":"student_grouping",
			"key":studentGroup,
			"encoded_data":encoded_data},
        success: function(ajaxResponse) {
			gradingInstKeyArray = json_parse(ajaxResponse.gradingInstKeyArray);
			gradingInstDetails = json_parse(ajaxResponse.gradingInstDetails);
			//the student records are never used in the web page, they are just 
			//returned when sending results
			studentRecordsJson = ajaxResponse.studentRecordsArray;
			buildGdInstDetailsSection();
			buildGradesTable(ajaxResponse);
			cleanupFormActions();
			},
		error: function(ajaxResponse, textStatus) {
			reportServerError(ajaxResponse, textStatus);
			}
    });
}

function getGrades(studentGroup, gradingInstances, isAchievementTest){
	gradesTable.setDom(document.getElementById('id_grades_table'));
	$.loadanim.start({
		message: "Loading Student Grades"
	});
	loadGrades(studentGroup, gradingInstances, isAchievementTest);
}

function showGradesDiv() {
	//hide top part of form, show grade table
	$("#initial_div").hide();
	$("#grades_div").show();
}

function setGradingPeriodChanges() {
	titleString = "Quarterly Grades for " + localParams["class_session_name"];
	$("#form_title").html(titleString);
}

function getAchievementTestGrades(){
	gradesTable.setDom(document.getElementById('id_grades_table'));
	$.loadanim.start({
		message: "Loading Achievement Test Grades"
	});
	loadAchievementTestGrades();
}

function loadAchievementTestGrades() {
	studentGroup =  $("#id_section").val();
	var achievementTest = $("#id_achievement_test").val();
	var encodedData = JSON.stringify({
					"requested_action":"full_package",
					"achievement_test":achievementTest});
	if (achievementTest !== "") {
		$.ajax({
			url: "/ajax/get_grades/",
			type: "POST",
			dataType: "json",
			data: {
				"class": "section",
				"key": studentGroup,
				"encoded_data":encodedData
			},
			success: function(ajaxResponse){
				gradingInstKeyArray = json_parse(ajaxResponse.gradingInstKeyArray);
				achievementTestKey = json_parse(ajaxResponse.achievementTest);
				studentKeysArray = json_parse(ajaxResponse.keysArray);
				currentGradesArray = json_parse(ajaxResponse.rawDataArray);
				buildGradesTable(ajaxResponse);
				cleanupFormActions();
			},
			error: function(ajaxResponse, textStatus){
				reportServerError(ajaxResponse, textStatus);
			}
		});
	} else {
		reportError("You must choose an Achievement Test first. If no tests are available click the Cancel button.");
	}
}

function loadGradingPeriodGrades(editGradingPeriods, viewGradingPeriods) {
	studentGroup = $("#id_object_instance").val();
	json_edit_grading_periods = JSON.stringify(editGradingPeriods);
	json_view_grading_periods = JSON.stringify(viewGradingPeriods);
	var student_list = [];
	json_student_list = JSON.stringify(student_list);
	if (! localParams["user_is_teacher"]) {
		changeBottomButtonsToFinished(true);		
	}
	showGradesDiv();
	gradesTable.setDom(document.getElementById('id_grades_table'));
	$.loadanim.start({
		message: "Loading Student Grades"
	});
		$.ajax({
		url: "/ajax/edit_grading_period_grades",
		type: "POST",
		dataType: "json",
		data: {
			"class": "class_session",
			"key": studentGroup,
			"action":"Get",
			"json_edit_grading_periods":json_edit_grading_periods,
			"json_view_grading_periods":json_view_grading_periods,
			"json_student_list":json_student_list
		},
		success: function(ajaxResponse){
			tableName = ajaxResponse.tableName;
			buildGradesTable(ajaxResponse);
			editedGradingPeriodsArray = jQuery.parseJSON(ajaxResponse.editedGradingPeriods);
			setGradingPeriodChanges();
			cleanupFormActions();				
		},
		error: function(ajaxResponse, textStatus){
			reportServerError(ajaxResponse, textStatus);
		}
		});
}

function saveGradingPeriodGrades(){
	$.loadanim.start({
		message: "Saving Student Grades"
	});
	//block multiple save attempts
	$("#save_grades_btn").unbind("click");
	var class_session = $("#id_object_instance").val();
	var json_grades_data = gradesTable.marshallInputFieldsResults(
				tableName, editedGradingPeriodsArray);
	var json_edited_grading_periods = JSON.stringify(editedGradingPeriodsArray);
	$.ajax( {
		type: "POST",
		url: "/ajax/edit_grading_period_grades/",
		dataType: "json",
        data: {"class":"class_session",
			"key":class_session,
			"action":"Set",
			"json_grades_data":json_grades_data,
			"edited_grading_periods":json_edited_grading_periods
			},
		timeout: 31000,
		success: function(ajaxResponse){
			successfulAjaxOnlySave(ajaxResponse);
			},
		error: function(ajaxResponse, status, error) {
			successfulAjaxOnlySave(ajaxResponse);
			//>>>fix me
			//warnSaveFailure(ajaxResponse, status, error);
		}
	});
}

