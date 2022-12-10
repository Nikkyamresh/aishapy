$(function() {
  $('a#calculate').bind('click', function() {
    alert("hi")
    send();
    return false;
  });
  $("#form").bind('submit',function() {
    send();
    return false;
  })
  $("#say").click(function() {
    say();
  /*  var text=say();
    $('input[name="a"]').val(text);
  send();*/
  })
});
function send() {
  $("#img").attr("src","static/play.gif");
  $.getJSON($SCRIPT_ROOT + '/bot', {
    a: $('input[name="a"]').val(),
   }, function(data) {
    $("#result").prepend("<br> Me : "+ $('input[name="a"]').val());
    $("#result").prepend("<br> AISHA: "+data.result);
  //  responsiveVoice.speak($('input[name="a"]').val(),"UK English Male");
    $('input[name="a"]').val('')
    responsiveVoice.speak(data.result,"UK English Female");
    $("#img").attr("src","static/play.jpg");
      $('input[name="a"]').focus();
     setTimeout(function() {$("#say").click();},2000);
  });
  return false;
}
function say() {
  var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition || window.mozSpeechRecognition || window.msSpeechRecognition)();
recognition.lang = 'en-US';
recognition.interimResults = false;
recognition.maxAlternatives = 5;
recognition.start();
recognition.onresult = function(event) {
    var v=event.results[0][0].transcript;
    console.log(v);
    $('input[name="a"]').val(v);

      send();
     return v;
}
}
// Find all iframes
var $iframes = $( "iframe" );

// Find &#x26; save the aspect ratio for all iframes
$iframes.each(function () {
  $( this ).data( "ratio", this.height / this.width )
    // Remove the hardcoded width &#x26; height attributes
    .removeAttr( "width" )
    .removeAttr( "height" );
});

// Resize the iframes when the window is resized
$( window ).resize( function () {
  $iframes.each( function() {
    // Get the parent container&#x27;s width
    var width = $( this ).parent().width();
    $( this ).width( width )
      .height( width * $( this ).data( "ratio" ) );
  });
// Resize to fix all iframes on page load.
}).resize();
