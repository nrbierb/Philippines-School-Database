/**
 * @author master
 * Perform specially focused actions for teachers with predefined targets
 */


function saveSelectedInCookie() {
	//active values are used in all other pages
	$.cookie("active_section_name", $("#id_users_section_name").val());
	$.cookie("active_section", $("#id_users_section").val());
	$.cookie("active_class_session_name", $("#id_users_class_session_name").val());
	$.cookie("active_class_session", $("#id_users_class_session").val());
	//selected values are used in return to the my_work page
	$.cookie("selected_section_name", $("#id_users_section_name").val());
	$.cookie("selected_section", $("#id_users_section").val());
	$.cookie("selected_class_session_name", $("#id_users_class_session_name").val());
	$.cookie("selected_class_session", $("#id_users_class_session").val());
	$.cookie("return_to_page", "/my_work");
}

function saveSelected() {
	var selectedValues = {"selected_section":$("#id_users_section").val(),
		"selected_class_session": $("#id_users_class_session").val()};
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

function setChoiceValue(field_id, data, parameter){
	var field = $("#" + field_id);
	var name_field = $("#" + field_id + "_name");
	if (data) {
		field.val(data.item.key);
		name_field.val(data.item.value);
	}
	else {
		field.val("");
		name_field.val("");
	}
	setSingleValue("database_user", localParams.dbUserKey, parameter, field.val());
}

function toggleSectionExpansion() {
		$('#section_task1').slideToggle(50,function(){
			if ($('#sect_expand_button').val() == "Show Other Tasks") {
				$('#sect_expand_button').val("Hide Other Tasks");
			}
			else {
				$('#sect_expand_button').val("Show Other Tasks");
			}
		});
		$('#section_task2').slideToggle(50);
	}

function toggleClassExpansion() {
		$('#class_task1').slideToggle(50, function(){
			if ($('#class_expand_button').val() == "Show Other Tasks") {
				$('#class_expand_button').val("Hide Other Tasks");
			}
			else {
				$('#class_expand_button').val("Show Other Tasks");
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
	$("#id_users_section_name").val(localParams.users_section_name);
	$("#id_users_section").val(localParams.users_section);
	$("#id_users_class_session_name").val(localParams.users_class_session_name);
	$("#id_users_class_session").val(localParams.users_class_session);
	
	$(".menu-button").click(function(){
		var target, action, url;
		var selectedKey = "default";
		var sectionKey = $("#id_users_section").val();
		var classSessionKey= $("#id_users_class_session").val();
		switch (this.id) {
			case "attendance_button":
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
				target="Section";
				action="Edit"
				url="/achievement_test_grades";
				break;
			case "sect_details_button":
				target = "Section";
				action = "View";
				url = "/section";
				break;
			case "class_grades_button":
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
			case "class_assign_students_button":
				target = "Class";
				action = "Edit";
				url = "/assign_students";
				break;
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
				target = "Teacher"
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
				if (selectedKey == "") {
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

