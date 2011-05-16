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
var tableName = "";

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
			//warnSaveFailure(initialRequest, status, error);
			successfulAjaxOnlySave(ajaxResponse);
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
	$("#initial-div-cancel_button").click(function(){
		//redefine this funcion as needed locally
		cleanupForCancel();
		history.back();
	});
});

function loadPage(studentGroup, gradingInstances, isAchievementTest) {
	encoded_data = JSON.stringify({
					"gi_keys":gradingInstances,
                    "requested_action":"full_package",
					"achievement_test":isAchievementTest});
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
	loadPage(studentGroup, gradingInstances, isAchievementTest);
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

function loadAchievementTestGrades() {
	var section = $("#id_section").val();
	var achievementTest = $("#id_achievement_test").val();
	if (achievementTest !== "") {
		$.ajax({
			url: "/ajax/get_achievement_test_grading_instances",
			type: "POST",
			dataType: "json",
			data: {
				"class": "achievement_test",
				"key": achievementTest,
				"secondary_class": "section",
				"secondary_key": section
			},
			success: function(ajaxResponse){
				var gradingInstKeyArray = ajaxResponse.gradingInstKeyArray;
				//var studentRecordsArray = ajaxResponse.studentRecordsArray;
				showGradesDiv();
				getGrades(section, gradingInstKeyArray, true);
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
	var class_session = $("#id_object_instance").val();
	json_edit_grading_periods = JSON.stringify(editGradingPeriods);
	json_view_grading_periods = JSON.stringify(viewGradingPeriods);
	var student_list = [];
	json_student_list = JSON.stringify(student_list);
	if (! localParams["user_is_teacher"]) {
		changeBottomButtonsToFinished();		
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
			"key": class_session,
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

