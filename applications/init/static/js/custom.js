(function(){
    "use strict";


    $(function ($) {

        $(document).ready(function() {
            var animateSpeed = 700;

            $('#car-chooser-switch-toppicks').click(function() {
                $('#car-chooser-toppicks').show(animateSpeed);
                $('#car-chooser-allmakes').hide(animateSpeed);
            });

            $('#car-chooser-switch-allmakes').click(function() {
                $('#car-chooser-toppicks').hide(animateSpeed);
                $('#car-chooser-allmakes').show(animateSpeed);
            });
        });

    });

})();









