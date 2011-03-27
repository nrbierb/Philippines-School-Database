/**
 * @author master
 * Classes to support tables built around google tables and jquery ui dialogs
 */
//Google Widget Table General Support
google.load('visualization', '1', {packages:['table']});

function StandardTable() {
	this.theTable = null;	
	this.keysArray = null;
	this.tableDescriptor = null;
	this.tableDomElement = null;
	this.dataTable = null;
	this.noSelectDialog = null;
	this.multiSelectDialog = null;
} 

StandardTable.prototype.setDomAndCreateTable = function(domElement) {
	this.tableDomElement = domElement;
	this.theTable = new google.visualization.Table(this.tableDomElement);
}

StandardTable.prototype.isInitialized = function() {
	return (this.theTable !== null);
};

StandardTable.prototype.loadAjaxResponse = function(ajaxResponse){
	if (ajaxResponse) {
		var extracted = eval('(' + ajaxResponse + ')');
		this.keysArray = eval('(' + extracted[0] + ')');
		this.tableDescriptor = eval('(' + extracted[1] + ')');
	}
};

StandardTable.prototype.finalizeTable = function(tableParameters) {
	this.dataTable = new google.visualization.DataTable(this.tableDescriptor, 0.6);
	this.theTable.draw(this.dataTable,tableParameters);  
};

StandardTable.prototype.getSelectedKeys = function() {
    var selection = this.theTable.getSelection();
	var selectedKeys = [];
    for (var i = 0; i < selection.length; i++) {
		row = selection[i].row;
		selectedKeys[i] = this.theTable.keysArray[row];	  
	}
	return selectedKeys;	
};

StandardTable.prototype.setSelectionDialogs = function(noSelectDiv, multiSelectDiv) {
	this.noSelectDialog = noSelectDiv.dialog(std_ok_dialog);
	this.multiSelectDialog = multiSelectDiv.dialog(std_ok_dialog);
};

StandardTable.prototype.warnNoSelection = function() {
	 this.noSelectDialog('open');
};
	 
StandardTable.prototype.warnTooManySelections = function() {
	this.multiSelectDialog("open");
};

StandardTable.prototype.getSingleSelectedKey = function() {
	var selectedKey = null;
	var selectedKeys = this.getSelectedKeys();
	if (selectedKeys.length === 0) {
		this.warnNoSelection();
	} else if (selectedKeys.length > 1) {
		this.warnTooManySelections();
	} else {
		selectedKey = selectedKeys[0];
	}
	return selectedKey;
};
