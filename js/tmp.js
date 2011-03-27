var atYearNames = [];
var atSubjectNames = [];
var atTestingInfo = [];

function atBuildSubjectsTable(class_year) {
	var subjectName, subjectNameCol;
	var subjectNameCols = [];
	var subjectsTh = '';
	var subjectsTable;
	var subjectTr = [];
	var subjectsRows = '';
	var id, x, y;
	var numColumns = 2;
	var numRowsFirst = Math.floor(atSubjectNames.length / numColumns)  + 
		(atSubjectNames.length % numColumns);
	var numRowsOther = Math.floor(atSubjectNames.length / numColumns);
	var index = 0;
	for (x = 0; x <numColumns; x++) {
		var rowCount = (x === 0) ? numRowsFirst : numRowsOther;
		subjectNameCols[x] = atSubjectNames.slice(index, index+rowCount);
		index += rowCount;
		}
	for (y=0; y< subjectNameCols[0].length; y++){
		for (x=0; x<numColumns; x++) {
			subjectNameCol=atSubjectNames[x];
			if (y < subjectNameCols[x].length) {
				subjectName=subjectNameCol[y];
				id = class_year + "-" + subjectName;
				subjectTr[x] = '<td>' + subjectName + '</td>' + 
				'<td><input type="checkbox" class="subject-checkbox active-checkbox" id="subject-checkbox-' + id + '"></td>' +
				'<td><input type="text" class="small-numeric-field integer-field hidden" id="subject-numfield-' + id + '"></td>';
			} else {
				subjectTr[x] = "<td></td><td></td><td></td>";
			}
		}
		subjectsRows += '<tr class="subject-row">' + subjectTr[0]+ subjectTr[1] + '</tr>';
	}
	subjectsTh = '<tr><th class="width75">Name</th><th></th><th class="width120"># Questions</th> ' +
		'<th class="width75">Name</th><th></th><th style="width=120"># Questions</th></tr>';
	subjectsTable = '<table class="at-subjects thin-border hidden" id="subject-table-' + class_year +
		 '><tbody>' + subjectsTh + subjectsRows + '</tbody></table>';
	return subjectsTable;	
}

function atBuildYearsTable() {
	var yearTr, yearIndex, yearName;
	for (yearIndex = 0; yearIndex < atYearNames.length; yearIndex++) {
		yearName = atYearNames[yearIndex];
		yearTr = '<tr class="at-year"><td>' + yearName +
		'</td><td><input type="checkbox" class="year-checkbox active-checkbox" id="#year-' + yearIndex +
		 '"> </td><td >' +
		atBuildSubjectsTable(yearIndex) + '</td></tr>';
		$(yearTr).appendTo("#years_table");
	}
}	

function atLoadTestingInfo() {
	var entry, entryIndex;
	var idYearCheckbox, idSubjectsTable, idSubjectCheckbox, idNumField;
	for (entryIndex=0; entryIndex<atTestingInfo; entryIndex++) {
		entry = atTestingInfo[entryIndex];
		idYearCheckbox = "#year-" + entry[0];
		idSubjectsTable = "#subject-table-" + entry[0];
		idSubjectCheckbox = "#subject-checkbox-" + entry[0] + "-" + atSubjectNames[entry[1]];
		idNumField  = "#subject-numfield-" + entry[0] + "-" + atSubjectNames[entry[1]];
		$(idYearCheckbox).attr("checked:true");
		$(idSubjectCheckbox).attr("checked:true");
		$(idNumField).val(entry[2]);
		$(idSubjectsTable).removeClass("hidden");
		$(idNumField).removeClass("hidden");
	}
}

function atGatherTestingInfo(){
	//report only those subjects active for the year
	var testingInfo = [];
	var singleTestSubject = [];
	var yearIndex, subjectIndex;
	var idYearCheckbox, idSubjectCheckbox, idNumField;
	var numQuestions;
	for (yearIndex = 0; yearIndex < atYearNames.length; yearIndex++) {
		idYearCheckbox = "#year-" + yearIndex;
		if ($(idYearCheckbox).attr("checked")) {
			for (subjectIndex = 0; subjectIndex < atSubjectNames.length; subjectIndex++) {
				idSubjectCheckbox = "#subject-checkbox-" + 
					yearIndex + "-" + atSubjectNames[subjectIndex];
				if ($(idSubjectCheckbox).attr("checked")) {
					idNumField  = "#subject-numfield-" +
						yearIndex + "-" + atSubjectNames[subjectIndex];
					numQuestions = $(idNumField).val();
					singleTestSubject[0] = yearIndex;
					singleTestSubject[1] = subjectIndex;
					singleTestSubject[2] = numQuestions;
					testingInfo.push(singleTestSubject);
				}
			}
		}
	}
	$("#id_json_testing_info").val(JSON.stringify(testingInfo));
}

function atParseTestingInfo(){
	if ($("#id_json_classyear_names").val() !== null) {
		atYearNames = json_parse($("#id_json_classyear_names").val());
	}
	if ($("#id_json_subject_names").val() !== null) {
		atSubjectNames = json_parse($("#id_json_subject_names").val());
	}
	if ($("#id_json_testing_info").val() !== null) {
		atTestingInfo = json_parse($("#id_json_testing_info".val));
	}
}


$(function() {
	atParseTestingInfo();
	atBuildYearsTable();
	atLoadTestingInfo();
	$(".active-checkbox").click(function(){
		checkboxHideContents($(this));});
	$("#save_button").click(atGatherTestingInfo);		
});
