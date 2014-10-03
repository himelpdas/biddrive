
/*global $:false */
/*global window: false */

(function(){
  "use strict";


$(function ($) {

		if( !device.tablet() && !device.mobile() ) {

			/* plays the BG Vimeo or Youtube video if non-mobile device is detected*/ 
			$.okvideo({ source: '80282064', //set your video source here
		                    autoplay:true,
		                    loop: true,
		                    highdef:true,
		                    hd:true, 
		                    adproof: true,
		                    volume:50 // control the video volume by setting a value from 0 to 99
		                 });
						
		} else {
			
			/* displays a poster image if mobile device is detected*/ 
			$('.intro-04').addClass('poster-img');
			
		}
   		
        
   
});
// $(function ($)  : ends

})();
//  JSHint wrapper $(function ($)  : ends







	

