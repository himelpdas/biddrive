/*global $:false */
/*global window: false */

(function(){
  "use strict";


$(function ($) {

		if( !device.tablet() && !device.mobile() ) {

			/* Activate Parallax effect if non-mobile device is detected*/ 
		  	$('.intro-05').parallax("50%", 0.1);
		  	$('.intro-07').parallax("50%", 0.1);
		  	$('.promotional').parallax("50%", 0.1);
		  	$('.testimonial').parallax("50%", 0.1);
		  	$('.news-head').parallax("50%", 0.1);
		  	$('.project-head').parallax("50%", 0.1);
		  	$('.misc-head').parallax("50%", 0.1);
		  	$('.pricing-head').parallax("50%", 0.1);
								
		} else {
			
			/* Dectivate Parallax effect if mobile device is detected (bg image is displayed)*/ 
			$('.parallax').addClass('no-parallax');
			
		}
   		
        
   
});
// $(function ($)  : ends

})();
//  JSHint wrapper $(function ($)  : ends







	

