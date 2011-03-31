/**
 * @author master
 */
var loadanimVersion = 0.1;
var loadaminIntervalId = null;
var loadaminCount = 0;
var loadaminStartedCount = 0;
var loadaminStarted = false;

jQuery.loadanim = {
    start : function (options) {
        var defaults = {  
            updateTime: 400,  // milliseconds
            message: "Loading",
            ellipsisText: "..."  
        };  
        var options = $.extend(defaults, options);  

		loadaminStartedCount += 1;
        if (loadaminStartedCount > 1) {
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
        loadaminStarted = true;
        obj.html(options.message);
        loadaminCount = 0;
        loadaminIntervalId =  setInterval(function () {
            if (++loadaminCount > options.ellipsisText.length) {
                loadaminCount = 0;
            }
            var obj = $("div#loadAnim");
            obj.html(options.message + options.ellipsisText.substr(0, loadaminCount));
          }, options.updateTime);
        obj.css("display", "block");
    },
    stop : function (options) {
        if (!loadaminStarted) {
            return;
        }
        loadaminStartedCount -= 1;
		if (loadaminStartedCount > 0) {
			return;
		}
        clearInterval(loadaminIntervalId);
        loadaminIntervalId = null;
        var obj = $("div#loadAnim");
        obj.css("display", "none");
        obj.remove();
		loadaminStarted = false;
    }

};
