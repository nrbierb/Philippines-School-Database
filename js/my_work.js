/**
 * @author master
 * Perform specially focused actions for teachers with predefined targets
 */

var hideString = "Hide Other Tasks " + String.fromCharCode(8657);
var showString = "Show Other Tasks " + String.fromCharCode(8659);
var isTeacher = false;
var isAdvisor = false;
function saveSelectedInCookie() {
	//clear out old ones -- just cleanup for those that have already used this
	$.cookie("aSn",null);
	$.cookie("aS", null);
	$.cookie("aCn", null);
	$.cookie("aC", null);
	//selected values are used in return to the my_work page
	$.cookie("sSn",null);
	$.cookie("sS", null);
	$.cookie("sCn", null);
	$.cookie("sC",null);
	
	//active values are used in all other pages
	$.cookie("aSn", $("#id_users_section_name").val(), {page:'/'});
	$.cookie("aS", $("#id_users_section").val(), {page:'/'});
	$.cookie("aCn", $("#id_users_class_session_name").val(), {page:'/'});
	$.cookie("aC", $("#id_users_class_session").val(), {page:'/'});
	//selected values are used in return to the my_work page
	$.cookie("sSn", $("#id_users_section_name").val(), {page:'/'});
	$.cookie("sS", $("#id_users_section").val(), {page:'/'});
	$.cookie("sCn", $("#id_users_class_session_name").val(), {page:'/'});
	$.cookie("sC", $("#id_users_class_session").val(), {page:'/'});
}

function saveSelected() {
	var selectedValues = {"active_section":$("#id_users_section").val(),
		"active_class_session": $("#id_users_class_session").val()};
	setUserPreferences(selectedValues);
}

function submitAction(selectedKey,requestedAction, newUrl) {
	saveSelectedInCookie();
	if (($("#id_users_section").val() != localParams.users_section) ||
	($("#id_users_class_session").val() != localParams.users_class_session)) {
		//update saved preferences only if changed
		saveSelected();
	}
	$("#id_state").val("Exists");
	$("#id_selection_key").val(selectedKey);
	$("#id_requested_action").val(requestedAction);
	$("#form2").attr("action",newUrl);
	$("#form2").submit();
}

function setSectionUserStatus(){
	if (isAdvisor) {
		$("#attendance_button").removeClass("not-ready");
		$("#sect_tests_button").removeClass("not-ready");
		$("#sect_students_button").val("Edit Students");
	} else {
		$("#attendance_button").addClass("not-ready");
		$("#sect_tests_button").addClass("not-ready");
		$("#sect_students_button").val("View Students");		
	}
}

function setClassSessionUserStatus() {
	if (isTeacher) {
		$("#class_grades_button").val("Edit Grades");
		//$("#class_grading_button").removeClass("not-ready");
	} else {
		$("#class_grades_button").val("View Grades");
		//$("#class_grading_button").addClass("not-ready");
	}
}

function setActiveSection(data){
	var key = "";
	var name = "";
	isAdvisor = false;
	if (data) {
		keystring = data.item.key;
		name = data.item.value;	
		key = keystring.slice(1);
		isAdvisor = (keystring.slice(0,1) === '+');
	}
	$("#id_users_section").val(key);
	$("#id_users_section_name").val(name);
	setSectionUserStatus();
}

function setActiveClassSession(data){
	var key = "";
	var name = "";
	isTeacher = false;
	if (data) {
		keystring = data.item.key;
		name = data.item.value;	
		key = keystring.slice(1);
		isTeacher = (keystring.slice(0,1) === '+');
	}
	$("#id_users_class_session").val(key);
	$("#id_users_class_session_name").val(name);
	setClassSessionUserStatus();
}

function toggleSectionExpansion() {
		$('#section_task1').slideToggle(50,function(){
			if ($('#sect_expand_button').val() == showString) {
				$('#sect_expand_button').val(hideString);
			}
			else {
				$('#sect_expand_button').val(showString);
			}
		});
		$('#section_task2').slideToggle(50);
	}

