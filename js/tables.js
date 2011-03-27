		
/**
 * Classes to support tables built around google tables and jquery ui dialogs
 */
//Google Widget Table General Support
google.load('visualization', '1', {packages:['table']});

function StandardTable() {
	this.theTable = null;	
	this.dataTable = null;
	this.tableParameters = {};
	this.readyFunction = null;
	this.formatFunction = null;
	this.keysArray = null;
	this.tableDomElement = null;
	this.noTableDialog = null;
	this.noSelectDialog = null;
	this.multiSelectDialog = null;
	this.confirmDeleteDiv = null;
	this.objectClass = "";
	this.updateTableFunction = null;
	this.maxHeight = 400;
	this.rowHeight = 25;
	this.padHeight = 40;
	this.sortColumns = null;
}

StandardTable.prototype.initializeTableParams = function() {
	this.tableParameters = {
		'width': 0,
		cssClassNames: {
			headerRow: "ui-widget-header",
			tableRow: "tblRow",
			selectedTableRow: "tblSelectRow",
			oddTableRow: "tblOddRow",
			hoverTableRow: "tblRow ui-state-hover",
			rowNumberCell: "row-number-cell"
		}
	};
	if (this.sortColumns !== null) {
		this.tableParameters.sortColumn = this.sortColumns;
	}
	
};

StandardTable.prototype.setDom = function(domElement) {
	this.tableDomElement = domElement;
};

StandardTable.prototype.isInitialized = function() {
	return (this.theTable !== null);
};

StandardTable.prototype.loadAjaxResponse = function(parsedAjaxResponse){
	if (parsedAjaxResponse) {
		this.keysArray = jQuery.parseJSON(parsedAjaxResponse.keysArray);
		this.tableDescriptor = eval('(' + parsedAjaxResponse.tableDescriptor + ')');
	}
};

StandardTable.prototype.setHeight = function(lineCount){
	var computedHeight = lineCount * this.rowHeight + this.padHeight;
	var tableHeight = (computedHeight < this.maxHeight)? computedHeight : this.maxHeight;
	this.tableParameters.height = tableHeight;
};

StandardTable.prototype.setWidth = function(pixelsWide){
	this.tableParameters.width = pixelsWide;
};

StandardTable.prototype.draw = function() {
	this.theTable.draw(this.dataTable,this.tableParameters);  
};
	
StandardTable.prototype.finalizeTable = function() {
	this.dataTable = new google.visualization.DataTable(this.tableDescriptor, 0.6);
	this.theTable = new google.visualization.Table(this.tableDomElement);
	if (this.formatFunction !== null) {
		this.formatFunction(this.dataTable);
	}	
	if (this.readyFunction !== null) {
		google.visualization.events.addListener(this.theTable, 'ready', this.readyFunction);
	}	
	this.draw();
};

StandardTable.prototype.getRow = function(rowIndex){
	/*
	 * Get the key from the keyArray and an associative array of the row values indexed by
	 * the column id. 
	 */
	var key = "";
	if (this.keysArray !== null) {
		var key = this.keysArray[rowIndex];
	}
	var rowData = {};
	var j;
	for (j=0; j < this.dataTable.getNumberOfColumns(); j++) {
		var cellData = {};
		cellData.v = this.dataTable.getValue(rowIndex,j);
		cellData.fv = this.dataTable.getFormattedValue(rowIndex,j);
		rowData[this.dataTable.getColumnId(j)] = cellData;
	}
	return {
		"key": key,
		"data": rowData
		};	
};

StandardTable.prototype.selectAllRows = function(){
	var selectionArray = [];
	var i;
	for (i = 0; i < this.dataTable.getNumberOfRows(); i++) {
		selectionArray[i] = {
			row: i,
			column: 0
		};
	}
	this.theTable.setSelection(selectionArray);
}
	
StandardTable.prototype.getSelectedRowsData = function() {
    var selection = this.theTable.getSelection();
	var rowsData = [];
	var i;
	var rowIndex;
    for (i = 0; i < selection.length; i++) {
		rowIndex = selection[i].row;
		rowsData[i] = this.getRow(rowIndex);
	}
	return rowsData;	
};

StandardTable.prototype.removeSelectedRows = function(){
	var rowsData = this.getSelectedRowsData();
	var selection = this.theTable.getSelection();
	var i;
	//remove bottom first to avoid row reindexing problems
	for (i = selection.length -1; i >= 0; i--) {
		this.dataTable.removeRow(selection[i].row);
	}
	//clear all selections
	this.theTable.setSelection();
	this.draw();
	return rowsData;
};

StandardTable.prototype.putRow = function(rowData, fillFunctions){
	/*
	 * Put the data obtained by the getRow function from a different table into a new row 
	 * in the table. Each column will be filled by the data from a corresponding column id.
	 * fillFunctions is an associative array keyed by columnId of anonymous functions used to fill in
	 * the values of columns that do not have values in the rowData
	 */
	var dTable = this.dataTable;
	var newRowIndex = dTable.addRow();
	if (this.keysArray !== null) {
		this.keysArray[newRowIndex] = rowData.key;
	}
	var j;
	for (j=0; j< dTable.getNumberOfColumns(); j++ ) {
		var id = dTable.getColumnId(j);
		var cellData;
		if (id in rowData.data) {
			cellData = rowData.data[id];
			dTable.setCell(newRowIndex, j, cellData.v, cellData.fv);
		} else if (id in fillFunctions) {
				cellData = fillFunctions.id(rowData);
				dTable.setCell(newRowIndex, j, cellData.v, cellData.fv);
		}
	}
};

