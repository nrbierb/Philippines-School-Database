/**
 * @author master
 */
var version = 0.01;
var intvl_id = null;
var count = 0;
var startedCount = 0;

jQuery.loadanim = {

    start : function (options) {
        var defaults = {  
            updateTime: 400,  // milliseconds
            message: "Loading",
            ellipsisText: "..."  
        };  
        var options = $.extend(defaults, options);  

		startedCount += 1;
        if (startedCount > 1) {
            return;
        }
        $("body").append('<div id="loadAnim"></div>');
        var obj = $("div#loadAnim");
        obj.css("display", "none");
        obj.css("color", "#000");
        obj.css("background-color", "#FEB");
        obj.css("position", "absolute");
        obj.css("width", (options.message.length + options.ellipsisText.length + 1) + "ex");
		obj.css("border", ("4px groove  #8b6914"));
        obj.css("padding", "1ex");
        obj.css("left", "40%");
        obj.css("top", "20%");
        obj.css("z-index", "9999");
        started = true;
        obj.html(options.message);
        count = 0;
        intvl_id =  setInterval(function () {
            if (++count > options.ellipsisText.length) {
                count = 0;
            }
            var obj = $("div#loadAnim");
            obj.html(options.message + options.ellipsisText.substr(0, count));
          }, options.updateTime);
        obj.css("display", "block");
    },
    stop : function (options) {
        if (!started) {
            return;
        }
        startedCount -= 1;
		if (startedCount > 0) {
			return;
		}
        clearInterval(intvl_id);
        intvl_id = null;
        var obj = $("div#loadAnim");
        obj.css("display", "none");
        obj.remove();
    }

};
