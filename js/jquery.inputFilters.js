/*
 *  Dev One (http://www.dev-one.com)
 *  Input filters jQuery plug-in
 *
 */

$(function() {
	$.fn.numeric = function(options) {
		settings = jQuery.extend({
			allowDecimal: true,
			allowNegative: false,
			decimalSeparator: ".",
			maxDecimals: -1
		}, options);

		$(this).keypress(function(e) {
			var key = (e.which) ? e.which : e.keyCode;
			var text = $(this).val();
			var caretPos = getCaretPos($(this)[0]);

			// Allow system keys
			if ((e.which == 0) || (e.which == 8))
			{
				return true;
			}
			
			// Allow digits
			if ((e.which >= 48) && (e.which <= 57))
			{
				if ((settings.allowDecimal) && (settings.maxDecimals > -1))
				{
					var decimalSeparatorPos = text.indexOf(settings.decimalSeparator);
					
					if ((decimalSeparatorPos > -1) && (caretPos > decimalSeparatorPos) && (text.substr(decimalSeparatorPos + 1).length >= settings.maxDecimals))
					{
						return false;
					}
				}
				
				return true;
			}
			
			// Allow negative
			if ((settings.allowNegative) && (e.which == 45) && (caretPos == 0) && (text.indexOf("-") == -1))
			{
				return true;
			}
			
			
			// Allow decimal
			if ((settings.allowDecimal) && (e.which == getSeparatorCode(settings.decimalSeparator)) && (caretPos > 0) && (text.indexOf(settings.decimalSeparator) == -1) && (text.substr(caretPos).length <= settings.maxDecimals))
			{
				return true;
			}
			
			return false;
		});
		
		$(this).blur(function() {
			var text = $(this).val();
			var pos = text.length - 1
			
			// Remove the decimal separator if it ends the string
			$(this).filter(function() {
				return text.charAt(pos) == settings.decimalSeparator;
			}).val(text.substr(0, pos));

		});
	};
});

function getCaretPos(element)
{
	var pos = -1;
				
	if (document.selection)
	{
		element.focus ();
		var oSel = document.selection.createRange ();
		oSel.moveStart ('character', -element.value.length);
		pos = oSel.text.length;
	}
	else if (element.selectionStart || element.selectionStart == "0")
	{
		pos = element.selectionStart;
	}
	
	return pos;
}

function getSeparatorCode(character)
{
	switch (character)
	{
		case ".":
			return 46;
		case ",":
			return 44;
		default:
			return -1;
	}
}