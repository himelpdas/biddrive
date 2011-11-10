// autoscroll widget with jquery event(s)

var toggleAutoScroll = function () {
    // uses an obj attached to window for state
    var scrollOn = function() {
        window.autoScroll = setInterval( function() {
                // ui hack?  needs more testing
                window.output.scrollTop = window.output.scrollHeight;
        }, 3000);  // 3 second interval
    };
    var scrollOff = function() {
        clearInterval(window.autoScroll);
        delete window.autoScroll;
    };
    if (arguments.length > 0) {
        // boolean test first arg force with true/false for on/off
        if (arguments[0]) {
            scrollOn();
        } else {
            scrollOff();
        }
    } else if (typeof window.autoScroll == 'undefined') {
        scrollOn();
    } else {
        scrollOff();
    }
};

// jquery event(s)

jQuery(document).ready(function () {
    // force it on by default
    toggleAutoScroll(true)
    // click event
    jQuery('#autoscroll').click(function() {
        toggleAutoScroll();
        if (typeof window.autoScroll == 'undefined') {
            // 'off' state animation
            jQuery(this).fadeTo(350, 0.55);
        } else {
            // 'on' state animation
            jQuery(this).fadeTo(350, 1);
        }
    });
});

// todo: some key - toggle off
// todo: drag scrollbar up - toggle off
// todo: drag scrollbar to bottom - toggle off
