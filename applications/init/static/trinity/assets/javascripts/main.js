// MAIN.JS
//--------------------------------------------------------------------------------------------------------------------------------
//This is main JS file that contains custom JS scipts and initialization used in this template*/
// -------------------------------------------------------------------------------------------------------------------------------
// Template Name: trinity.
// Author: Designova.
// Version 1.0 - Initial Release
// Website: http://www.designova.net 
// Copyright: (C) 2014 
// -------------------------------------------------------------------------------------------------------------------------------

/*global $:false */
/*global window: false */

(function(){
  "use strict";


$(function ($) {

    //Detecting viewpot dimension
     var vH = $(window).height();
     var vW = $(window).width();
     var cW = $('.container').width();

     //Adjusting Intro Components Spacing based on detected screen resolution
     $('#intro, .full-height').css('height',vH);
     $('.full-width').css('width',vW);
     $('.half-height').css('height',vH/2);

    //mouse icon fixes
     var fixPerc = (vH * 95 / 100).toFixed(2);
     $('.intro .mouse-icon-wrap').css('top',fixPerc+'px');

    //Left WallPaper Layout
    var lH = $('.left-wallpaper').parent().height();
    $('.left-wallpaper').css('height',lH);
    $('.left-wallpaper').mouseenter(function(){
    });
    var rH = $('.right-wallpaper').parent().height();
    $('.right-wallpaper').css('height',rH);
    $('.right-wallpaper').mouseenter(function(){
    });



//Equi-heigh Divs
$(document).ready(function() {

  if(vW > 1000)
  {
   var maxHeight = -1;

   $('.equal-height-one').each(function() {
     maxHeight = maxHeight > $(this).height() ? maxHeight : $(this).height();
   });

   $('.equal-height-one').each(function() {
     $(this).height(maxHeight);
   });

}

 });



$(window).bind('load', function () { 
    $('.animated').each(function(){ 
        $(this).closest('.inner-section').css('overflow','hidden'); 
    }); 
});



$(document).ready(function() {


    
    //contact form expander
    $('#contact-trigger-button').click(function(){
      $('#contact-form').slideDown(2000);
      $('html, body').animate({scrollTop: ($('#contact-form').offset().top - 0)});
    });


    //Service Details Expander
    $('.service-item a').click(function(){
        var serviceTarget = $(this).attr('data-service-details-expand');
        $('.service-details').slideUp('slow');
        $('#service-details-'+serviceTarget).slideDown('slow');
    });


});


//TWITTER INIT (Updated with compatibility on Twitter's new API):
//PLEASE READ DOCUMENTATION FOR INFO ABOUT SETTING UP YOUR OWN TWITTER CREDENTIALS:
$(function ($) {
          $('#ticker').tweet({
              modpath: '/init/static/trinity/assets/twitter/',
              count: 1,
              loading_text: 'loading twitter update...',
              username:'designovastudio'
              /* etc... */
          });
}); 



    //contact form expander
    $('.contact-trigger-button').click(function(){
      $(this).fadeOut();
      $('#contact-form-wrap').slideDown(2000);
      $('html, body').animate({scrollTop: ($('#contact-form-wrap').offset().top - 0)});
    });


   

    $("#intro-carousel").owlCarousel({
        navigation : true,
        pagination: false,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,1],
        itemsDesktopSmall: [1440,1],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: true,
        autoHeight: true,
        transitionStyle : "goDown"
      });


    $("#intro-statistics-carousel").owlCarousel({
        navigation : true,
        pagination: false,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,1],
        itemsDesktopSmall: [1440,1],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: true,
        autoHeight: true,
        transitionStyle : "backSlide"
      });

    $("#intro-agency-carousel").owlCarousel({
        navigation : true,
        pagination: false,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,1],
        itemsDesktopSmall: [1440,1],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: true,
        autoHeight: true
      });


    $("#intro-02-carousel").owlCarousel({
        navigation : true,
        pagination: false,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,1],
        itemsDesktopSmall: [1440,1],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: true,
        autoHeight: true,
        slideSpeed: 2200,
        paginationSpeed: 1200,
        transitionStyle : "fadeUp"
      });


    $("#intro-03-carousel").owlCarousel({
        navigation : true,
        pagination: false,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,1],
        itemsDesktopSmall: [1440,1],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: true,
        autoHeight: true
      });

    $("#intro-06-carousel").owlCarousel({
        navigation : true,
        pagination: false,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,1],
        itemsDesktopSmall: [1440,1],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: true,
        autoHeight: true,
        transitionStyle : "goDown"
      });
      
    $("#about-carousel").owlCarousel({
        navigation : false,
        pagination: true,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,1],
        itemsDesktopSmall: [1440,1],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: false,
        autoHeight: true,
      });

    $("#stats-carousel").owlCarousel({
        navigation : false,
        pagination: false,
        responsive: true,
        items: 3,
        touchDrag: true,
        mouseDrag: true,
        itemsDesktop: [3000,8],
        itemsDesktopSmall: [1440,3],
        itemsTablet:[800,3],
        itemsTabletSmall: [600,2],
        itemsMobile: [360,1],
        autoPlay: true
      });

    $("#thumb-carousel").owlCarousel({
        navigation : false,
        pagination: false,
        responsive: true,
        items: 2,
        touchDrag: true,
        mouseDrag: true,
        itemsDesktop: [3000,8],
        itemsDesktopSmall: [1440,2],
        itemsTablet:[800,2],
        itemsTabletSmall: [600,2],
        itemsMobile: [360,1],
        autoPlay: true
      });


    $("#service-list-carousel").owlCarousel({
        navigation : false,
        pagination: true,
        responsive: true,
        items: 2,
        touchDrag: true,
        mouseDrag: true,
        itemsDesktop: [3000,3],
        itemsDesktopSmall: [1440,2],
        itemsTablet:[800,2],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoHeight: true,
        autoPlay: true
      });

    $("#process-carousel").owlCarousel({
        navigation : false,
        pagination: true,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,3],
        itemsDesktopSmall: [1440,3],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: false,
        autoHeight: false,
      });



    $("#testimonial-carousel").owlCarousel({
        navigation : false,
        pagination: true,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,1],
        itemsDesktopSmall: [1440,1],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: false,
        autoHeight: true,
      });



    $("#team-carousel").owlCarousel({
        navigation : true,
        pagination: false,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,3],
        itemsDesktopSmall: [1440,3],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: false,
        autoHeight: false,
      });


    $("#client-carousel").owlCarousel({
        navigation : true,
        pagination: false,
        responsive: true,
        items: 1,
        touchDrag: true,
        navigationText: false,
        mouseDrag: true,
        itemsDesktop: [3000,4],
        itemsDesktopSmall: [1440,4],
        itemsTablet:[1024,1],
        itemsTabletSmall: [600,1],
        itemsMobile: [360,1],
        autoPlay: false,
        autoHeight: true,
      });


    //Venobox Responsive Lightbox
    $('.venobox, .image-lightbox-link').venobox({
    numeratio: true
    }); 

    //Portfolio Filter Active State
    $('ul#portfolioFilter li').click(function(){
      $('ul#portfolioFilter li').removeClass('active-filter');
      $(this).addClass('active-filter');
    });


    //Highlight the navigation on focusing a section
   $('.standard-nav li > a').click(function(){
        $('.standard-nav li > a').removeClass('highlighted');
        $(this).addClass('highlighted');
    });
    $('.page, .intro').mouseenter(function(){
        var sectionId = $(this).attr('id');
        $('.standard-nav li > a').removeClass('highlighted');
        $('#'+sectionId+'-linker').addClass('highlighted');
    });





    //Setup waypoints plugin
    $('.page').first().waypoint(function (event, direction) {

        //If the user scrolls up change the navigation link that has the same data-slide attribute as the slide to active and 
        //remove the active class from the previous navigation link 
        if (direction === 'down') {
          $('.standard-header-top').fadeIn();
          $('.standard-header-bottom').addClass('move-top');
        }
        // else If the user scrolls down change the navigation link that has the same data-slide attribute as the slide to active and 
        //remove the active class from the next navigation link 
        else {
          $('.standard-header-top').fadeOut();
          $('.standard-header-bottom').removeClass('move-top');
        }

    }, { offset: 150 });


});
// $(function ($)  : ends

})();
//  JSHint wrapper $(function ($)  : ends







  