StandardTable.prototype.putRows = function(rowsData, fillFunctions){
	//A trivial extension to putRow to use with multiple rows
	var i;
	for (i = 0; i < rowsData.length; i++) {
		this.putRow(rowsData[i], fillFunctions);
	}
	//clear all selections
	this.theTable.setSelection();
	this.draw();
};

StandardTable.prototype.getSelectedKeys = function() {
    var selection = this.theTable.getSelection();
	var selectedKeys = [];
	var i;
	var rowIndex;
    for (i = 0; i < selection.length; i++) {
		rowIndex = selection[i].row;
		selectedKeys[i] = this.keysArray[rowIndex];	  
	}
	return selectedKeys;	
};

StandardTable.prototype.getSelectedNames = function() {
	//Get a list of the first values in the first column of all selected rows.
	//The first column is assumed to be the name.
	var selection = this.theTable.getSelection();
	var selectedNames = [];
	var i;
	var rowIndex;
    for (i = 0; i < selection.length; i++) {
		rowIndex = selection[i].row;
		selectedNames[i] = this.dataTable.getValue(rowIndex, 0);	  
	}
	return selectedNames;	
};


StandardTable.prototype.setSelectionDialogs = function(noTableDiv, noSelectDiv, 
	multiSelectDiv, confirmDeleteDiv){
	if (noTableDiv) {
		this.noTableDialog = noTableDiv.dialog(std_ok_dialog);
	}
	if (noSelectDiv) {
		this.noSelectDialog = noSelectDiv.dialog(std_ok_dialog);
	}
	if (multiSelectDiv) {
		this.multiSelectDialog = multiSelectDiv.dialog(std_ok_dialog);
	}
	if (confirmDeleteDiv) {
		this.confirmDeleteDiv = confirmDeleteDiv;
	}
};

StandardTable.prototype.warnNoTable = function() {
	 this.noTableDialog.dialog('open');
};
	 
StandardTable.prototype.warnNoSelection = function() {
	 this.noSelectDialog.dialog('open');
};
	 
StandardTable.prototype.warnTooManySelections = function() {
	this.multiSelectDialog.dialog("open");
};

StandardTable.prototype.getSingleSelectedKey = function() {
	var selectedKey = null;
	if (this.isInitialized()) {
		var selectedKeys = this.getSelectedKeys();
		if (selectedKeys.length === 0) {
			this.warnNoSelection();
		} else if (selectedKeys.length > 1) {
				this.warnTooManySelections();
			} else {
				selectedKey = selectedKeys[0];
			}
	} else {
		this.warnNoTable();
	} 
	return selectedKey;
};

StandardTable.prototype.getSingleSelectedKeyNoWarn = function() {
	var selectedKey = null;
	if (this.isInitialized()) {
		var selectedKeys = this.getSelectedKeys();
		if (selectedKeys.length > 0) {
			selectedKey = selectedKeys[0];
		}
	}
	return selectedKey;
};

StandardTable.prototype.marshallResults= function(columnArray, cellProcessFunction) {
	var rowCount = this.keysArray.length;
	var columnCount = columnArray.length;
	var returnData = [];
	var i;
	var j;
	var cellValue;
	var theData;
	for (i = 0; i < rowCount; i++) {
		returnData[i] = [];
		for ( j = 0; j < columnCount; j++) {
			cellValue = this.dataTable.getValue(i, j+1);
			if (cellProcessFunction !== null) {
				cellValue = cellProcessFunction(cellValue);
			}
			returnData[i][j] = cellValue;
		}
	}
	theData = {"keys":this.keysArray, "columns":columnArray, "data":returnData};
	return (JSON.stringify(theData));
};

StandardTable.prototype.marshallInputFieldsResults= function(tableName, columnArray) {
	var rowCount = this.keysArray.length;
	var columnCount = columnArray.length;
	var fieldsIndex = 0;
	var returnData = [];
	var i, j, id_field
	for (i = 0; i < rowCount; i++) {
		returnData[i] = [];
		for (j = 0; j < columnCount; j++) {
			id_field = tableName + "-" + String(j) + "-" + String(i);
			returnData[i][j] = $("#" + id_field).val();
			fieldsIndex++;
		}
	}
	var theData = {
		"keys": this.keysArray,
		"columns": columnArray,
		"data": returnData
	};
	return (JSON.stringify(theData));
};

StandardTable.prototype.deleteSelectedObject = function(theTable, deleteObjectKey) {
    $.ajax( {
        type: "POST",
        url: "/ajax/delete_instance/",
        data: {"class":theTable.objectClass,
                "key":deleteObjectKey},
        dataType: "json" ,
        success: function(returnData) {
            theTable.updateTableFunction();
		}
	});	
};

StandardTable.prototype.confirmDeleteSelection = function(theTable, deleteObjectKey, deleteFunction) {	
	this.confirmDeleteDiv.dialog({
		modal:true,
		autoOpen:true,
		buttons: { "Ok": function() {$(this).dialog("destroy"); 
						deleteFunction(theTable, deleteObjectKey);},
		         "Cancel": function() { $(this).dialog("destroy");}}});
};


StandardTable.prototype.deleteSelectedRow = function(){
	var deleteObjectKey = this.getSingleSelectedKey();
	if (deleteObjectKey) {
		this.confirmDeleteSelection(this, deleteObjectKey, this.deleteSelectedObject);
	}
};
