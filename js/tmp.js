var subjectYearNames = [];
var subjectSubjectNames = [];
var subjectFormInfo = [];

function buildSubjectsTable(class_year, type="achievementTest") {
	var subjectName, subjectNameCol;
	var subjectNameCols = [];
	var subjectsTable;
	var subjectTr = [];
	var subjectsRows = '';
	var id, x, y;
	var numColumns = 2;
	var numRowsFirst = Math.floor(subjectSubjectNames.length / numColumns)  + 
		(subjectSubjectNames.length % numColumns);
	var numRowsOther = Math.floor(subjectSubjectNames.length / numColumns);
	var index = 0;
		var secondField = 
			'<td><input type="text" class="small-numeric-field integer-field hidden" id="subject-numfield-' 
			+ id + '"></td>';
		var subjectsTh = '<tr><th class="width75">Name</th><th></th><th class="width120"># Questions</th> ' +
		'<th class="width75">Name</th><th></th><th style="width=120"># Questions</th></tr>'; 
		}
	} else {
		var secondField = 
			'<td><input type="text" class="hidden" id="subject-namefield' + id + '"></td>';		
		var subjectsTh = '<tr><th class="width75">Name</th><th></th><th class="width120">Class Name Suffix</th> ' +
		'<th class="width75">Name</th><th></th><th style="width=120">Class Name Suffix</th></tr>'; 
		}
	}
	for (x = 0; x <numColumns; x++) {
		var rowCount = (x === 0) ? numRowsFirst : numRowsOther;
		subjectNameCols[x] = subjectSubjectNames.slice(index, index+rowCount);
		index += rowCount;
		}
	for (y=0; y< subjectNameCols[0].length; y++){
		for (x=0; x<numColumns; x++) {
			subjectNameCol=subjectSubjectNames[x];
			if (y < subjectNameCols[x].length) {
				subjectName=subjectNameCol[y];
				id = class_year + "-" + subjectName;
				subjectTr[x] = '<td>' + subjectName + '</td>' + 
				'<td><input type="checkbox" class="subject-checkbox active-checkbox" id="subject-checkbox-' + id + '"></td>' +
				secondField;
			} else {
				subjectTr[x] = "<td></td><td></td><td></td>";
			}
		}
		subjectsRows += '<tr class="subject-row">' + subjectTr[0]+ subjectTr[1] + '</tr>';
	}
	subjectsTable = '<table class="at-subjects thin-border hidden" id="subject-table-' + class_year +
		 '><tbody>' + subjectsTh + subjectsRows + '</tbody></table>';
	return subjectsTable;	
}

function subjectBuildYearsTable() {
	var yearTr, yearIndex, yearName;
	for (yearIndex = 0; yearIndex < subjectYearNames.length; yearIndex++) {
		yearName = subjectYearNames[yearIndex];
		yearTr = '<tr class="at-year"><td>' + yearName +
		'</td><td><input type="checkbox" class="year-checkbox active-checkbox" id="#year-' + yearIndex +
		 '"> </td><td >' +
		subjectBuildSubjectsTable(yearIndex) + '</td></tr>';
		$(yearTr).appendTo("#years_table");
	}
}	

function subjectLoadFormInfo() {
	var entry, entryIndex;
	var idYearCheckbox, idSubjectsTable, idSubjectCheckbox, idValField;
	for (entryIndex=0; entryIndex<subjectFormInfo; entryIndex++) {
		entry = subjectFormInfo[entryIndex];
		idYearCheckbox = "#year-" + entry[0];
		idSubjectsTable = "#subject-table-" + entry[0];
		idSubjectCheckbox = "#subject-checkbox-" + entry[0] + "-" + subjectSubjectNames[entry[1]];
		idValField  = "#subject-numfield-" + entry[0] + "-" + subjectSubjectNames[entry[1]];
		$(idYearCheckbox).attr("checked:true");
		$(idSubjectCheckbox).attr("checked:true");
		$(idValField).val(entry[2]);
		$(idSubjectsTable).removeClass("hidden");
		$(idValField).removeClass("hidden");
	}
}

function subjectGatherFormInfo(){
	//report only those subjects active for the year
	var formInfo = [];
	var singleSubject = [];
	var yearIndex, subjectIndex;
	var idYearCheckbox, idSubjectCheckbox, idValField;
	var valFieldValue;
	for (yearIndex = 0; yearIndex < subjectYearNames.length; yearIndex++) {
		idYearCheckbox = "#year-" + yearIndex;
		if ($(idYearCheckbox).attr("checked")) {
			for (subjectIndex = 0; subjectIndex < subjectSubjectNames.length; subjectIndex++) {
				idSubjectCheckbox = "#subject-checkbox-" + 
					yearIndex + "-" + subjectSubjectNames[subjectIndex];
				if ($(idSubjectCheckbox).attr("checked")) {
					idValField  = "#subject-numfield-" +
						yearIndex + "-" + subjectSubjectNames[subjectIndex];
					valFieldValue = $(idValField).val();
					singleSubject[0] = yearIndex;
					singleSubject[1] = subjectIndex;
					singleSubject[2] = valFieldValue;
					formInfo.push(singleSubject);
				}
			}
		}
	}
	$("#id_json_testing_info").val(JSON.stringify(formInfo));
}

function subjectParseFormInfo(){
	if ($("#id_json_classyear_names").val() !== null) {
		subjectYearNames = json_parse($("#id_json_classyear_names").val());
	}
	if ($("#id_json_subject_names").val() !== null) {
		subjectSubjectNames = json_parse($("#id_json_subject_names").val());
	}
	if ($("#id_json_testing_info").val() !== null) {
		subjectFormInfo = json_parse($("#id_json_testing_info".val));
	}
}


$(function() {
	subjectParseFormInfo();
	subjectBuildYearsTable();
	subjectLoadFormInfo();
	$(".active-checkbox").click(function(){
		checkboxHideContents($(this));});
	$("#save_button").click(subjectGatherFormInfo);		
});