function toggleClassExpansion() {
		$('#class_task1').slideToggle(50, function(){
			if ($('#class_expand_button').val() == showString) {
				$('#class_expand_button').val(hideString);
			}
			else {
				$('#class_expand_button').val(showString);
			}
		});
		$('#class_task2').slideToggle(50);	
}
/*
 * Actions:
 * sections 
 * attendance: return to url attendance with selection_key the key of the section action edit
 * report button -return to url reports/students with section selection key
 * students -- return to url build-list/student with section key
 * classes?
 * details return to url section with with selection_key the key of the section action edit
 * 
 * Classes:
 * grades: return to /initialselect/grading_instance/grades with selection key and action select
 * reports: return to reports/classes with class selection key
 * grading_instance: return to /select/grading_instance with class_key action select
 * students:return to build_list/class with class_key
 * details:return to class_session with selection class_key
 */

$(function(){
	$("#dialog_not_advisor_attendance").dialog(std_ok_dialog);
	$("#dialog_not_advisor_achtest").dialog(std_ok_dialog);
	$("#dialog_not_teacher").dialog(std_ok_dialog);
	$("#id_users_section_name").val(localParams.users_section_name);
	$("#id_users_section").val(localParams.users_section);
	$("#id_users_class_session_name").val(localParams.users_class_session_name);
	$("#id_users_class_session").val(localParams.users_class_session);
	isTeacher = localParams.user_is_class_session_teacher;
	isAdvisor = localParams.user_is_section_advisor;
	setClassSessionUserStatus(isTeacher);
	setSectionUserStatus(isAdvisor);	
	$(".menu-button").click(function(){
		var target, action, url;
		var selectedKey = "default";
		var sectionKey = $("#id_users_section").val();
		var classSessionKey= $("#id_users_class_session").val();
		switch (this.id) {
			case "attendance_button":
				if (! isAdvisor) {
					$("#dialog_not_advisor_attendance").dialog('open');
					return true;
					}
				target = "Section";
				action = "Edit";
				url = "/attendance";
				break;				
			case "sect_report_button":
				target = "Section";
				action = "Edit";
				url = "/choose_report";
				break;
			case "sect_students_button":
				target = "Section";
				//action changed to Edit for section advisor in server code
				action = "Select";
				url = "/choose/section_students";
				break;
			case"sect_classes_button":
				target = "Section";
				action = "Select";
				url = "/choose/section_classes";
				break;
			case "sect_expand_button":
				//Expand the list for other tasks.
				//Completely different kind of action from all other buttons.
				return toggleSectionExpansion();
			case "sect_tests_button":
				if (! isAdvisor) {
					$("#dialog_not_advisor_achtest").dialog('open');
					return true;
					}
				target="Section";
				action="Edit";
				url="/achievement_test_grades";
				break;
			case "sect_details_button":
				target = "Section";
				action = "View";
				url = "/section";
				break;
			case "class_grades_button":
				/*
				if (! isTeacher) {
					$("#dialog_not_teacher").dialog('open');
					return true;
					}
					*/
				target = "Class";
				action = "Edit";
				url = "/grading_period_results";
				break;
			//to be fixed
			/*
			case "class_reports_button":
				target = "Class";
				action = "Select";
				url = "/choose_report/class";
				break;
			case "class_grading_button":
				target = "Class";
				action = "Select";
				url = "/gradebook_entries_calendar";
				break;
				*/
			case "class_students_button":
				target = "Class";
				action = "Select";
				url = "/choose/class_session_students";
				break;
			case "class_expand_button":
				//Expand the list for other tasks.
				//Completely different kind of action from all other buttons.
				return toggleClassExpansion();
			case "class_details_button":
				target = "Class";
				action = "View";
				url = "/class_session";
				break;
			case "my_choices_button":
				action = "Edit";
				url = "/my_choices";
				break;
			case "my_info_button":
				target = "Teacher";
				action = "Edit";
				url = "/teacher";
				break;
			case "my_school_button":
				target = "School";
				action = "View";
				url = "/school";
				break;
			default:
				//do nothing
				return true;
		}
		
		switch (target) {
			case "Section":
				selectedKey = sectionKey;
				if (selectedKey == "") {
					reportError("Please select a Section first.", "Section Select Needed");
				}
				break;
			case "Class":
				selectedKey = classSessionKey;
				if (selectedKey === "") {
					reportError("Please select a Class first.", "Class Select Needed");
				}
				break;
			case "Teacher":
				selectedKey = localParams.personKey;
				break;
			case "School":
				selectedKey = localParams.school;
				break;
			default:
				selectedKey = "Dummy Fill";
		}
		
		if (selectedKey != "") {
			submitAction(selectedKey, action, url);
		} else {
			//show warning
		}
	});
});

